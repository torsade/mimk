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
Usage:
'''
    python mimk.py [-h] [-c CONFIG] [-r] [-v] target
    target                      Target configuration file
    -h, --help                  Show help message and exit
    -c CONFIG, --config CONFIG  Compiler configration file
    -r, --remove                Remove all dependency, object and executable files
    -v, --verbose               Verbose output
'''

# Configuration
Mimk requires one (mandatory) target configuration file and one (optional) compiler configuration file.

## Target Configuration
The target configuration file contains information about how to build the target(s).
The entry point is the variable 'targets', which contains a list of targets that will be build.
Each target is defined by a dictionary with the following keys:
* 'TARGET':  Target filename
* 'SRCPATH': Path to folder holding the source files
* 'DEPRULE': Rule that describes how to generate dependency files
* 'SRCRULE': Rule that describes how to compile source files 
* 'OBJRULE': Rule that describes how to compile/link object files
* 'EXERULE': Rule that describes how to execute the resulting target executable

## Compiler configuration
The compiler configuration file contains information about compilers, linkers and flags.
The entry point if the dictionary variable 'config', which contains 
The following keys are supported:
* 'BUILD':   Name of the compiler configuration, e.g. "gcc_release"
* 'DEPPATH': Name of subfolder for dependency files
* 'OBJPATH': Name of subfolder for object files
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
