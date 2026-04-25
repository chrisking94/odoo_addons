# -*- coding: utf-8 -*-
# @Time         : 10:26 2026/4/24
# @Author       : Chris
# @Description  :
import inspect


# Compatible implementation for all Python versions
# Uses __origin__ and __args__ attributes available since Python 3.5
def get_origin(tp):
    """Get the origin of a generic type."""
    return getattr(tp, '__origin__', None)


def get_args(tp):
    """Get the type arguments of a generic type."""
    return getattr(tp, '__args__', ())


def _python_type_to_json_type(py_type):
    """Convert Python type annotations to JSON Schema types."""
    if py_type == inspect.Parameter.empty:
        return "string"
    
    origin = get_origin(py_type)
    
    if origin is not None:
        if origin in (list, tuple, set):
            args = get_args(py_type)
            if args:
                item_type = _python_type_to_json_type(args[0])
                return {"type": "array", "items": {"type": item_type}}
            return {"type": "array", "items": {"type": "string"}}
        elif origin is dict:
            return {"type": "object"}
        elif origin.__name__ == 'Literal':
            return {"type": "string"}
    
    type_mapping = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        bytes: "string",
        type(None): "null",
    }
    
    return type_mapping.get(py_type, "string")


def mcp_tool(description=None):
    def decorator(func):
        func._is_mcp_tool = True
        func._mcp_desc = description or func.__doc__ or "Odoo Tool"

        sig = inspect.signature(func)
        schema = {"type": "object", "properties": {}, "required": []}

        for name, param in sig.parameters.items():
            if name == 'self':
                continue

            json_type = _python_type_to_json_type(param.annotation)
            
            prop_schema = {}
            if isinstance(json_type, dict):
                prop_schema.update(json_type)
            else:
                prop_schema["type"] = json_type
            
            if param.default != inspect.Parameter.empty:
                prop_schema["default"] = param.default
            
            schema["properties"][name] = prop_schema
            
            if param.default == inspect.Parameter.empty:
                schema["required"].append(name)

        func._mcp_schema = schema
        return func

    return decorator
