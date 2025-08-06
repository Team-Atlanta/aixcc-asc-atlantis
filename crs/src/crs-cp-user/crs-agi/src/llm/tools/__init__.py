from . import util

def m2tools(module):
    """Expose all functions under the tool."""

    rtn = []
    for name, val in module.__dict__.items():
        if callable(val) and len(val.__doc__) != 0:
            if val.__module__ == module.__name__:
                rtn.append(val)
                globals()[name] = val
    return rtn

__tools__ = []
__tools__.extend(m2tools(util))

def get_tool_signatures():
    return [func.__doc__.strip() for func in __tools__]

__all__ = [get_tool_signatures]
__all__.extend(__tools__)

