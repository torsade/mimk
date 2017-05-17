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

## Target Configuration
The target configuration file contains information about how to build the target(s).
The entry point is the variable 'targets', which contains a list of targets that will be build.
Each target is defined by a dictionary with the following keys:
* 'TARGET':  Target filename
* 'SRCPATH' (optional): Path to folder holding the source files 
* 'DEPRULE': Rule that describes how to generate dependency files
* 'SRCRULE': Rule that describes how to compile source files 
* 'OBJRULE': Rule that describes how to compile/link object files
* 'EXERULE': Rule that describes how to execute the resulting target executable
If you want mimk to use all source files in one folder, define 'SRCPATH' as the path to that folder (mimk will then collect all files matching $SRCPATH/*.$SRCEXT)
If you rather want to provide a list with all source files, define them (with relative path) in the list variable 'src_files'.

## Compiler configuration
The compiler configuration file contains information about compilers, linkers and flags.
If no compiler configuration file is given, the default file 'gcc_release.py' is used.
The entry point if the dictionary variable 'config'.
The following keys are supported:
* 'BUILD':   Name of the compiler configuration, (default: 'gcc_release')
* 'DEPPATH': Name of subfolder for dependency files (default: 'dep')
* 'OBJPATH': Name of subfolder for object files (default: 'obj')
* 'SRCEXT':  Extension of source files (e.g. 'c')
* 'INCEXT':  Extension of include files (e.g. 'h')
* 'DEPEXT':  Extension of dependency files (e.g. 'd')
* 'OBJEXT':  Extension of object files (e.g.'o')

Although the keys used within target rules can be freely defined, these keys are typical:
* 'CC':       Compiler executable (e.g. 'gcc')
* 'DEP':      Dependency executable (e.g. 'gcc')
* 'LD':       Linker executable (e.g. 'ld')
* 'AR':       Archive executable (e.g. 'ar')
* 'CFLAGS':   Compiler flags
* 'DEPFLAGS': Flags to generate dependency files
* 'LDFLAGS':  Linker flags
