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
from .types import App, File, Job, Result


def install_app(app: App) -> None:  # sourcery skip: extract-method
    """Downloads the app and its dependencies.
    Apps use python 3.10 and pip to install dependencies into a
    virtual environment in the app directory.

    Args:
        app (App): the app to install
    """
    crud.set_node_busy()

    # mkdir the app directory and give read, write, and execute
    # permissions to the current user
    app_path = get_app_directory() / app.id

    if app_path.exists():
        logger.info(f"App {app.name} is already installed")
        crud.add_app(app)
        crud.set_node_idle()
        return

    logger.info(f"Installing app {app.name}")

    try:
        app_path.mkdir(parents=True, exist_ok=True, mode=0o777)

        download_files(app.files, app_path)

        # create a virtual environment
        subprocess.run(["python", "-m", "venv", app_path / ".venv"])

        if (app_path / "requirements.txt").exists():
            # install the app dependencies
            subprocess.run(
                [".venv/bin/pip", "install", "-r", app_path / "requirements.txt"]
            )
            logger.info(f"App {app.name} has no dependencies")
    except Exception as e:
        logger.error(f"Failed to install app {app.name}: {e}")
        crud.report_failed_app_install(app, AppFailedToInstallException(str(e)))
    crud.add_app(app)
    crud.set_node_idle()


def uninstall_app(app: App) -> None:
    """Removes the app and its dependencies.

    Args:
        app (App): the app to remove
    """
    crud.set_node_busy()
    app_path = get_app_directory() / app.id
    if not app_path.exists():
        crud.set_node_idle()
        return
    logger.info(f"Uninstalling app {app.name}")
    try:
        # remove the app directory, which also removes the virtual environment
        if app_path.exists():
            subprocess.run(["rm", "-rf", app_path])
    except Exception as e:
        logger.error(f"Failed to uninstall app {app.name}: {e}")
        crud.report_failed_app_uninstall(app, AppFailedToUninstallException(str(e)))
    crud.remove_app(app)
    crud.set_node_idle()


def run_job(job: Job):
    """Runs the installed app with the given job.

    Args:
        job (Job): the job to run
    """
    logger.info(f"Running job {job.id} with app {job.app_id}")
    app_path = get_app_directory() / job.app_id

    start_time = 0
    end_time = 0
    try:
        if not app_path.exists():
            raise ValueError(f"App {job.app_id} is not installed")

        # ensure the input and output directories exist
        input_path = app_path / "input"
        shutil.rmtree(input_path)
        input_path.mkdir(exist_ok=True)

        output_path = app_path / "output"
        shutil.rmtree(output_path)
        output_path.mkdir(exist_ok=True)

        # download the input files
        download_files(job.files or [], input_path)

        command = [".venv/bin/python", "main.py"]

        # add the job arguments, if any
        kwargs = job.meta.get("kwargs", {})
        if isinstance(kwargs, dict):
            for key, value in kwargs.items():
                command.extend((f"--{key}", value))

        # run the app in the app directory
        start_time = time.time()
        process_output = subprocess.run(
            command, cwd=app_path, capture_output=True, check=False
        )
        end_time = time.time()

        success = True
        error = None
        if process_output.returncode != 0:
            logger.error(
                f"Job {job.id} failed with exit code {process_output.returncode}"
            )
            success = False
            error = f"Job failed with exit code {process_output.returncode}"

        crud.set_job_finishing(job)

        # ensure the output directory exists
        output_path = app_path / "output"
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
            end_time = time.process_time()
    finally:
        # remove the input and output directory contents
        shutil.rmtree(input_path)
        shutil.rmtree(output_path)

    stdout_str = process_output.stdout.decode() or ""
    stderr_str = process_output.stderr.decode() or ""
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
        lambda url: httpx.get(url, follow_redirects=True, verify=False),
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
    """
    responses = thread_map(lambda path: upload_file(path, root), paths)
    for response in responses:
        response.raise_for_status()
    return [response.json()["id"] for response in responses]


def upload_file(path: Path, root: Path) -> httpx.Response:
    """Uploads a file to the router.

    Args:
        path (Path): the path to the file to upload
    """
    url = f"{config.router_url}/file"
    content_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
    with open(path, "rb") as f:
        files = {
            "file": (path.name, f, content_type),
            "path": (None, str(path.relative_to(root)), "text/plain"),
        }
        if path.parent == root:
            del files["path"]
        return httpx.post(
            url,
            files=files,
            headers={"ethaddress": config.node.eth_address},
            verify=False,
        )
