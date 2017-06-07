# mimk target configration file
#
# Target:   helloworld

src_files = [
    'examples/helloworld/helloworld.c'
]

helloworld = {
    'TARGET':   'helloworld',
    'SRCDIR':   'examples/helloworld',

    'DEPRULE':  '$DEP $DEPFLAGS $DEP_PATH $SRC_PATH',
    'SRCRULE':  '$CC $CFLAGS -c $SRC_PATH -o $OBJ_PATH',
    'OBJRULE':  '$CC $CFLAGS $OBJ_LIST -o $TARGET_PATH',
    'EXERULE':  '$TARGET_PATH'
}

targets = [helloworld]
