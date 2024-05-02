import mimetypes
from pathlib import Path

import httpx
from tqdm.contrib.concurrent import thread_map

from .config import config
from .types import File


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
        return httpx.post(url, files=files, verify=False)
