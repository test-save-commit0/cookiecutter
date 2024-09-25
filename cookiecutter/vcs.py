"""Helper functions for working with version control systems."""
import logging
import os
import subprocess
from pathlib import Path
from shutil import which
from typing import Optional
from cookiecutter.exceptions import RepositoryCloneFailed, RepositoryNotFound, UnknownRepoType, VCSNotInstalled
from cookiecutter.prompt import prompt_and_delete
from cookiecutter.utils import make_sure_path_exists
logger = logging.getLogger(__name__)
BRANCH_ERRORS = ['error: pathspec', 'unknown revision']


def identify_repo(repo_url):
    """Determine if `repo_url` should be treated as a URL to a git or hg repo.

    Repos can be identified by prepending "hg+" or "git+" to the repo URL.

    :param repo_url: Repo URL of unknown type.
    :returns: ('git', repo_url), ('hg', repo_url), or None.
    """
    repo_url = repo_url.lower()
    if repo_url.startswith('git+'):
        return 'git', repo_url[4:]
    elif repo_url.startswith('hg+'):
        return 'hg', repo_url[3:]
    elif repo_url.endswith('.git') or 'github.com' in repo_url:
        return 'git', repo_url
    elif 'bitbucket.org' in repo_url:
        return 'hg', repo_url
    return None


def is_vcs_installed(repo_type):
    """
    Check if the version control system for a repo type is installed.

    :param repo_type: The type of repository ('git' or 'hg').
    :return: True if the VCS is installed, False otherwise.
    """
    if repo_type == 'git':
        return which('git') is not None
    elif repo_type == 'hg':
        return which('hg') is not None
    return False


def clone(repo_url: str, checkout: Optional[str]=None, clone_to_dir:
    'os.PathLike[str]'='.', no_input: bool=False):
    """Clone a repo to the current directory.

    :param repo_url: Repo URL of unknown type.
    :param checkout: The branch, tag or commit ID to checkout after clone.
    :param clone_to_dir: The directory to clone to.
                         Defaults to the current directory.
    :param no_input: Do not prompt for user input and eventually force a refresh of
        cached resources.
    :returns: str with path to the new directory of the repository.
    """
    repo_type, repo_url = identify_repo(repo_url)
    if repo_type is None:
        raise UnknownRepoType(f"Couldn't determine repository type for {repo_url}")

    if not is_vcs_installed(repo_type):
        raise VCSNotInstalled(f"{repo_type} is not installed.")

    clone_to_dir = Path(clone_to_dir).resolve()
    make_sure_path_exists(clone_to_dir)

    repo_dir = clone_to_dir / Path(repo_url).stem

    if repo_dir.exists():
        if no_input:
            logger.warning("'%s' directory already exists, deleting it", repo_dir)
            subprocess.check_call([repo_type, 'init', str(repo_dir)])
        else:
            prompt_and_delete(repo_dir)

    if repo_type == 'git':
        clone_cmd = ['git', 'clone', repo_url, str(repo_dir)]
    else:  # hg
        clone_cmd = ['hg', 'clone', repo_url, str(repo_dir)]

    try:
        subprocess.check_output(clone_cmd, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        output = e.output.decode('utf-8')
        if 'Repository not found' in output:
            raise RepositoryNotFound(f"The repository {repo_url} could not be found")
        else:
            raise RepositoryCloneFailed(f"Cloning {repo_url} failed: {output}")

    if checkout:
        if repo_type == 'git':
            checkout_cmd = ['git', 'checkout', checkout]
        else:  # hg
            checkout_cmd = ['hg', 'update', checkout]

        with Path.cwd():
            os.chdir(repo_dir)
            try:
                subprocess.check_output(checkout_cmd, stderr=subprocess.STDOUT)
            except subprocess.CalledProcessError as e:
                output = e.output.decode('utf-8')
                if any(error in output for error in BRANCH_ERRORS):
                    raise RepositoryCloneFailed(
                        f"Couldn't checkout {checkout} in {repo_url}. "
                        f"Error: {output}"
                    )
                else:
                    raise

    return str(repo_dir)
