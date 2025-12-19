#!/usr/bin/env python
import argparse
import concurrent.futures
import datetime
import glob
import hashlib
import importlib
import json
import os
import shlex
import shutil
import string
import subprocess
import sys
import threading

# Version and date
mimk_version = '1.43'
mimk_date = '2025-12-19'

# Terminal detection
def is_terminal():
    return hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()

# Color printing
def color_print(str, col='red', pre=''):
    color = {
        'reset': '\033[0m',
        'red': '\033[91m',
        'green': '\033[92m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'magenta': '\033[95m',
        'cyan': '\033[96m',
        'none': ''
    }
    reset = 'reset'
    if not is_terminal():
        col = 'none'
        reset = 'none'
    print(pre + color[col] + str + color[reset])

# Remove duplicates from list
def unique_list(list):
    seen = set()
    seen_add = seen.add
    return [x for x in list if not (x in seen or seen_add(x))]

# Get SHA-256 hash of file
def sha256file(filename, ext=''):
    hash_sha256 = hashlib.sha256()
    if not os.path.isfile(filename):
        filename += ext
    try:
        with open(filename, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hash_sha256.update(chunk)
    except EnvironmentError:
        return -1
    return hash_sha256.hexdigest()

# Print progress
def print_progress(iteration, total, name='', length=50):
    col = (80 if sys.version_info < (3, 0) else shutil.get_terminal_size()[0]) - length - 17
    percent = ('{0:.1f}').format(100 * (iteration / float(total)))
    filled_length = int(col * iteration // total)
    bar = u'\u2591' * filled_length + ' ' * (col - filled_length)
    print(u'\r{} {}% ({}/{}) {}'.format(bar,percent, iteration, total, name[:length].ljust(length)), end='\r', file=sys.stderr)
    if iteration == total:
        print(file=sys.stderr)

# Evaluate rule by replacing variables
def eval_rule(rule_str, config):
    if rule_str:
        return string.Template(rule_str).safe_substitute(config)

# Make directory
def makedir(pathname):
    if not os.path.exists(pathname):
        os.makedirs(pathname, exist_ok=True)

# Remove file
def remove(filename, ext=''):
    global args
    if not os.path.isfile(filename):
        filename += ext
    if os.path.isfile(filename):
        if not args.quiet:
            color_print('Remove {}'.format(filename), 'magenta')
        os.remove(filename)

# Check if list of files exists
def files_exist(file_list):
    exist_list = []
    for file in file_list:
        exist_list.append(os.path.isfile(file))
    return all(exist_list)

# Issue command
def run_command(command_str, undo=False, iteration=0, total=0, name=''):
    global args
    if command_str:
        # Remember current working directory
        wd = os.getcwd()
        command_list = command_str.split(';');
        for command in command_list:
            if not args.quiet:
                color_print('{}{}'.format('Undo 'if undo else '', command), 'cyan')
            if command[0] == '@':
                # Built-in commands start with @
                param = [x for x in shlex.split(command[1:], posix=False) if x]
                src_list = glob.glob(param[1]) if '*' in param[1] else [param[1]]
                for src_file in src_list:
                    if param[0] == 'copy':
                        if not undo:
                            # Copy file to dir/file
                            shutil.copy2(src_file, param[2])
                        else:
                            # Undo: delete copied file
                            head, tail = os.path.split(src_file)
                            copied_file = os.path.join(param[2], tail)
                            if os.path.isfile(copied_file):
                                os.remove(copied_file)
                    elif param[0] == 'move':
                        if not undo:
                            # Move file to dir/file
                            shutil.copy2(src_file, param[2])
                            os.remove(src_file)
                        else:
                            # Undo: reverse move
                            if os.path.isdir(param[2]):
                                head, tail = os.path.split(src_file)
                                moved_file = os.path.join(param[2], tail)
                                shutil.copy2(moved_file, head)
                                os.remove(moved_file)
                            elif os.path.isfile(param[2]):
                                shutil.copy2(param[2], src_file)
                                os.remove(param[2])
                            elif not os.path.isfile(param[2]):
                                if os.path.isfile(param[2] + '.exe'):
                                    shutil.copy2(param[2] + '.exe', src_file)
                                    os.remove(param[2] + '.exe')
                    elif param[0] == 'rename':
                        if not undo:
                            # Rename file to file
                            os.rename(src_file, param[2])
                        else:
                            # Undo: reverse rename
                            os.rename(param[2], src_file)
                    elif param[0] == 'makedir':
                        if not undo:
                            # Makedir
                            makedir(src_file)
                        else:
                            # Undo: remove dir
                            if os.path.isdir(src_file):
                                shutil.rmtree(src_file)
                    elif param[0] == 'delete':
                        if not undo:
                            # Delete dir/file
                            if os.path.isdir(src_file):
                                os.removedirs(src_file)
                            elif os.path.isfile(src_file):
                                os.remove(src_file)
                            elif not os.path.isfile(src_file):
                                if os.path.isfile(src_file + '.exe'):
                                    os.remove(src_file + '.exe')
                    elif param[0] == 'echo':
                        if not undo:
                            # Echo parameters into file
                            with open(param[1], 'w') as echo_file:
                                print(' '.join(param[2:]), file=echo_file)
                        else:
                            if os.path.isfile(param[1]):
                                os.remove(param[1])
                    elif param[0] == 'append':
                        if not undo:
                            # Append parameters to end of file
                            with open(param[1], 'a') as append_file:
                                print(' '.join(param[2:]), file=append_file)
                        else:
                            if os.path.isfile(param[1]):
                                os.remove(param[1])
                    elif param[0] == 'cat':
                        if not undo:
                            # Concatenate multiple files into one
                            with open(param[1], 'w') as cat_file:
                                for file in param[2:]:
                                    with open(file) as infile:
                                        cat_file.write(infile.read())
                        else:
                            if os.path.isfile(param[1]):
                                os.remove(param[1])
                    elif param[0] == 'cd':
                        # Change directory
                        os.chdir(src_file)
                    elif param[0] == 'ok':
                        if not undo:
                            # Run external command, ignoring errors
                            subprocess.run(' '.join(param[1:]), shell=True)
                    elif param[0] == 'try':
                        if not undo:
                            tries = int(param[1])
                            while tries > 0:
                                # Run external command, trying several times if error occurs
                                ret = subprocess.run(' '.join(param[2:]), shell=True).returncode
                                if ret == 0:
                                    break
                                else:
                                    tries -= 1
                    elif param[0] == 'exists':
                        if not undo:
                            # Run external command if path exists, ignoring errors
                            if os.path.exists(param[1]):
                                subprocess.run(' '.join(param[2:]), shell=True)
                    elif param[0] == 'python':
                        if not undo:
                            # Run python code
                            exec(' '.join(param[1:]))
            else:
                if not undo:
                    # Print progress
                    if total > 0 and is_terminal():
                        print_progress(iteration, total, name)
                    # External command
                    try:
                        ret = subprocess.run(' '.join([x for x in shlex.split(command, posix=False) if x]), shell=True).returncode
                        if not args.debug:
                            if ret < 0:
                                color_print('Command {} terminated by signal {}'.format(command.split(' ')[0], -ret))
                                sys.exit(ret)
                            elif ret > 0:
                                color_print('Command {} returned error {}'.format(command.split(' ')[0], ret))
                                sys.exit(ret)
                    except OSError as e:
                        color_print('Command execution failed: {}'.format(e))
                        sys.exit(1)
        # Restore working directory
        os.chdir(wd)

# Build dependency and source files, using threading
def build_dep_and_src(lock, src_path, idx):
    global config, dep_dir, obj_dir, base_offset, args, target, total, hash_dict, new_hash_dict, obj_list, obj_list_rel

    # Convert separators
    src_path = src_path.replace('/', os.sep)
    src_name  = os.path.basename(src_path)
    iteration = idx + 1

    # Setup paths for dependency, source, and object files
    dep = os.path.splitext(src_path)[0] + '.' + config['DEPEXT']
    obj = os.path.splitext(src_path)[0] + '.' + config['OBJEXT']
    dep_path = os.path.join(dep_dir, dep)
    obj_path = os.path.join(obj_dir, obj)
    makedir(os.path.split(dep_path)[0])
    makedir(os.path.split(obj_path[base_offset:])[0])

    # Remove dependency and object files if remove flag is set
    if args.remove:
        remove(dep_path)
        remove(obj_path)
        if 'REMRULE' in target and target['REMRULE']:
            run_command(eval_rule(target['REMRULE'], config), iteration=iteration, total=total, name=src_name)
        if 'PRERULE' in target and target['PRERULE']:
            run_command(os.path.join(*eval_rule(target['PRERULE'], config).split('/')), undo=True, iteration=iteration, total=total, name=src_name)
        return False

    # Add paths to local thread's config
    local_config = config.copy()
    local_config['SRC_PATH'] = src_path
    local_config['DEP_PATH'] = dep_path
    local_config['OBJ_PATH'] = obj_path

    # Create dependency file if it does not exist
    dependencies = []
    if not os.path.exists(dep_path):
        if 'DEPRULE' in target and target['DEPRULE']:
            command_dep = eval_rule(target['DEPRULE'], local_config)
            run_command(command_dep)

    # Firstly, assume file is modified
    modified = True

    # Get list of dependencies
    if 'DEPRULE' in target and target['DEPRULE']:
        try:
            with open(dep_path) as dep_file:
                dep_str = dep_file.read()
            dependencies = unique_list(dep_str.replace(': ', ' ').replace(' \\', '').replace('\\', '/').replace('\n', '').replace('\r', '').split(' '))

            # Sanity check
            dep_obj_path = os.path.join(os.path.split(src_path)[0], dependencies[0])
            if dep_obj_path != obj:
                color_print('Error: mismatch in dependency file {}: Expected {}, got {}'.format(dep_path, obj, dep_obj_path))
                sys.exit(1)

            # Assume file is not modified unless one dependency file's hash is either missing or has changed
            modified = False

            # Check for all dependencies, starting with second (first is resulting object file)
            for dep_path in dependencies[1:]:
                # Check if file has been modified by checking its SHA-256 hash against a list of known hashes
                hash = sha256file(dep_path)

                if dep_path in hash_dict:
                    if hash_dict[dep_path] != hash:
                        # Different hash, so file has been modified
                        modified = True
                        break
                else:
                    # New file, mark as modified
                    modified = True
                    break
        except:
            pass

    # Check if object file exists
    if not os.path.exists(obj_path):
        modified = True

    if modified:
        # Compile source file
        if 'SRCRULE' in target and target['SRCRULE']:
            command_src = eval_rule(target['SRCRULE'], local_config)
            #with lock:
            run_command(command_src, iteration=iteration, total=total, name=src_name)

        # Add dependencies' hashes to new dictionary
        if dependencies:
            for dep_path in dependencies[1:]:
                hash = sha256file(dep_path)
                if hash != -1:
                    with lock:
                        new_hash_dict[dep_path] = hash

    # After object file has been compiled, append it to list
    with lock:
        obj_list.append(obj_path)
        obj_list_rel.append(obj[base_offset:])

    return modified

# Main program
total_time_start = datetime.datetime.now()
execute_elapsed = total_time_start - total_time_start

# Set config path
config_dir = next((dir for dir in ['mimk', 'cfg'] if os.path.isdir(dir)), '')

# Check init file and create it if it doesn't exist
init_file = os.path.join(config_dir, '__init__.py')
if not os.path.isfile(init_file):
    open(init_file, 'a').close()

# Prevent *.pyc file creation
sys.dont_write_bytecode=True

# Get list of target and config files
target_choices = []
config_choices = []
for file in os.listdir(config_dir):
    if file.endswith('.py'):
        module_file = os.path.splitext(file)[0]
        try:
            module = importlib.import_module(config_dir + ('' if config_dir == '' else '.') + module_file, package=None)
            if hasattr(module, 'targets'):
                target_choices.append(module_file)
            elif hasattr(module, 'config'):
                config_choices.append(module_file)
        except ImportError as e:
            pass

# Default compiler
default_compiler = os.environ.get('MIMK_COMPILER', 'gcc_release')

# Argument parsing
global args
parser = argparse.ArgumentParser(description='mimk - Minimal make')
parser.add_argument('target', choices=target_choices, help='Target configuration file')
parser.add_argument('-a', '--arg', nargs='*', help='Add argument(s)')
parser.add_argument('-c', '--config', choices=config_choices, default=default_compiler, help='Compiler configuration file')
parser.add_argument('-d', '--debug', action='store_true', help='Debug mode, do not stop on errors')
parser.add_argument('-l', '--list', action='store_true', help='List targets')
parser.add_argument('-q', '--quiet', action='store_true', help='Quiet output')
parser.add_argument('-r', '--remove', action='store_true', help='Remove all dependency, object and executable files and undo pre-processing rule')
parser.add_argument('-s', '--source', nargs='*', help='Source folder(s), overrides SRCDIR')
parser.add_argument('-t', '--threads', type=int, choices=range(0, 33), default=0, help='Number of threads (0: default, 1: turn off threading)')
parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
parser.add_argument('-w', '--wipe', action='store_true', help='Wipe build database')
parser.add_argument('-x', '--execute', nargs='*', help='Execute specific target(s)')
parser.add_argument('-y', '--exclude', nargs='*', help='Exclude specific target(s)')
args = parser.parse_args()

# Start message
color_print('mimk - Minimal make v{} ({})'.format(mimk_version, mimk_date), 'yellow')

# Set default config
config = {
    'BUILD':    args.config,
    'DEPPATH':  'dep',
    'OBJPATH':  'obj',
    'SRCEXT':   'c',
    'INCEXT':   'h',
    'DEPEXT':   'd',
    'OBJEXT':   'o'
}

# Import config and target
try:
    config_module = importlib.import_module(config_dir + ('' if config_dir == '' else '.') + args.config, package=None)
    if hasattr(config_module, 'config'):
        config.update(config_module.config)
except ImportError as e:
    color_print('Could not load config file {}.py: {}'.format(os.path.join(config_dir, args.config), e))
    sys.exit(1)
try:
    target_module = importlib.import_module(config_dir + ('' if config_dir == '' else '.') + args.target, package=None)
    targets = target_module.targets
    target_dict = {}
    for item in dir(target_module):
        if not item.startswith('__'):
            target_attr = getattr(target_module, item)
            if isinstance(target_attr, dict):
                if 'TARGET' in target_attr:
                    target_dict[item] = target_attr['TARGET']
    if hasattr(target_module, 'config'):
        config.update(target_module.config)
except ImportError as e:
    color_print('Could not load target file {}.py: {}'.format(os.path.join(config_dir, args.target), e))
    sys.exit(1)
std_dep_path = config['DEPPATH']
std_obj_path = config['OBJPATH']
if not args.quiet:
    color_print('{}'.format(config['BUILD']), 'cyan', 'Build:  ')

# Remove init file
if os.path.isfile(init_file):
    os.remove(init_file)

# List option
if args.list:
    for target in targets:
        if target['TARGET']:
            color_print('{}'.format(target['TARGET']), 'green')
    for target in target_dict:
        color_print('{}'.format(target), 'green')
    sys.exit(0)

# Execute option, also support variable name
if args.execute:
    new_execute_list = []
    for execute in args.execute:
        if execute in target_dict:
            new_execute_list.append(target_dict[execute])
            target_attr = getattr(target_module, execute)
            if isinstance(target_attr, dict):
                if 'TARGET' in target_attr:
                    if not any(target['TARGET'] == target_attr['TARGET'] for target in targets):
                        targets.append(target_attr)
        else:
            color_print('Could not find target {} to execute'.format(execute))
            sys.exit(1)
    args.execute = new_execute_list

# Exclude option
for exclude in args.exclude or []:
    if exclude in target_dict:
        target_attr = getattr(target_module, exclude)
        if isinstance(target_attr, dict):
            if 'TARGET' in target_attr:
                targets.remove(target_attr)
    else:
        color_print('Could not find target {} to exclude'.format(exclude))
        sys.exit(1)
    if args.execute and exclude in args.execute:
        args.execute.remove(exclude)

# Build dir paths
build_dir = os.path.join('build', config['BUILD'])
hashes_file = '.hashes.json'
hashes_path = os.path.join(build_dir, hashes_file)

# Wipe build database
if args.wipe and os.path.isdir(build_dir):
    try:
        os.remove(hashes_path)
        shutil.rmtree(build_dir)
    except Exception:
        pass

# Create build directory
config['BUILD_DIR'] = build_dir
makedir(build_dir)

# Read hashes from file
try:
    hash_dict = json.load(open(hashes_path, 'r'))
except Exception:
    hash_dict = {}

# Print statistics
if args.verbose:
    hash_src = 0
    hash_inc = 0
    hash_trgt = 0
    for hash_key in hash_dict:
        hash_ext = os.path.splitext(hash_key)[1][1:]
        if hash_ext == config['SRCEXT']:
            hash_src += 1
        elif hash_ext == config['INCEXT']:
            hash_inc += 1
        else:
            hash_trgt += 1
    color_print('Loaded hash dictionary with {} entries (src: {}, inc: {}, trgt: {}).'.format(len(hash_dict), hash_src, hash_inc, hash_trgt), 'reset')

# Process targets
previous = []
for index, target in enumerate(targets):
    # If defined, target extensions override config extensions
    if 'SRCEXT' in target:
        config['SRCEXT'] = target['SRCEXT']
    if 'INCEXT' in target:
        config['INCEXT'] = target['INCEXT']
    if 'DEPEXT' in target:
        config['DEPEXT'] = target['DEPEXT']
    if 'OBJEXT' in target:
        config['OBJEXT'] = target['OBJEXT']
    config['DEPPATH'] = target['DEPPATH'] if 'DEPPATH' in target else std_dep_path
    config['OBJPATH'] = target['OBJPATH'] if 'OBJPATH' in target else std_obj_path

    # Dep and obj sub-folders
    dep_dir = os.path.join(build_dir, config['DEPPATH'])
    obj_dir = os.path.join(build_dir, config['OBJPATH'])

    # Wipe object folder
    if args.wipe and os.path.isdir(obj_dir):
        try:
            shutil.rmtree(obj_dir)
        except Exception:
            pass

    # Create dep and obj sub-folders
    config['DEP_DIR'] = dep_dir
    makedir(dep_dir)
    config['OBJ_DIR'] = obj_dir
    makedir(obj_dir)

    # Check target
    if 'TARGET' not in target:
        color_print('No target defined in section #{} of file {}.py'.format(str(index), args.target))
        continue

    # Arg option
    arg = args.arg if args.arg else []
    config['ARGS'] = ' '.join(arg)

    # Copy target names (i.e., all names starting with 'TARGET') to config
    config.update([[key, value] for key, value in target.items() if key.startswith('TARGET')])

    # Execute only specific target(s)
    if args.execute:
        if target['TARGET'] not in args.execute:
            continue
    color_print('{}'.format(target['TARGET']), 'green', 'Target: ')

    # Create target path and add to current config
    target_path = os.path.join(build_dir, target['TARGET'])
    target_path_dict = build_dir + '/' + target['TARGET']
    config['TARGET_PATH'] = target_path

    # Source folder
    base_offset = 0
    if 'SRCBASE' in target:
        config['SRCBASE'] = target['SRCBASE']
        base_offset = len(target['SRCBASE']) + 1
    if 'SRCDIR' in target:
        config['SRCDIR'] = target['SRCDIR']
    if args.source:
        target['SRCDIR'] = ' '.join(args.source)
        config['SRCDIR'] = target['SRCDIR']

    # Run pre-processing rule
    if not args.remove:
        if 'PRERULE' in target and target['PRERULE']:
            run_command(os.path.join(*eval_rule(target['PRERULE'], config).split('/')))

    # Get source files list
    src_files = []
    if getattr(target_module, 'src_files', None):
        # Get list of source files from target configuration
        src_files = target_module.src_files
        if not files_exist(src_files):
            color_print('At least one source file could not be found: {}'.format(src_files))
            continue
    elif 'SRCDIR' in target:
        # Get list of all SRCEXT files from SRCDIR
        try:
            for src_dir in target['SRCDIR'].split(' '):
                if 'SRCBASE' in target:
                    src_dir = os.path.join(target['SRCBASE'], src_dir)
                src_files.extend([os.path.join(src_dir, fn) for fn in os.listdir(src_dir) if fn.endswith('.' + config['SRCEXT'])])
        except Exception:
            pass
        if not src_files:
            color_print('No source files found matching pattern ({})*.{}'.format(target['SRCDIR'], config['SRCEXT']))
            continue

    if not args.quiet:
        color_print('Processing {} source files...'.format(len(src_files)), 'reset')

    # Compile all files
    new_hash_dict = {}
    obj_list = []
    obj_list_rel = []
    modified_any = False
    total = len(src_files)

    # Create lock
    lock = threading.Lock()

    # Set number of threads
    threads = args.threads if args.threads > 0 else None
    if 'THREADS' in target:
        threads = target['THREADS'] if target['THREADS'] > 0 else None
    if args.remove:
        threads = 1

    # Concurrently get source file dependencies and compile source files
    with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
        futures = []
        for idx, src_path in enumerate(src_files):
            futures.append(executor.submit(build_dep_and_src, lock=lock, src_path=src_path, idx=idx))

        for future in concurrent.futures.as_completed(futures):
            modified = future.result()
            if modified:
                # Set modified_any flag
                modified_any = True

    # Add object list to current config
    config['OBJ_LIST'] = ' '.join(obj_list)
    config['OBJ_LIST_REL'] = ' '.join(obj_list_rel)

    # Assume file is not modified unless one dependency file's hash is either missing or has changed
    modified = False

    # Handle additional dependencies
    if 'DEPENDS' in target:
        config['DEPENDS'] = eval_rule(target['DEPENDS'], config)
        depends = config['DEPENDS'].split(' ')
        for dep in depends:
            try:
                hash = sha256file(dep, '.exe')
                if hash == -1:
                    hash_dict.pop(dep, None)
                elif dep in hash_dict:
                    if hash_dict[dep] != hash or dep in previous:
                        modified = True
                        new_hash_dict[dep] = hash
                else:
                    new_hash_dict[dep] = hash
            except Exception:
                hash = ''
                modified = True

    if target_path_dict in hash_dict:
        # Check if target file has been modified by checking its SHA-256 hash against a list of known hashes
        try:
            hash = sha256file(target_path, '.exe')
            if hash_dict[target_path_dict] != hash:
                modified = True
        except Exception:
            hash = ''
            modified = True
    else:
        modified = True

    # Handle target file
    if args.remove:
        # Remove target file
        remove(target_path, '.exe')
    else:
        # Create target file
        if modified or modified_any:
            if 'OBJRULE' in target and target['OBJRULE']:
                run_command(eval_rule(target['OBJRULE'], config))

            # Append hash of newly generated file to list
            try:
                hash = sha256file(target_path, '.exe')
                if hash != -1:
                    hash_dict[target_path_dict] = hash
                    previous.append(target_path_dict)
            except Exception:
                pass

    # Update hash dictionary with new hashes
    hash_dict.update(new_hash_dict);

    # Remove hash dictionary
    if args.remove:
        hash_dict = {}

    # Write hash file
    json.dump(hash_dict, open(os.path.join(build_dir, hashes_file), 'w'), indent=1, sort_keys=True)

    # Run executable
    if not args.remove:
        if 'EXERULE' in target and target['EXERULE']:
            time_start = datetime.datetime.now()
            run_command(os.path.join(*eval_rule(target['EXERULE'], config).split('/')))
            elapsed = datetime.datetime.now() - time_start
            execute_elapsed += elapsed
            if not args.quiet:
                color_print('Execute: {}'.format(str(elapsed)), 'green')

        # Run post-processing rule
        if 'PSTRULE' in target and target['PSTRULE']:
            run_command(os.path.join(*eval_rule(target['PSTRULE'], config).split('/')))

# End message
if not args.quiet:
    total_elapsed = datetime.datetime.now() - total_time_start
    compile_elapsed = total_elapsed - execute_elapsed
    compile_str = str(compile_elapsed)
    if '.' not in compile_str:
        compile_str += '.000000'
    execute_str = str(execute_elapsed)
    if '.' not in execute_str:
        execute_str += '.000000'
    color_print('Timings:', 'yellow')
    color_print('Compile: {} ({:2.1f}%)'.format(compile_str, (compile_elapsed.total_seconds() * 100) / total_elapsed.total_seconds()), 'green')
    color_print('Execute: {} ({:2.1f}%)'.format(execute_str, (execute_elapsed.total_seconds() * 100) / total_elapsed.total_seconds()), 'green')
    color_print('Total:   {}'.format(str(total_elapsed)), 'green')
color_print('Done.', 'yellow')
