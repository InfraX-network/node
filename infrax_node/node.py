from __future__ import annotations

import mimetypes
import shutil
import subprocess
import time
from pathlib import Path

import httpx
from loguru import logger
from tqdm.contrib.concurrent import thread_map

from . import crud
from .config import config
from .exceptions import AppFailedToInstallException, AppFailedToUninstallException
from .types import File, Job, Result


def install_app(app_id: str) -> None:  # sourcery skip: extract-method
    """Downloads the app and its dependencies.
    Apps use python 3.10 and pip to install dependencies into a
    virtual environment in the app directory.

    Args:
        app (App): the app to install
    """
    crud.set_node_busy()

    app = crud.get_app(app_id)

    # mkdir the app directory and give read, write, and execute
    # permissions to the current user
    app_path = get_app_directory() / app.id

    if app_path.exists():
        logger.info(f"App {app.name} is already installed")
        crud.add_app(app.id)
        crud.set_node_idle()
        return

    logger.info(f"Installing app {app.name}")

    try:
        app_path.mkdir(parents=True, exist_ok=True, mode=0o777)

        # create a virtual environment
        logger.info(f"Creating virtual environment for app {app.name}")
        subprocess.run(["python3.11", "-m", "venv", app_path / ".venv"])
        logger.info(f"Virtual environment created for app {app.name}")

        download_files(app.files, app_path)

        # install app dependencies
        if (app_path / "requirements.txt").exists():
            logger.info(
                f"requirements.txt exists for app {app.name}, installing dependencies"
            )
            subprocess.run(
                [
                    ".venv/bin/pip",
                    "install",
                    "-r",
                    app_path / "requirements.txt",
                ],
                cwd=app_path,
            )
            logger.info(f"Dependencies installed for app {app.name}")
        else:
            logger.info(f"App {app.name} has no dependencies")
    except Exception as e:
        logger.error(f"Failed to install app {app.name}: {e}")
        crud.report_failed_app_install(app.id, AppFailedToInstallException(str(e)))
    crud.add_app(app.id)
    crud.set_node_idle()


def uninstall_app(app_id: str) -> None:
    """Removes the app and its dependencies.

    Args:
        app (App): the app to remove
    """
    crud.set_node_busy()
    app_path = get_app_directory() / app_id
    if not app_path.exists():
        crud.set_node_idle()
        return
    logger.info(f"Uninstalling app {app_id}")
    try:
        # remove the app directory, which also removes the virtual environment
        if app_path.exists():
            subprocess.run(["rm", "-rf", app_path])
    except Exception as e:
        logger.error(f"Failed to uninstall app {app_id}: {e}")
        # clean up the app directory
        if app_path.exists():
            shutil.rmtree(app_path)
        crud.report_failed_app_uninstall(app_id, AppFailedToUninstallException(str(e)))
    crud.remove_app(app_id)
    crud.set_node_idle()


def run_job(job: Job):
    """Runs the installed app with the given job.

    Args:
        job (Job): the job to run
    """
    crud.set_node_busy()
    logger.info(f"Running job {job.id} with app {job.app_id}")
    app_path = get_app_directory() / job.app_id
    input_path = app_path / "input"
    output_path = app_path / "output"

    start_time = 0
    end_time = 0
    process = None

    try:
        if not app_path.exists():
            logger.error(f"App {job.app_id} is not installed")
            crud.set_node_idle()
            return

        # ensure the input and output directories exist
        if input_path.exists():
            shutil.rmtree(input_path)
        input_path.mkdir(exist_ok=True)

        if output_path.exists():
            shutil.rmtree(output_path)
        output_path.mkdir(exist_ok=True)

        # download the input files
        download_files(job.files or [], input_path)

        venv_command = ".venv/bin/python"
        if not (app_path / venv_command).exists():
            raise FileNotFoundError(f"{venv_command} does not exist")

        command = [venv_command, "main.py"]

        # add the job arguments, if any
        kwargs = job.meta.get("kwargs", {})

        if isinstance(kwargs, dict):
            for key, value in kwargs.items():
                command.extend((f"--{key}", str(value)))

        # run the app in the app directory
        start_time = time.time()

        # async live capture the output
        process = subprocess.Popen(
            command,
            cwd=app_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # wait for the process to finish
        while process.poll() is None:
            time.sleep(1)

        end_time = time.time()

        success = True
        error = None
        if process.returncode != 0:
            logger.error(f"Job {job.id} failed with exit code {process.returncode}")
            success = False
            error = f"Job failed with exit code {process.returncode}"

        crud.set_job_finishing(job)

        # ensure the output directory exists
        if not output_path.exists():
            output_path.mkdir(exist_ok=True)

        # iterate over the output files and upload them
        output_files = list(output_path.iterdir())
        file_ids = upload_files(output_files, output_path)

    except Exception as e:
        logger.error(f"Job {job.id} failed: {e}")
        success = False
        error = str(e)
        file_ids = []
        if not end_time:
            # end_time = time.process_time() # this may be wrong
            end_time = time.time()  # swapped to this

    finally:
        # remove the input and output directory contents, if it exists
        if input_path.exists():
            shutil.rmtree(input_path)
        if output_path.exists():
            shutil.rmtree(output_path)

        stdout_str = process.stdout.read() if process and process.stdout else ""
        stderr_str = process.stderr.read() if process and process.stderr else ""
        output = f"{stdout_str}\n{stderr_str}"

        result = Result(
            job_id=job.id,
            execution_time=end_time - start_time,
            success=success,
            error=error,
            output=output,
            file_ids=file_ids,
        )
        crud.upload_result(result)
        crud.set_job_finished(job)
        crud.set_node_idle()


def get_app_directory() -> Path:
    app_dir = Path(config.host.app_dir)
    app_dir.mkdir(exist_ok=True, parents=True)
    return app_dir


def get_installed_apps() -> list[str]:
    # get the list of currently installed apps
    # app_dir contains folders with the app ids
    return [d.name for d in get_app_directory().iterdir() if d.is_dir()]


def download_files(files: list[File], path: Path):
    """Downloads the files to the given path.

    Args:
        files (list[File]): the files to download
        path (Path): the path to save the files
    """
    file_map = {f.id: f for f in files}
    urls = [f"{config.router_url}/file/{f.id}" for f in files]
    # show a progress bar for each file
    responses = thread_map(
        lambda url: httpx.get(
            url,
            follow_redirects=True,
            verify=False,
            timeout=10,
        ),
        urls,
    )
    for url, response in zip(urls, responses):
        fle = file_map[url.split("/")[-1]]
        file_path = path / fle.path if fle.path else path
        with open(file_path / fle.name, "wb") as f:
            f.write(response.content)
    return


def upload_files(paths: list[Path], root: Path) -> list[str]:
    """Uploads files to the router.

    Args:
        paths (list[Path]): the paths to the files to upload
        root (Path): the root directory of the files
    """
    url = f"{config.router_url}/file"

    files = []
    for path in paths:
        if not path.exists() and path.is_file():
            print(f"File {path} does not exist")
            continue
        content_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
        files.append(
            ("file", (str(path.relative_to(root)), open(path, "rb"), content_type))
        )
    if not files:
        return []
    try:
        response = httpx.post(
            url,
            files=files,
            headers={"X-ETH-ADDRESS": config.node.eth_address},
            verify=False,
            timeout=None,
        )
        if response.status_code != 201:
            print("Failed to upload files")
            print(response.text)
            return []
        return [item["id"] for item in response.json()]
    except Exception as e:
        print("Failed to upload files")
        print(e)
        return []
    finally:
        for _, (_, f, _) in files:
            f.close()
