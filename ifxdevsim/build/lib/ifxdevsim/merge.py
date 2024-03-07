from copy import deepcopy
from ruamel.yaml.compat import OrderedDict


def deep_merge(source, destination):
    for key, value in source.items():
        if (isinstance(value, dict) or issubclass(type(value), OrderedDict)) and (
            isinstance(destination.get(key), dict)
            or issubclass(type(value), OrderedDict)
        ):
            destination[key].update(value)
        else:
            destination[key] = deepcopy(value)

    return deepcopy(destination)
