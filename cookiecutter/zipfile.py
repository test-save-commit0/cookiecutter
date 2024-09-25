"""Utility functions for handling and fetching repo archives in zip format."""
import os
import tempfile
from pathlib import Path
from typing import Optional
from zipfile import BadZipFile, ZipFile
import requests
from cookiecutter.exceptions import InvalidZipRepository
from cookiecutter.prompt import prompt_and_delete, read_repo_password
from cookiecutter.utils import make_sure_path_exists


def unzip(zip_uri: str, is_url: bool, clone_to_dir: 'os.PathLike[str]'='.',
    no_input: bool=False, password: Optional[str]=None):
    """Download and unpack a zipfile at a given URI.

    This will download the zipfile to the cookiecutter repository,
    and unpack into a temporary directory.

    :param zip_uri: The URI for the zipfile.
    :param is_url: Is the zip URI a URL or a file?
    :param clone_to_dir: The cookiecutter repository directory
        to put the archive into.
    :param no_input: Do not prompt for user input and eventually force a refresh of
        cached resources.
    :param password: The password to use when unpacking the repository.
    """
    clone_to_dir = Path(clone_to_dir)
    make_sure_path_exists(clone_to_dir)

    if is_url:
        # Download the file
        response = requests.get(zip_uri)
        response.raise_for_status()
        zip_file = tempfile.NamedTemporaryFile(delete=False, suffix='.zip', dir=clone_to_dir)
        zip_file.write(response.content)
        zip_file.close()
        zip_path = Path(zip_file.name)
    else:
        zip_path = Path(zip_uri)

    # Create a temporary directory to extract the contents
    with tempfile.TemporaryDirectory(dir=clone_to_dir) as temp_dir:
        try:
            with ZipFile(zip_path, 'r') as zip_ref:
                if zip_ref.namelist() and zip_ref.testzip() is not None:
                    raise InvalidZipRepository(f"The zip file {zip_uri} is invalid or corrupt.")

                if password is None and zip_ref.namelist()[0].endswith('/'):
                    password = read_repo_password('Enter the password for the encrypted repository:')

                try:
                    zip_ref.extractall(path=temp_dir, pwd=password.encode() if password else None)
                except RuntimeError as e:
                    if "Bad password" in str(e):
                        raise InvalidZipRepository(f"Invalid password for encrypted repository: {zip_uri}")
                    raise

            # If everything is successful, return the path to the extracted contents
            return Path(temp_dir)

        except BadZipFile:
            raise InvalidZipRepository(f"The zip file {zip_uri} is invalid or corrupt.")

        finally:
            if is_url:
                if no_input:
                    os.unlink(zip_path)
                else:
                    prompt_and_delete(zip_path)
