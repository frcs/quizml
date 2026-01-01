import os
import yaml
import logging
from string import Template
import pathlib

import quizml.cli.filelocator as filelocator
from quizml.exceptions import QuizMLConfigError

def get_config(args):
    """
    returns the yaml data of the config file
    """

    if args.config:
        config_file = os.path.realpath(os.path.expanduser(args.config))
    else:
        try:
            config_file = filelocator.locate.path('quizml.cfg')
        except FileNotFoundError:
            raise QuizMLConfigError("Could not find config file quizml.cfg")
   
    logging.info(f"using config file:{config_file}")
    
    try:
        with open(config_file) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
    except yaml.YAMLError as err:
        s = f"Something went wrong while parsing the config file at:\n {config_file}\n\n {str(err)}"
        raise QuizMLConfigError(s)

    config['yaml_filename'] = args.yaml_filename
    
    return config

def get_required_target_names_set(name, targets):
    """resolves the set of the names of the required targets
    """
    if not name:
        return {}
    
    if isinstance(name, list):
        input_set = set(name)
    else:
        input_set = {name}
    required_set = input_set
    for target in targets:
        if (target.get('name', '') in input_set) and ('dep' in target):
            dep_set = get_required_target_names_set(
                target['dep'], targets)
            required_set = required_set.union(dep_set)
            
    return required_set


def get_target_list(args, config, yaml_data):
    """
    gets the list of target templates from config['targets'] and
      * resolves the absolute path of each template
      * also resolves $inputbasename 
    """
    
    (basename, _) = os.path.splitext(config['yaml_filename'])
    
    subs = {'inputbasename': basename}
    filenames_to_resolve = ['template', 'html_css', 'html_pre', 'latex_pre']
    files_to_read_now = ['html_css', 'html_pre', 'latex_pre']

    # if CLI provided specific list of required target names
    # we compile a list of all the required target names
    target_names = args.target
    if not target_names:
        target_names = config.get('default_targets')

    required_target_names_set = get_required_target_names_set(
        target_names, config['targets'])
   
    if target_names:
        logging.info(f"requested target list:{target_names}")
        logging.info(f"required target list:{required_target_names_set}")

    target_list = []
    
    for t in config['targets']:
        t_name = t.get('name', '')
        dep_name = t.get('dep', '')
        
        if (required_target_names_set and t_name not in required_target_names_set):
            continue

        target = {}

        # resolves $inputbasename
        for key, val in t.items():
            target[key] = Template(val).substitute(subs)

        # resolves relative path for all files
        for key in filenames_to_resolve:        
            if key in target:
                target[key] = filelocator.locate.path(t[key])
                logging.info(f"'{target['descr']}:{key}'"
                             f" expands as '{target[key]}'")

        # replaces values with actual file content for some keys
        for key in files_to_read_now:
            if key in target:
                file_path = target[key]
                contents = pathlib.Path(file_path).read_text()
                target[key] = contents
        
        # add target to list
        target_list.append(target)

        # add preamble key if defined in the QuizMLYaml header
        if 'fmt' in target:
            target['user_pre'] = yaml_data['header'].get('_latexpreamble', '')

    return target_list
