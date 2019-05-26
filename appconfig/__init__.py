from configparser import ConfigParser

import os
import os.path

cwd = os.path.abspath(os.path.dirname(__file__))


cfg = ConfigParser()
cfg.read(os.path.join(cwd, 'config.conf.DEFAULT'))
cfg.read(os.path.join(cwd, 'config.conf'))

def fetch(section, option=None, check_env=True, cast_to=None):
    def toupper(s):
        if s is None:
            return None

        try:
            s = s.upper()
        except AttributeError:
            msg = f'option or section name must be type str, not {type(s)}'
            raise TypeError(msg)
        return s

    # Convert args to uppercase
    section, option = [*map(toupper, [section, option])]

    sec = cfg[section]

    if option == None:
        return sec

    env = None

    if check_env:
        varname = f'{section}_{option}'.upper()
        env = os.environ.get(varname)

    value = sec.get(option, env)

    if value.isnumeric():
        value = float(value)

    if cast_to != None:
        env = cast_to(env)

    return value

DEBUGGING = fetch('BOT', 'DEBUGGING', cast_to=bool)

