# -*- coding: utf-8 -*-
"""Unit tests for type conversion utilities."""
import sys
from typing import List, Dict, Optional, Union, Tuple, Set, Any
from mcp_base.typeutil import python_type_to_json_type, docstring_type_to_json_type


def test_python_type_to_json_basic():
    """Test basic Python type to JSON Schema conversion."""
    print("Testing basic Python types...")
    
    assert python_type_to_json_type(str) == "string"
    assert python_type_to_json_type(int) == "integer"
    assert python_type_to_json_type(float) == "number"
    assert python_type_to_json_type(bool) == "boolean"
    assert python_type_to_json_type(bytes) == "string"
    assert python_type_to_json_type(type(None)) == "null"
    
    print("  ✓ Basic types passed!\n")


def test_python_type_to_json_generics():
    """Test generic Python types to JSON Schema conversion."""
    print("Testing generic Python types...")
    
    # List[str]
    result1 = python_type_to_json_type(List[str])
    print(f"  List[str]: {result1}")
    assert result1 == {"type": "array", "items": {"type": "string"}}
    
    # List[int]
    result2 = python_type_to_json_type(List[int])
    print(f"  List[int]: {result2}")
    assert result2 == {"type": "array", "items": {"type": "integer"}}
    
    # Dict[str, int]
    result3 = python_type_to_json_type(Dict[str, int])
    print(f"  Dict[str, int]: {result3}")
    assert result3 == {"type": "object"}
    
    # Optional[str] - should extract inner type
    result4 = python_type_to_json_type(Optional[str])
    print(f"  Optional[str]: {result4}")
    # Note: Optional is Union[str, None], behavior depends on implementation
    
    # Tuple[int, str]
    result5 = python_type_to_json_type(Tuple[int, str])
    print(f"  Tuple[int, str]: {result5}")
    assert result5["type"] == "array"
    
    # Set[str]
    result6 = python_type_to_json_type(Set[str])
    print(f"  Set[str]: {result6}")
    assert result6["type"] == "array"
    
    print("  ✓ Generic types passed!\n")


def test_docstring_type_basic():
    """Test basic docstring type to JSON Schema conversion."""
    print("Testing basic docstring types...")
    
    assert docstring_type_to_json_type('str') == 'string'
    assert docstring_type_to_json_type('int') == 'integer'
    assert docstring_type_to_json_type('float') == 'number'
    assert docstring_type_to_json_type('bool') == 'boolean'
    assert docstring_type_to_json_type('list') == 'array'
    assert docstring_type_to_json_type('dict') == 'object'
    
    print("  ✓ Basic docstring types passed!\n")


def test_docstring_type_generics():
    """Test generic docstring types to JSON Schema conversion."""
    print("Testing generic docstring types...")
    
    # List[str]
    result1 = docstring_type_to_json_type('List[str]')
    print(f"  List[str]: {result1}")
    assert result1 == {'type': 'array', 'items': {'type': 'string'}}
    
    # Dict[str, int]
    result2 = docstring_type_to_json_type('Dict[str, int]')
    print(f"  Dict[str, int]: {result2}")
    assert result2 == {'type': 'object'}
    
    # Optional[str]
    result3 = docstring_type_to_json_type('Optional[str]')
    print(f"  Optional[str]: {result3}")
    assert result3 == 'string'
    
    # Union[int, str]
    result4 = docstring_type_to_json_type('Union[int, str]')
    print(f"  Union[int, str]: {result4}")
    assert result4 == 'integer'  # Takes first non-None type
    
    # List[Dict[str, Any]]
    result5 = docstring_type_to_json_type('List[Dict[str, Any]]')
    print(f"  List[Dict[str, Any]]: {result5}")
    assert result5 == {'type': 'array', 'items': {'type': 'object'}}
    
    # Sequence[str]
    result6 = docstring_type_to_json_type('Sequence[str]')
    print(f"  Sequence[str]: {result6}")
    assert result6 == {'type': 'array', 'items': {'type': 'string'}}
    
    # Mapping[str, int]
    result7 = docstring_type_to_json_type('Mapping[str, int]')
    print(f"  Mapping[str, int]: {result7}")
    assert result7 == {'type': 'object'}
    
    print("  ✓ Generic docstring types passed!\n")


def test_docstring_type_edge_cases():
    """Test edge cases for docstring type conversion."""
    print("Testing edge cases...")
    
    # Empty string
    result1 = docstring_type_to_json_type('')
    print(f"  Empty string: {result1}")
    assert result1 == 'string'
    
    # None/NoneType in Union
    result2 = docstring_type_to_json_type('Union[str, None]')
    print(f"  Union[str, None]: {result2}")
    assert result2 == 'string'
    
    result3 = docstring_type_to_json_type('Union[None, int]')
    print(f"  Union[None, int]: {result3}")
    assert result3 == 'integer'
    
    # Unknown type defaults to string
    result4 = docstring_type_to_json_type('CustomType')
    print(f"  CustomType: {result4}")
    assert result4 == 'string'
    
    # Case insensitivity
    result5 = docstring_type_to_json_type('STRING')
    print(f"  STRING (uppercase): {result5}")
    assert result5 == 'string'
    
    result6 = docstring_type_to_json_type('Int')
    print(f"  Int (mixed case): {result6}")
    assert result6 == 'integer'
    
    print("  ✓ Edge cases passed!\n")


if __name__ == '__main__':
    print("=" * 60)
    print("Type Utility Tests")
    print("=" * 60 + "\n")
    
    try:
        test_python_type_to_json_basic()
        test_python_type_to_json_generics()
        test_docstring_type_basic()
        test_docstring_type_generics()
        test_docstring_type_edge_cases()
        
        print("=" * 60)
        print("All type utility tests passed! ✓")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
