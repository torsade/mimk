#!/usr/bin/env python
import argparse
import hashlib
import importlib
import json
import os
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


# Issue command
def run_command(command_str):
    if command_str:
        command_list = command_str.split(';');
        for command in command_list:
            if args.verbose:
                print(command)
            try:
                ret = subprocess.call(command, shell=True)
                if ret < 0:
                    print('Command {} terminated by signal {}'.format(command.split(' ')[0], -ret))
                    quit()
                elif ret > 0:
                    print('Command {} returned error {}'.format(command.split(' ')[0], ret))
                    quit()
            except OSError as e:
                print('Command execution failed: ' + e)
                quit()


# Make directory
def makedir(pathname):
    if not os.path.exists(pathname):
        os.makedirs(pathname)


# Remove file
def remove(filename, ext=''):
    if args.verbose:
        print('Remove ' + filename)
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


# Main program
global args
parser = argparse.ArgumentParser(description='mimk - Minimal make')
parser.add_argument('target', help='Target configuration file')
parser.add_argument('-c', '--config', default='gcc_release', help='Compiler configuration file')
parser.add_argument('-r', '--remove', action='store_true', help='Remove all dependency, object and executable files')
parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
args = parser.parse_args()

# Start message
print('mimk - Minimal make')

# Import target and config
config_dir = 'cfg'
if not os.path.isdir(config_dir):
    config_dir = ''
try:
    target_module = importlib.import_module(config_dir + ('' if config_dir == '' else '.') + args.target, package=None)
    targets = target_module.targets
except Exception:
    print('Could not find target file ' + os.path.join(config_dir, args.target) + '.py')
    quit()
try:
    config_module = importlib.import_module(config_dir + ('' if config_dir == '' else '.') + args.config, package=None)
    config = config_module.config
except Exception:
    print('Could not find config file ' + os.path.join(config_dir, args.config) + '.py')
    quit()
if args.verbose:
    print('Build:  ' + config['BUILD'])


# Create build directory and sub-folders
build_dir = 'build_' + config['BUILD']
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

# Print statistics
if args.verbose:
    print('Loaded hash dictionary with {} entries (src: {}, inc: {}, trgt: {}).'.format(len(hash_dict), hash_src, hash_inc, hash_trgt))

# Process targets
for index, target in enumerate(targets):
    # Check target
    if 'TARGET' not in target:
        print('No target defined in section #' + str(index) + ' of file ' + args.target + '.py')
        continue
    print('Target: ' + target['TARGET'])

    # Get source files list
    src_files = []
    if getattr(target_module, 'src_files', None):
        # Get list of source files from target configuration
        src_files = target_module.src_files
        if not files_exist(src_files):
            print('At least one source file could not be found: ' + src_files)
            continue
    elif 'SRCPATH' in target:
        # Get list of all SRCEXT files from SRCPATH
        try:
            for src_path in target['SRCPATH'].split(' '):
                src_files.extend([os.path.join(src_path, fn) for fn in os.listdir(src_path) if fn.endswith(config['SRCEXT'])])
        except Exception:
            pass
        if not src_files:
            print('No source files found matching pattern (' + os.path.join(target['SRCPATH'], ')*.' + config['SRCEXT']))
            continue

    if args.verbose:
        print('Processing {} source files...'.format(len(src_files)))

    # Compile all files
    new_hash_dict = {}
    obj_list = []
    modified_any = False
    for src_path in src_files:
        # Setup paths for dependency, source, and object files
        dep = os.path.splitext(os.path.basename(src_path))[0] + '.' + config['DEPEXT']
        obj = os.path.splitext(os.path.basename(src_path))[0] + '.' + config['OBJEXT']
        dep_path = os.path.join(dep_dir, dep)
        obj_path = os.path.join(obj_dir, obj)

        # Remove dependency and object files
        if args.remove:
            remove(dep_path)
            remove(obj_path)
            continue

        # Add paths to config
        config['SRC_PATH'] = src_path
        config['DEP_PATH'] = dep_path
        config['OBJ_PATH'] = obj_path

        # Create dependency file
        if not os.path.exists(dep_path):
            if 'DEPRULE' in target:
                run_command(eval_rule(target['DEPRULE']))

        # Get list of dependencies
        dependencies = filter(None, open(dep_path, 'r').read().replace('\\', '/').translate(None, ':\n\r').split(' '))
        dependencies = unique_list([d for d in dependencies if d != '/'])

        # Sanity check
        if dependencies[0] != obj:
            print('Error: mismatch in dependency file ' + dep_path + ': Expected ' + obj + ', got ' + dependencies[0])
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

        if modified:
            # Set modified_any flag
            modified_any = True

            # Compile source file
            if 'SRCRULE' in target:
                run_command(eval_rule(target['SRCRULE']))

            # Add dependencies' hashes to new dictionary
            for dep_path in dependencies[1:]:
                new_hash_dict[dep_path] = sha256file(dep_path)

        # After object file has been compiled, append it to list
        obj_list.append(obj_path)

    # Create target
    target_path = os.path.join(build_dir, target['TARGET'])
    target_path_dict = build_dir + '/' + target['TARGET']

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

    # Add target path and object list to current config
    config['TARGET'] = target_path
    config['OBJ_LIST'] = ' '.join(obj_list)

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
            run_command(os.path.join(*eval_rule(target['EXERULE']).split('/')))

# End message
print('Done.')
