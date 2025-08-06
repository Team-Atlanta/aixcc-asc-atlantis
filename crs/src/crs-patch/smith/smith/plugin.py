from typing import Dict, Callable
from dataclasses import dataclass

@dataclass(frozen=True)
class Plugin:
    def __init__(self, handler: Callable, spec: Dict):
        self.handler = handler
        self.spec = spec
        self.name = spec.get("function", {}).get("name")

def plugin_execute(func: Callable) -> Plugin:
    """
    Execute the target program with a given input.
    """
    return Plugin(
        func,
        {
            "type": "function",
            "function": {
                "name": "plugin_execute",
                "description": plugin_execute.__doc__,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "input": {
                            "type": "string",
                            "description": "the input for the target program",
                        },
                    },
                    "required": ["input"],
                },
            },
        },
    )

def plugin_read_func_source_code(func: Callable) -> Plugin:
    """
    Read the source code of the function with a given function name
    """
    return Plugin(
        func,
        {
            "type": "function",
            "function": {
                "name": "plugin_read_func_source_code",
                "description": plugin_read_func_source_code.__doc__,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "the function name, e.g. main",
                        },
                    },
                    "required": ["name"],
                },
            },
        },
    )

def plugin_read_struct_source_code(func: Callable) -> Plugin:
    """
    Read the source code of the struct with a given name
    """
    return Plugin(
        func,
        {
            "type": "function",
            "function": {
                "name": "plugin_read_struct_source_code",
                "description": plugin_read_struct_source_code.__doc__,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "the struct name, e.g. node",
                        }
                    },
                    "required": ["name"],
                },
            },
        },
    )

def plugin_read_global_var_source_code(func: Callable) -> Plugin:
    """
    Read the source code of the global variable definition with a given name
    """
    return Plugin(
        func,
        {
            "type": "function",
            "function": {
                "name": "plugin_read_global_var_source_code",
                "description": plugin_read_global_var_source_code.__doc__,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "the global variable name",
                        }
                    },
                    "required": ["name"],
                },
            },
        },
    )
