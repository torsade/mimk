# mimk target configration file
#
# Target:   all

target_name = 'all'

targets = [
    # helloworld
    {
        'TARGET':   'helloworld',
        'SRCPATH':  'examples/helloworld',

        'DEPRULE':  '$DEP $DEPFLAGS $DEP_PATH $SRC_PATH',
        'SRCRULE':  '$CC $CFLAGS -c $SRC_PATH -o $OBJ_PATH',
        'OBJRULE':  '$CC $CFLAGS $OBJ_LIST -o $TARGET',
        'EXERULE':  '$TARGET'
    }
]
