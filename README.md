# mimk
Minimal make build automation system

Mimk (short for minimal make) is a small build automation system written in Python.

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
    -r, --remove                Remove all dependency, object and executable files
    -v, --verbose               Verbose output
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
Mimk requires one (mandatory) target configuration file and one (optional) compiler configuration file.
The configuration files are python programs that are imported by mimk.py.
This allows several shortcuts:
* defining an 'include' variable which s then used for compiler and linker flags
* importing multiple targets into the 'all' target
* defining compiler-dependant options using 'if...else' conditions
However, mimk does not execute any functions within these configuration files, but rather uses variables defined in them.

## Configuration Search Path
If a sub-folder 'cfg' exists and contains a file '\_\_init\_\_.py', mimk first looks into that folder.
Otherwise, mimk tries to load the configuration files from the current working directory.
Multiple levels of sub-folders can be addressed by using a '.' as path separator (e.g. 'example.all' for the path 'cfg/example/all.py').
Please note that all sub-folders have to contain an empty file called '\_\_init\_\_.py' as otherwise mimk will not be able to import the configuration file as a module.

## Target Configuration
The target configuration file contains information about how to build the target(s).
The entry point is the variable 'targets', which contains a list of targets that will be build.
Each target is defined by a dictionary with the following keys:

| Key       | Description                                                        | Necessity |
| --------- | ------------------------------------------------------------------ | --------- |
| 'TARGET'  | Target filename                                                    | Required  |
| 'SRCPATH' | Path to folder holding the source files                            | Optional  |
| 'DEPRULE' | Rule that describes how to generate dependency files               | Required  |
| 'SRCRULE' | Rule that describes how to compile source files to object files    | Required  |
| 'OBJRULE' | Rule that describes how to compile/link object files               | Required  |
| 'EXERULE' | Rule that describes how to execute the resulting target executable | Optional  |

### Source files
If you want mimk to use all source files in one folder, define 'SRCPATH' as the path to that folder (mimk will then collect all files matching $SRCPATH/*.$SRCEXT).
Instead, if you rather want to provide a list with all source files, define them (with relative path) in the list variable 'src_files'.

### Rules
Rules are strings that may contain variables, which have '$' as a prefix (similar to rules in GNU make).
During runtime, these variables are evaluated and replaced by effective values (paths, executables, etc.).
The order of execution is as given in the table above.

#### Dependency rule
This rule describes how the dependency files are generated.
Note that the files generated by the 'DEPRULE' rule must have the following format:
1. Target object file (possibly with terminating colon)
2. Any number of dependency files (possibly separated by backslashes and newlines)
GCC with the '-MM -MF <depfile>' option creates exactly this formmat.
Mimk automatically processes the file (removal of newlines, backslahes and colons), evaluates the list and adds the source file.

#### Source rule
This rule describes how the source files are processed to object files, usually by a compiler.

#### Object rule
This rule describes how the object files are combined to an executable, usually by a linker.

#### Execute rule
Finally, the execute rule describes how the resulting executable should be run, including constant parameters.

## Compiler configuration
The compiler configuration file contains information about compilers, linkers and flags.
If no compiler configuration file is given, the default file 'gcc_release.py' is used.
The entry point if the dictionary variable 'config'.
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
| 'OBJ_LIST' | List of object files, created at runtime |               |

Please note that the key 'OBJ_LIST' holds a list of all generated object files after 'SRCRULE' has completed.
The purpose is to use it subsequently in the 'OBJRULE' step, namely for the linker.

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
