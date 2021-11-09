
VERSION = (1, 0, 10)


def get_version():
    if not VERSION[2] and len(VERSION) > 3:
        return f"{'.'.join(map(str, VERSION[:2]))}{VERSION[3]}"
    else:
        return '.'.join(map(str, VERSION[:3]))
