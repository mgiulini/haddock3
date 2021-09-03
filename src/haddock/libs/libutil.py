"""General utilities."""
import logging
import shutil
from copy import deepcopy
from os import cpu_count

from haddock.error import SetupError


logger = logging.getLogger(__name__)


def get_result_or_same_in_list(function, value):
    """
    Return the result if True or the value within a list.

    Applies `function` to `value` and returns its result if it evaluates
    to True. Otherwise, return the value within a list.

    `function` should receive a single argument, the `value`.
    """
    result = function(value)
    return result if result else [value]


def make_list_if_string(item):
    if isinstance(item, str):
        return [item]
    return item


def copy_files_to_dir(paths, directory):
    """
    Copy files to directory.

    Parameters
    ----------
    paths : iterable of paths
        Source files.

    directory : path
        Where to copy files to.
    """
    for path in paths:
        shutil.copy(path, directory)


def zero_fill(number, digits=2):
    """Makes a number string zero filled to the left."""
    return str(number).zfill(digits)


def remove_folder(folder):
    """Removes a folder if it exists."""
    if folder.exists():
        logger.warning(f'{folder} exists and it will be REMOVED!')
        shutil.rmtree(folder)


def remove_dict_keys(d, keys):
    """
    Remove `keys` from dictionary (`d`).

    Return
    ------
    dict
        A copy of `d` dictionary without the `keys`.
    """
    return {k: deepcopy(v) for k, v in d.items() if k not in keys}


def parse_ncores(n=None, njobs=None, max_cpus=None):
    """
    Check the number of cores according to HADDOCK3 architecture.

    Parameters
    ----------
    n : int or str
        The desired number of cores. If `None` is given, returns the
        maximum number of cores allowed, see `max_cpus`.

    njobs : int
        The number of jobs to execute. Optional. The number of cores
        will be compared to `njobs`.

    max_cpus : int
        The maximum number of CPUs allowed. If not specified, defaults
        to the available CPUs minus one.

    Raises
    ------
    SetupError
        If `n` is not positive or not convertable to `int`.

    Returns
    -------
    int
        A correct number of cores according to specifications.
    """
    max_cpus = max_cpus or cpu_count() - 1

    if n is None:
        return max_cpus

    try:
        n = int(n)
    except (TypeError, ValueError) as err:
        _msg = f"`n` must be `int` or `int`-convertable `str`: {n!r} given."
        raise SetupError(_msg) from err

    if n < 1:
        _msg = "`n` is not positive, this is not possible."
        raise SetupError(_msg)

    if njobs:
        ncores = min(n, njobs, max_cpus)
        logger.info(
            f"Selected {ncores} cores to process {njobs} jobs, with {max_cpus} "
            "maximum available cores."
            )
        return ncores

    logger.info(f"`njobs` not specified, evaluating initial value {n}...")
    ncores = min(n, max_cpus)
    logger.info(f"Selected {ncores} for a maximum of {max_cpus} CPUs")
    return ncores