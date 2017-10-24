# mimk
Minimal make build automation system

Mimk (short for **minimal make**) is a small build automation system written in Python.

# Features
* Simple configuration
    * Target file: contains information about how to build target
    * Config file: contains information about compilers and flags
* Uses SHA-256 hashes to decide if file needs to be (re-)build
* Uses one target build folder for all target files (dependencies, object files and executables)
* Supports cross-compilation

# Usage
Mimk consists of just one Python script file 'mimk.py'.
Usage:
```
    python mimk.py [-h] [-c CONFIG] [-r] [-v] target
    target                      Target configuration file
    -h, --help                  Show help message and exit
    -c CONFIG, --config CONFIG  Compiler configration file
    -l, --list                  List targets
    -r, --remove                Remove all dependency, object and executable files and
                                undo pre-processing rule
    -q, --quiet                 Quiet output
    -v, --verbose               Verbose output
    -x [EXECUTE [EXECUTE ...]], --execute [EXECUTE [EXECUTE ...]]
                                Execute specific target(s)
```

## Examples
Make target 'all' with GCC compiler and release options:
```
    python mimk.py all
```
Make target 'all' with GCC compiler and debug options:
```
    python mimk.py -c gcc_debug.py all
```
Remove intermediate files:
```
    python mimk.py -r all
```
Be verbose:
```
    python mimk.py -v all
```

# Configuration
Mimk requires one (optional) compiler configuration file and one (mandatory) target configuration file.
The configuration files are python programs that are imported by mimk.py.
This allows several shortcuts:
* defining an 'include' variable which is then used for compiler and linker flags
* importing multiple targets into the 'all' target
* defining compiler-dependent options using 'if...else' conditions
However, mimk does not execute any functions within these configuration files, but rather uses variables defined in them.

## Configuration Search Path
If a sub-folder 'mimk' or 'cfg' exists, mimk first looks into that folder.
Otherwise, mimk tries to load the configuration files from the current working directory.
Multiple levels of sub-folders can be addressed by using a '.' as path separator (e.g. 'example.all' for the path 'cfg/example/all.py').

## Compiler configuration
The compiler configuration file contains information about compilers, linkers and flags.
If no compiler configuration file is given, the default file 'gcc_release.py' is used.
The entry point is the dictionary variable 'config'.
The following keys are supported:

| Key        | Description                              | Default       |
| ---------- | ---------------------------------------- | ------------- |
| 'BUILD'    | Name of the compiler configuration       | 'gcc_release' |
| 'DEPPATH'  | Name of subfolder for dependency files   | 'dep'         |
| 'OBJPATH'  | Name of subfolder for object files       | 'obj'         |
| 'SRCEXT'   | Extension of source files                | 'c'           |
| 'INCEXT'   | Extension of include files               | 'h'           |
| 'DEPEXT'   | Extension of dependency files            | 'd'           |
| 'OBJEXT'   | Extension of object files                | 'o'           |

### Keys created during runtime
Some keys are dynamically generated during runtime and can be used within rules.
To distinguish them from user-provided keys, they all contain an underscore '_' in their name.
The following keys are available:

