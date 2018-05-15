import os, errno
def make_dirs(path):
    try:
        os.makedirs(path)
    except OSError as exc:  #ignore directory exists error
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise