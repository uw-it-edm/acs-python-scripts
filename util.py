import os, errno
import yaml

def make_dirs(path):
    try:
        os.makedirs(path)
    except OSError as exc:  #ignore directory exists error
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise

# load conf file (yml)
def getConfig(filename, stage='dev'):
    # sanity check
    if not filename:
        return None

    ret = None
    with open(filename, 'r') as file:
        conf = yaml.load(file)
        ret = conf
        if conf['default']:
            ret = conf['default']
            if stage and stage in conf:  # override default
                for key in conf[stage]:
                    ret[key] = conf[stage][key]

    return ret;
