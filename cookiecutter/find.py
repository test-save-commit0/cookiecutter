"""Functions for finding Cookiecutter templates and other components."""
import logging
import os
from pathlib import Path
from jinja2 import Environment
from cookiecutter.exceptions import NonTemplatedInputDirException
logger = logging.getLogger(__name__)


def find_template(repo_dir: 'os.PathLike[str]', env: Environment) ->Path:
    """Determine which child directory of ``repo_dir`` is the project template.

    :param repo_dir: Local directory of newly cloned repo.
    :param env: Jinja2 Environment object for rendering template variables.
    :return: Relative path to project template.
    """
    repo_dir = Path(repo_dir)
    logger.debug('Searching %s for the project template.', repo_dir)

    # First, check for a cookiecutter.json file in the repo root
    if (repo_dir / 'cookiecutter.json').is_file():
        logger.debug('Found cookiecutter.json at project root level')
        return repo_dir

    # If not found, search for the first directory with a cookiecutter.json file
    for dirpath, dirnames, filenames in os.walk(repo_dir):
        if 'cookiecutter.json' in filenames:
            logger.debug('Found cookiecutter.json in %s', dirpath)
            return Path(dirpath).relative_to(repo_dir)

    # If no cookiecutter.json is found, look for the first directory that's not a repo artifact
    for path in repo_dir.iterdir():
        if path.is_dir() and path.name not in {'.git', '.hg', '.svn', '.bzr'}:
            logger.debug('Treating %s as project template', path)
            return path.relative_to(repo_dir)

    # If we reach here, we couldn't find a valid template directory
    raise NonTemplatedInputDirException(
        'The repo_dir {} is not a valid template directory. '
        'A valid template directory must either have a cookiecutter.json '
        'file or have one or more directories that are not repo artifacts.'
        .format(repo_dir)
    )