| Key            | Description                          | Generation                                      | Available |
| -------------- | ------------------------------------ | ----------------------------------------------- | --------- |
| 'BUILD_DIR'    | Build directory                      | 'build/' + compiler config name                 | Start     |
| 'DEP_DIR'      | Path to dependency dir in build dir  | BUILD_DIR/DEPPATH                               | Start     |
| 'OBJ_DIR'      | Path to object dir in build dir      | BUILD_DIR/OBJPATH                               | Start     |
| 'SRC_PATH'     | Source path                          | <src_files> or SRCDIR/*.SRCEXT                  | DEPRULE   |
| 'DEP_PATH'     | Path to dependency file in build dir | BUILD_DIR/DEPPATH/SRCPATH with DEPEXT extension | DEPRULE   |
| 'OBJ_PATH'     | Path to object file in build dir     | BUILD_DIR/OBJPATH/SRCPATH with OBJEXT extension | DEPRULE   |
| 'TARGET_PATH'  | Path to target file in build dir     | BUILD_DIR/TARGET                                | Start     |
| 'OBJ_LIST'     | List of object files                 | List of all generated OBJ_PATH files            | OBJRULE   |
| 'OBJ_LIST_REL' | List of object files (relative path) | List of all generated OBJ_PATH files            | OBJRULE   |

Please note that the key 'OBJ_LIST' holds a list of all generated object files.
The purpose is to use it in the 'OBJRULE' step, namely for the linker.

### Examples for typical target keys
Although the keys used within target rules can be freely defined, these keys are typical:

| Key        | Description                        | Example   |
| ---------- | ---------------------------------- | --------- |
| 'CC'       | Compiler executable                | 'gcc'     |
| 'DEP'      | Dependency executable              | 'gcc'     |
| 'LD'       | Linker executable                  | 'ld'      |
| 'AR'       | Archive executable                 | 'ar'      |
| 'CFLAGS'   | Compiler flags                     | '-Wall'   |
| 'DEPFLAGS' | Flags to generate dependency files | '-MM -MF' |
| 'LDFLAGS'  | Linker flags                       | '-lm'     |

## Target Configuration
The target configuration file contains information about how to build the target(s).
The entry point is the variable 'targets', which contains a list of targets that will be build.
Each target is defined by a dictionary with the following keys:

| Key       | Description                                                        | Necessity |
| --------- | ------------------------------------------------------------------ | --------- |
| 'TARGET'  | Target filename                                                    | Required  |
| 'SRCBASE' | Path to the base folder containing SRCDIR folder(s)                | Optional  |
| 'SRCDIR'  | Path to folder(s) holding the source files                         | Optional  |
| 'DEPENDS' | Additional dependencies not covered by DEPRULE                     | Optional  |
| 'PRERULE' | Pre-processing rule                                                | Optional  |
| 'DEPRULE' | Rule that describes how to generate dependency files               | Optional  |
| 'SRCRULE' | Rule that describes how to compile source files to object files    | Required  |
| 'OBJRULE' | Rule that describes how to compile/link object files               | Optional  |
| 'EXERULE' | Rule that describes how to execute the resulting target executable | Optional  |
| 'PSTRULE' | Post-processing rule                                               | Optional  |
| 'REMRULE' | Remove rule                                                        | Optional  |

Target-specific compiler configuration keys can be added to the target configuration file by defining the dictionary variable 'config'.
The 'config' keys from the compiler configuration file can be overridden by defining the same key in the 'config' variable in the target configuration file.

### Source files
If you want mimk to use all source files from one or multiple folders, define 'SRCDIR' as the path to those folders (mimk will then collect all files matching $SRCDIR/*.$SRCEXT).
Instead, if you rather want to provide a list with all source files, define them (with relative path) in the list variable 'src_files'.

### Rules
Rules are strings that may contain variables, which have '$' as a prefix (similar to rules in GNU make).
During runtime, these variables are evaluated and replaced by effective values (paths, executables, etc.).
The order of execution is as given in the table above.

#### Internal commands
Internal commands provide an OS-independent way for common operations on files and directories.
They are written in lower-case and start with an '@' sign.
Wildcards ('*') are supported.

| Command   | Description                           | Parameters        |
| --------- | ------------------------------------- | ----------------- |
| 'copy'    | Copy file                             | file, dir/file    |
| 'move'    | Move file                             | file, dir/file    |
| 'rename'  | Rename file                           | file, file        |
| 'makedir' | Make directory                        | dir               |
| 'delete'  | Delete file or directory              | dir/file          |
| 'cd'      | Change directory                      | dir               |
| 'ok'      | Run external command, ignoring errors | external command  |

#### Pre-processing rule
This rule can be used to perform pre-processing steps, e.g. copying files to $SRCDIR.

#### Dependency rule
This rule describes how the dependency files are generated.
Note that the files generated by the 'DEPRULE' rule must have the following format:
1. Target object file (possibly with terminating colon)
2. Any number of dependency files (possibly separated by backslashes and newlines)
GCC with the '-MM -MF <depfile>' option creates exactly this formmat.
Mimk automatically processes the file (removal of newlines, backslahes and colons) and evaluates the list.

#### Source rule
This rule describes how the source files are processed to object files, usually by a compiler.

#### Object rule
This rule describes how the object files are combined to an executable, usually by a linker.
Additional dependencies not covered by 'DEPRULE' (e.g., libraries) can be added by using the 'DEPENDS' keyword.

#### Execute rule
Finally, the execute rule describes how the resulting executable should be run, including constant parameters.

#### Post-processing rule
This rule can be used to perform post-processing steps, e.g. copying, moving, deleting or renaming files.

#### Remove rule
This rule is executed when using the "-r" switch.
