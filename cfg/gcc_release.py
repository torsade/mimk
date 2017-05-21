# mimk compiler configration file
#
# Compiler: GCC
# Options:  Release

config = {
    'BUILD':    'gcc_release',

    'CC':       'gcc',
    'DEP':      'gcc',

    'CFLAGS':   '-Wall -Wextra -Wundef',
    'DEPFLAGS': '-MM -MF',

    'DEPPATH':  'dep',
    'OBJPATH':  'obj',

    'SRCEXT':   'c',
    'INCEXT':   'h',
    'DEPEXT':   'd',
    'OBJEXT':   'o'
}
