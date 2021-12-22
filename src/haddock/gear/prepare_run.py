"""Logic pertraining to preparing the run files and folders."""
import importlib
import shutil
import sys
from contextlib import contextmanager
from functools import wraps
from pathlib import Path
from copy import deepcopy
from pprint import pprint

from haddock import contact_us, haddock3_source_path, log
from haddock import toppar_path
from haddock.core.exceptions import ConfigurationError, ModuleError
from haddock.gear.config_reader import get_module_name, read_config
from haddock.gear.greetings import get_goodbye_help
from haddock.gear.parameters import config_mandatory_general_parameters
from haddock.gear.restart_run import remove_folders_after_number
from haddock.libs.libutil import (
    make_list_if_string,
    remove_dict_keys,
    zero_fill,
    )
from haddock.modules import (
    general_parameters_affecting_modules,
    modules_category,
    )


@contextmanager
def config_key_error():
    """Raise ConfigurationError on KeyError."""
    try:
        yield
    except KeyError as err:
        msg = f"Expected {err.args[0]!r} parameter in configuration file."
        log.debug(err)
        raise ConfigurationError(msg) from err


def with_config_error(func):
    """Add config error context."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        with config_key_error():
            return func(*args, **kwargs)
    return wrapper


def setup_run(workflow_path, restart_from=None):
    """
    Set up HADDOCK3 run.

    This function performs several actions in a pipeline.

    #1 : validate the parameter TOML file
    #2 : convert strings to paths where it should
    #3 : copy molecules to topology key
    #4 : validate haddock3 modules params names against defaults
    #5 : remove folder from previous runs if run folder name overlaps
    #6 : create the needed folders/files to start the run
    #7 : copy additional files to run folder

    Parameters
    ----------
    workflow_path : str or pathlib.Path
        The path to the configuration file.

    erase_previous : bool
        Whether to erase the previous run folder and reprare from
        scratch. Defaults to `True`.

    Returns
    -------
    tuple of two dicts
        A dictionary with the parameters for the haddock3 modules.
        A dictionary with the general run parameters.
    """
    params = read_config(workflow_path)
    check_mandatory_argments_are_present(params)
    clean_rundir_according_to_restart(params['run_dir'], restart_from)
    copy_molecules_to_topology(params)
    _modules_keys = identify_modules(params)
    # separate general from modules parameters
    general_params = remove_dict_keys(params, _modules_keys)
    modules_params = remove_dict_keys(params, list(general_params.keys()))
    validate_modules_params(modules_params)
    check_if_modules_are_installed(modules_params)

    data_dir = create_data_dir(general_params["run_dir"])
    new_mp = copy_input_files_to_data_dir(data_dir, modules_params)

    #general_params["cwd"] = general_params["run_dir"]


    #shutil.copytree(toppar_path, Path(general_params["run_dir"], 'toppar'))

    #with working_directory(general_params["run_dir"]):

    #new_config = {**general_params, **new_mp}
    #new_config_path = Path(data_dir, 'config.cfg')
    #save_config(new_config, new_config_path)

    # validates the configuration file

    #validate_params(params)

    # these are copied because molecules is a general parameter just to
    # facilitate users experience, but in fact 'molecules' is a
    # parameter from topology

    # separates modules headers from general parameters
    # this is done by comparing headers to the modules categories








    # return the modules' parameters and other parameters that may serve
    # the workflow, the "other parameters" can be expanded in the future
    # by a function if needed
    print(general_params)
    #sys.exit()
    return new_mp, general_params


def validate_params(params):
    """
    Validate the parameter file.

    #1 : checks for mandatory parameters
    #2 : checks for correct modules
    """
    check_mandatory_argments_are_present(params)
    validate_modules_names(params)


def check_mandatory_argments_are_present(params):
    """Confirm order key exists in config."""
    for arg in config_mandatory_general_parameters:
        if arg not in params:
            _msg = (
                f"Parameter {arg!r} is not defined in the configuration file. "
                "Please refer to DOCUMENTATION-LINK for more information."
                )
            raise ConfigurationError(_msg)
    return


@with_config_error
def validate_modules_names(params):
    """Validate all modules names are spelled correctly."""
    keys = \
        set(params) \
        - set(config_mandatory_general_parameters) \
        - set(general_parameters_affecting_modules)

    for module in keys:
        if get_module_name(module) not in modules_category.keys():
            _msg = (
                f"Module {module} not found in HADDOCK3 library. "
                "Please refer to the list of available modules at: "
                "DOCUMENTATION-LINK"
                )
            raise ConfigurationError(_msg)


@with_config_error
def validate_modules_params(modules_params):
    """
    Validate individual parameters for each module.

    Raises
    ------
    ConfigError
        If there is any parameter given by the user that is not defined
        in the defaults.cfg of the module.
    """
    for module_name, args in modules_params.items():
        _module_name = get_module_name(module_name)
        pdef = Path(
            haddock3_source_path,
            'modules',
            modules_category[_module_name],
            _module_name,
            'defaults.cfg',
            ).resolve()

        defaults = read_config(pdef)
        if not defaults:
            return

        diff = set(args.keys()) \
            - set(defaults.keys()) \
            - set(config_mandatory_general_parameters) \
            - general_parameters_affecting_modules

        if diff:
            _msg = (
                'The following parameters do not match any expected '
                f'parameters for module {module_name!r}: {diff}.'
                )
            raise ConfigurationError(_msg)


def check_if_modules_are_installed(params):
    """Validate if third party-libraries are installed."""
    for module_name in params.keys():
        module_import_name = '.'.join([
            'haddock',
            'modules',
            modules_category[get_module_name(module_name)],
            get_module_name(module_name),
            ])
        module_lib = importlib.import_module(module_import_name)
        try:
            module_lib.HaddockModule.confirm_installation()
        except Exception as err:
            _msg = (
                'A problem occurred while assessing if module '
                f'{module_name!r} is installed in your system. Have you '
                'installed the packages required to run this module? If '
                f'yes, write us at {contact_us!r} describing your system '
                'and the problems you are facing. If not, please install '
                'the required packages to use the module.'
                )
            raise ModuleError(_msg) from err


def convert_params_to_path(params):
    """Convert parameters to path."""
    convert_molecules_to_path(params)
    convert_run_dir_to_path(params)
    return


@with_config_error
def convert_molecules_to_path(params):
    """
    Convert molecules path strings to Python Paths.

    And... convert `molecules` in `params` to a dictionary where keys
    are `key` + `sep` + enumerate(`start`), and values are the new Path
    values.
    """
    molecules = make_list_if_string(params['molecules'])
    params['molecules'] = [Path(i).resolve() for i in molecules]
    return


@with_config_error
def convert_run_dir_to_path(params):
    """Convert run directory value to Python Path."""
    project_dir = Path(params['run_dir'])
    params['run_dir'] = project_dir.resolve()
    return


@with_config_error
def create_data_dir(run_dir):
    """
    Create initial files for HADDOCK3 run.

    Returns
    -------
    pathlib.Path
        A path referring only to 'data'.
    """
    data_dir = Path(run_dir, 'data')
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


#def copy_molecules_to_begin_folder(
#        molecules,
#        begin_dir,
#        mol='mol',
#        sep='_',
#        start=1,
#        ):
#    """Copy molecules to run directory begin folder."""
#    for i, mol_path in enumerate(molecules, start=start):
#        mol_id = f"{mol}{sep}{i}.pdb"
#        begin_mol = Path(begin_dir, mol_id).resolve()
#        shutil.copy(mol_path, begin_mol)


@with_config_error
def copy_molecules_to_topology(params):
    """Copy molecules to mandatory topology module."""
    params['topoaa']['molecules'] = list(map(Path, params['molecules']))


@with_config_error
def copy_ambig_files(module_params, directory):
    """Copy ambiguity table files to run directory and updates new path."""
    for step, step_dict in module_params.items():
        for key, value in step_dict.items():
            if key == 'ambig':
                ambig_f = Path(value).resolve()
                new_loc = Path(directory, step, 'ambig.tbl')
                new_loc.parent.mkdir(exist_ok=True)

                try:
                    shutil.copy(ambig_f, new_loc)
                except FileNotFoundError:
                    _msg = f'Stage: {step} ambig file {ambig_f.name} not found'
                    raise ConfigurationError(_msg)

                step_dict[key] = new_loc

def copy_input_files_to_data_dir(data_dir, modules_params):
    """Copy files to data directory."""
    new_mp = deepcopy(modules_params)
    # this line must be synchronized with create_data_dir()
    rel_data_dir = data_dir.name

    for i, molecule in enumerate(modules_params['topoaa']['molecules']):
        end_path = Path(data_dir, '00_topoaa')
        end_path.mkdir(parents=True, exist_ok=True)
        name = Path(molecule).name
        shutil.copy(molecule, Path(end_path, name))
        new_mp['topoaa']['molecules'][i] = Path(rel_data_dir, '00_topoaa', name)


    #other_modules = list(modules_params.items())[1:]  # don't use topology
    for i, (module, params) in enumerate(modules_params.items(), start=1):
        end_path = Path(f'{zero_fill(i)}_{get_module_name(module)}')
        pf = Path(data_dir, end_path)
        pf.mkdir(exist_ok=True)
        for parameter, value in params.items():
            if parameter.endswith('_fname'):
                name = Path(value).name
                shutil.copy(value, Path(pf, name))
                new_mp[module][parameter] = Path(rel_data_dir, end_path, name)
    pprint(new_mp)
    return new_mp


def clean_rundir_according_to_restart(run_dir, restart_from=None):
    if restart_from is None:
        # prepares the run folders
        _p = Path(run_dir)
        if _p.exists() and len(list(_p.iterdir())) > 0:
            log.info(
                f"The `run_dir` {str(_p)!r} exists and is not empty. "
                "We can't work on it unless you provide the `--restart` "
                "option. If you want to start a run from scratch, "
                "indicate a new folder, or manually delete this one first, "
                "or use `--restart 0`."
                )
            sys.exit(get_goodbye_help())

    else:
        remove_folders_after_number(run_dir, restart_from)


def identify_modules(params):
    """Identify keys (headings) belogging to HADDOCK3 modules."""
    modules_keys = [
        k
        for k in params.keys()
        if get_module_name(k) in modules_category
        ]
    return modules_keys
