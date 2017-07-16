#!/usr/bin/env python
import argparse
import datetime
import glob
import hashlib
import importlib
import json
import os
import shutil
import string
import subprocess


# Remove duplicates from list
def unique_list(list):
    seen = set()
    seen_add = seen.add
    return [x for x in list if not (x in seen or seen_add(x))]

# Get SHA-256 hash of file
def sha256file(filename, ext=''):
    hash_sha256 = hashlib.sha256()
    if not os.path.isfile(filename):
        filename = filename + ext
    with open(filename, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()


# Evaluate rule by replacing variables
def eval_rule(rule_str):
    if rule_str:
        return string.Template(rule_str).safe_substitute(config)


# Make directory
def makedir(pathname):
    if not os.path.exists(pathname):
        os.makedirs(pathname)


# Remove file
def remove(filename, ext=''):
    if args.verbose:
        print('\033[95mRemove {}\033[0m'.format(filename))
    if not os.path.isfile(filename):
        filename = filename + ext
    if os.path.isfile(filename):
        os.remove(filename)


# Check if list of files exists
def files_exist(file_list):
    exist_list = []
    for file in file_list:
        exist_list.append(os.path.isfile(file))
    return all(exist_list)


# Issue command
def run_command(command_str):
    if command_str:
        # Remember current working directory
        wd = os.getcwd()
        command_list = command_str.split(';');
        for command in command_list:
            if args.verbose:
                print('\033[96m{}\033[0m'.format(command))
            if command[0] == '@':
                # Internal commands start with @
                param = command[1:].split(' ')
                src_list = glob.glob(param[1]) if '*' in param[1] else [param[1]]
                for src_file in src_list:
                    if param[0] == 'copy':
                        # Copy file to dir/file
                        shutil.copy2(src_file, param[2])
                    elif param[0] == 'move':
                        # Move file to dir/file
                        shutil.copy2(src_file, param[2])
                        os.remove(src_file)
                    elif param[0] == 'rename':
                        # Rename file to file
                        os.rename(src_file, param[2])
                    elif param[0] == 'makedir':
                        # Makedir
                        makedir(src_file)
                    elif param[0] == 'delete':
                        # Delete dir/file
                        if os.path.isfile(src_file):
                            os.remove(src_file)
                        elif os.path.isdir(src_file):
                            os.removedirs(src_file)
                    elif param[0] == 'cd':
                        # Change directory
                        os.chdir(src_file)
                    elif param[0] == 'ok':
                        # Run external command, ignoring errors
                        subprocess.call(src_file, shell=True)
            else:
                # External command
                try:
                    ret = subprocess.call(command, shell=True)
                    if ret < 0:
                        print('\033[91mCommand {} terminated by signal {}\033[0m'.format(command.split(' ')[0], -ret))
                        quit()
                    elif ret > 0:
                        print('\033[91mCommand {} returned error {}\033[0m'.format(command.split(' ')[0], ret))
                        quit()
                except OSError as e:
                    print('\033[91mCommand execution failed: {}\033[0m'.format(e))
                    quit()
        # Restore working directory
        os.chdir(wd)


# Main program
mimk_version = '1.5'
mimk_date = '2017-07-16'
global args
parser = argparse.ArgumentParser(description='mimk - Minimal make')
parser.add_argument('target', help='Target configuration file')
parser.add_argument('-c', '--config', default='gcc_release', help='Compiler configuration file')
parser.add_argument('-r', '--remove', action='store_true', help='Remove all dependency, object and executable files')
parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
args = parser.parse_args()

# Start message
print('\033[93mmimk - Minimal make v{} ({})\033[0m'.format(mimk_version, mimk_date))

# Set config path
config_dir = 'mimk'
if not os.path.isdir(config_dir):
    config_dir = 'cfg'
    if not os.path.isdir(config_dir):
        config_dir = ''

# Check init file and create it if it doesn't exist
init_file = os.path.join(config_dir, '__init__.py')
if not os.path.isfile(init_file):
    open(init_file, 'a').close()

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
    print('\033[91mCould not load config file {}.py: {}\033[0m'.format(os.path.join(config_dir, args.config), e))
    quit()
try:
    target_module = importlib.import_module(config_dir + ('' if config_dir == '' else '.') + args.target, package=None)
    targets = target_module.targets
    if hasattr(target_module, 'config'):
        config.update(target_module.config)
except ImportError as e:
    print('\033[91mCould not load target file {}.py: {}\033[0m'.format(os.path.join(config_dir, args.target), e))
    quit()
if args.verbose:
    print('Build:  \033[96m{}\033[0m'.format(config['BUILD']))

# Remove init file
if os.path.isfile(init_file):
    os.remove(init_file)
    os.remove(init_file + 'c')

# Create build directory and sub-folders
build_dir = os.path.join('build', config['BUILD'])
config['BUILD_DIR'] = build_dir
makedir(build_dir)
dep_dir = os.path.join(build_dir, config['DEPPATH'])
makedir(dep_dir)
obj_dir = os.path.join(build_dir, config['OBJPATH'])
makedir(obj_dir)

# Read hashes from file
hashes_file = '.hashes.json'
try:
    hash_dict = json.load(open(os.path.join(build_dir, hashes_file), 'r'))
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
    print('Loaded hash dictionary with {} entries (src: {}, inc: {}, trgt: {}).'.format(len(hash_dict), hash_src, hash_inc, hash_trgt))

# Process targets
for index, target in enumerate(targets):
    # Check target
    if 'TARGET' not in target:
        print('\033[91mNo target defined in section #{} of file {}.py\033[0m'.format(str(index), args.target))
        continue
    config['TARGET'] = target['TARGET']
    print('Target: \033[92m{}\033[0m'.format(target['TARGET']))

    # Create target path and add to current config
    target_path = os.path.join(build_dir, target['TARGET'])
    target_path_dict = build_dir + '/' + target['TARGET']
    config['TARGET_PATH'] = target_path

    # Run pre-processing rule
    if 'SRCDIR' in target:
        config['SRCDIR'] = target['SRCDIR']
    if not args.remove:
        if 'PRERULE' in target:
            run_command(os.path.join(*eval_rule(target['PRERULE']).split('/')))

    # Get source files list
    src_files = []
    if getattr(target_module, 'src_files', None):
        # Get list of source files from target configuration
        src_files = target_module.src_files
        if not files_exist(src_files):
            print('\033[91mAt least one source file could not be found: {}\033[0m'.format(src_files))
            continue
    elif 'SRCDIR' in target:
        # Get list of all SRCEXT files from SRCDIR
        try:
            for src_dir in target['SRCDIR'].split(' '):
                src_files.extend([os.path.join(src_dir, fn) for fn in os.listdir(src_dir) if fn.endswith('.' + config['SRCEXT'])])
        except Exception:
            pass
        if not src_files:
            print('\033[91mNo source files found matching pattern ({})*.{}\033[0m'.format(target['SRCDIR'], config['SRCEXT']))
            continue

    if args.verbose:
        print('Processing {} source files...'.format(len(src_files)))

    # Compile all files
    new_hash_dict = {}
    obj_list = []
    modified_any = False
    for src_path in src_files:
        # Convert separators
        src_path = src_path.replace('/', os.sep)

        # Setup paths for dependency, source, and object files
        dep = os.path.splitext(src_path)[0] + '.' + config['DEPEXT']
        obj = os.path.splitext(src_path)[0] + '.' + config['OBJEXT']
        dep_path = os.path.join(dep_dir, dep)
        obj_path = os.path.join(obj_dir, obj)
        makedir(os.path.split(dep_path)[0])
        makedir(os.path.split(obj_path)[0])

        # Remove dependency and object files
        if args.remove:
            remove(dep_path)
            remove(obj_path)
            continue

        # Add paths to config
        config['SRC_PATH'] = src_path
        config['DEP_PATH'] = dep_path
        config['OBJ_PATH'] = obj_path

        # Create dependency file if it does not exist
        dependencies = []
        if not os.path.exists(dep_path):
            if 'DEPRULE' in target:
                run_command(eval_rule(target['DEPRULE']))

        # Get list of dependencies
        try:
            dependencies = filter(None, open(dep_path, 'r').read().replace('\\', '/').translate(None, '\n\r').split(' '))
            # Remove duplicates
            dependencies = unique_list([d for d in dependencies if d != '/'])
            # Strip trailing ':' from first entry
            dependencies[0] = dependencies[0][:-1]

            # Sanity check
            dep_obj_path = os.path.join(os.path.split(src_path)[0], dependencies[0])
            if dep_obj_path != obj:
                print('\033[91mError: mismatch in dependency file {}: Expected {}, got {}\033[0m'.format(dep_path, obj, dep_obj_path))
                quit()

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
            modified = True

        if modified:
            # Set modified_any flag
            modified_any = True

            # Compile source file
            if 'SRCRULE' in target:
                run_command(eval_rule(target['SRCRULE']))

            # Add dependencies' hashes to new dictionary
            if dependencies:
                for dep_path in dependencies[1:]:
                    new_hash_dict[dep_path] = sha256file(dep_path)

        # After object file has been compiled, append it to list
        obj_list.append(obj_path)

    # Add object list to current config
    config['OBJ_LIST'] = ' '.join(obj_list)

    # Assume file is not modified unless one dependency file's hash is either missing or has changed
    modified = False

    # Handle additional dependencies
    if 'DEPENDS' in target:
        config['DEPENDS'] = eval_rule(target['DEPENDS'])
        depends = config['DEPENDS'].split(' ')
        for dep in depends:
            try:
                hash = sha256file(dep, '.exe')
                if dep in hash_dict:
                    if hash_dict[dep] != hash:
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
            if 'OBJRULE' in target:
                run_command(eval_rule(target['OBJRULE']))

            # Append hash of newly generated file to list
            try:
                hash = sha256file(target_path, '.exe')
                hash_dict[target_path_dict] = hash
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
        if 'EXERULE' in target:
            time_start = datetime.datetime.now()
            run_command(os.path.join(*eval_rule(target['EXERULE']).split('/')))
            elapsed = datetime.datetime.now() - time_start
            if args.verbose:
                print('\033[92mTime: {} seconds\033[0m'.format(elapsed.total_seconds()))

        # Run post-processing rule
        if 'PSTRULE' in target:
            run_command(os.path.join(*eval_rule(target['PSTRULE']).split('/')))

# End message
print('\033[93mDone.\033[0m')
