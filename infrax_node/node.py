import shutil
import subprocess
import time

from loguru import logger

from . import crud
from .exceptions import AppFailedToInstallException, AppFailedToUninstallException
from .types import App, Job, Result
from .util import download_files, get_app_directory, upload_files


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

        (app_path / "input").mkdir(parents=True, exist_ok=True)
        (app_path / "output").mkdir(parents=True, exist_ok=True)

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

    execution_time = 0
    try:
        if not app_path.exists():
            raise ValueError(f"App {job.app_id} is not installed")

        # ensure the input and output directories exist
        input_path = app_path / "input"
        input_path.mkdir(exist_ok=True)
        output_path = app_path / "output"
        output_path.mkdir(exist_ok=True)

        # download the input files
        download_files(job.files or [], input_path)

        # run the app
        start = time.time()

        command = [".venv/bin/python", "main.py"]
        # set the working directory to the app directory
        process_output = subprocess.run(
            command, cwd=app_path, capture_output=True, check=False
        )
        crud.set_job_finishing(job)

        success = True
        error = None
        if process_output.returncode != 0:
            logger.error(
                f"Job {job.id} failed with exit code {process_output.returncode}"
            )
            success = False
            error = f"Job failed with exit code {process_output.returncode}"

        execution_time = time.time() - start

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
    finally:
        # remove the input and output directory contents
        shutil.rmtree(input_path)
        shutil.rmtree(output_path)

    result = Result(
        job_id=job.id,
        execution_time=execution_time,
        success=success,
        error=error,
        file_ids=file_ids,
    )
    crud.upload_result(result)
    crud.set_job_finished(job)
    crud.set_node_idle()
