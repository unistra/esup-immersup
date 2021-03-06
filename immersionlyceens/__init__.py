VERSION = (2, 0, '0-alpha')


def get_version():
    if not VERSION[2] and len(VERSION) > 3:
        return f"{'.'.join(map(str, VERSION[:2]))}{VERSION[3]}"
    else:
        return '.'.join(map(str, VERSION[:3]))
