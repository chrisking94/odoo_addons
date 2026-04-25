# -*- coding: utf-8 -*-
"""Quick test for docstring parser functionality."""
import sys
from mcp_base.docstring import parse_docstring, parse_docstring_params, extract_tool_description
from mcp_base.decorators import mcp_tool


def test_google_style():
    """Test Google-style docstring parsing."""
    print("Testing Google style...")
    
    docstring = """Search for customers by name.
    
    Args:
        name: Customer name to search for
        limit: Maximum number of results to return
    
    Returns:
        List of matching customers
    """
    
    params = parse_docstring_params(docstring)
    print(f"  Parsed params: {params}")
    assert params.get('name') == "Customer name to search for", f"Expected 'Customer name to search for', got {params.get('name')}"
    assert params.get('limit') == "Maximum number of results to return", f"Expected 'Maximum number of results to return', got {params.get('limit')}"
    print("  ✓ Google style passed!\n")


def test_numpy_style():
    """Test NumPy-style docstring parsing."""
    print("Testing NumPy style...")
    
    docstring = """Calculate total price.
    
    Parameters
    ----------
    quantity : int
        Number of items
    price : float
        Price per item
    
    Returns
    -------
    float
        Total price
    """
    
    params = parse_docstring_params(docstring)
    print(f"  Parsed params: {params}")
    # Note: descriptions are normalized to lowercase by cleandoc
    assert 'quantity' in params, "Missing 'quantity' parameter"
    assert 'price' in params, "Missing 'price' parameter"
    assert 'items' in params['quantity'].lower(), f"Expected description containing 'items', got {params['quantity']}"
    assert 'price' in params['price'].lower(), f"Expected description containing 'price', got {params['price']}"
    print("  ✓ NumPy style passed!\n")


def test_sphinx_style():
    """Test Sphinx/reST-style docstring parsing."""
    print("Testing Sphinx style...")
    
    docstring = """Send email notification.
    
    :param recipient: Email recipient address
    :param subject: Email subject line
    :arg body: Email body content
    """
    
    params = parse_docstring_params(docstring)
    print(f"  Parsed params: {params}")
    assert params.get('recipient') == "Email recipient address", f"Expected 'Email recipient address', got {params.get('recipient')}"
    assert params.get('subject') == "Email subject line", f"Expected 'Email subject line', got {params.get('subject')}"
    assert params.get('body') == "Email body content", f"Expected 'Email body content', got {params.get('body')}"
    print("  ✓ Sphinx style passed!\n")


def test_parse_docstring_complete():
    """Test complete docstring parsing (description + params + returns)."""
    print("Testing complete docstring parsing...")
    
    # Test 1: Sphinx style with returns
    docstring1 = """Search customers by name.
    
    :param name: Customer name to search for
    :param limit: Maximum number of results
    :returns: List of matching customers
    """
    result1 = parse_docstring(docstring1)
    print(f"  Description: '{result1['description']}'")
    print(f"  Params: {result1['params']}")
    print(f"  Returns: '{result1['returns']}'")
    assert result1['description'] == "Search customers by name."
    assert result1['params']['name'] == "Customer name to search for"
    assert result1['params']['limit'] == "Maximum number of results"
    assert result1['returns'] == "List of matching customers"
    
    # Test 2: Google style
    docstring2 = """Calculate total price.
    
    Args:
        quantity: Number of items
        price: Price per item
    
    Returns:
        Total price as float
    """
    result2 = parse_docstring(docstring2)
    print(f"  Description: '{result2['description']}'")
    assert result2['description'] == "Calculate total price."
    assert 'quantity' in result2['params']
    assert 'price' in result2['params']
    assert 'total price' in result2['returns'].lower()
    
    # Test 3: No returns section
    docstring3 = """Simple method.
    
    :param x: Input value
    """
    result3 = parse_docstring(docstring3)
    assert result3['description'] == "Simple method."
    assert result3['params']['x'] == "Input value"
    assert result3['returns'] == ""
    
    print("  ✓ Complete docstring parsing passed!\n")


def test_extract_tool_description():
    """Test extraction of tool description from docstring."""
    print("Testing tool description extraction...")
    
    # Test 1: Sphinx style
    docstring1 = """Search customers by name.
    
    :param name: Customer name to search for
    :param limit: Maximum number of results
    """
    desc1 = extract_tool_description(docstring1)
    print(f"  Sphinx style: '{desc1}'")
    assert desc1 == "Search customers by name.", f"Expected 'Search customers by name.', got '{desc1}'"
    
    # Test 2: Google style
    docstring2 = """Calculate total price.
    
    Args:
        quantity: Number of items
        price: Price per item
    """
    desc2 = extract_tool_description(docstring2)
    print(f"  Google style: '{desc2}'")
    assert desc2 == "Calculate total price.", f"Expected 'Calculate total price.', got '{desc2}'"
    
    # Test 3: NumPy style
    docstring3 = """Send email notification.
    
    Parameters
    ----------
    recipient : str
        Email recipient
    """
    desc3 = extract_tool_description(docstring3)
    print(f"  NumPy style: '{desc3}'")
    assert desc3 == "Send email notification.", f"Expected 'Send email notification.', got '{desc3}'"
    
    # Test 4: No params
    docstring4 = """Simple method without parameters."""
    desc4 = extract_tool_description(docstring4)
    print(f"  No params: '{desc4}'")
    assert desc4 == "Simple method without parameters.", f"Expected 'Simple method without parameters.', got '{desc4}'"
    
    # Test 5: Empty docstring
    desc5 = extract_tool_description("")
    print(f"  Empty: '{desc5}'")
    assert desc5 == "Odoo Tool", f"Expected 'Odoo Tool', got '{desc5}'"
    
    print("  ✓ Tool description extraction passed!\n")


def test_complex_types_from_docstring():
    """Test parsing of complex type annotations from :type: directives."""
    print("Testing complex type parsing...")
    
    # Test 1: List[str]
    docstring1 = """Method with list type.
    
    :param names: List of user names
    :type names: List[str]
    """
    result1 = parse_docstring(docstring1)
    print(f"  List[str]: {result1['param_types'].get('names')}")
    assert result1['param_types']['names'] == {'type': 'array', 'items': {'type': 'string'}}
    
    # Test 2: Dict[str, int]
    docstring2 = """Method with dict type.
    
    :param data: User data mapping
    :type data: Dict[str, int]
    """
    result2 = parse_docstring(docstring2)
    print(f"  Dict[str, int]: {result2['param_types'].get('data')}")
    assert result2['param_types']['data'] == {'type': 'object'}
    
    # Test 3: Optional[str]
    docstring3 = """Method with optional type.
    
    :param name: Optional user name
    :type name: Optional[str]
    """
    result3 = parse_docstring(docstring3)
    print(f"  Optional[str]: {result3['param_types'].get('name')}")
    assert result3['param_types']['name'] == 'string'
    
    # Test 4: List[Dict[str, Any]]
    docstring4 = """Method with complex nested type.
    
    :param users: List of user objects
    :type users: List[Dict[str, Any]]
    """
    result4 = parse_docstring(docstring4)
    print(f"  List[Dict[str, Any]]: {result4['param_types'].get('users')}")
    assert result4['param_types']['users'] == {'type': 'array', 'items': {'type': 'object'}}
    
    # Test 5: Union[int, str]
    docstring5 = """Method with union type.
    
    :param value: Value that can be int or str
    :type value: Union[int, str]
    """
    result5 = parse_docstring(docstring5)
    print(f"  Union[int, str]: {result5['param_types'].get('value')}")
    assert result5['param_types']['value'] == 'integer'  # Takes first non-None type
    
    print("  ✓ Complex type parsing passed!\n")


def test_type_priority():
    """Test that type hints take priority over docstring :type:."""
    print("Testing type priority...")
    
    # Test 1: Type hint present (should use type hint)
    @mcp_tool()
    def method_with_hint(self, name: str):
        """Method with type hint.
        
        :type name: int
        :param name: User name
        """
        pass
    
    schema1 = method_with_hint._mcp_schema
    print(f"  Type hint (str) vs :type: int -> {schema1['properties']['name']['type']}")
    assert schema1['properties']['name']['type'] == 'string', "Should use type hint (str -> string)"
    
    # Test 2: No type hint, only :type: in docstring
    @mcp_tool()
    def method_without_hint(self, age):
        """Method without type hint.
        
        :type age: int
        :param age: User age
        """
        pass
    
    schema2 = method_without_hint._mcp_schema
    print(f"  Only :type: int -> {schema2['properties']['age']['type']}")
    assert schema2['properties']['age']['type'] == 'integer', "Should use :type: directive"
    
    # Test 3: Neither type hint nor :type:
    @mcp_tool()
    def method_no_type(self, data):
        """Method with no type info.
        
        :param data: Some data
        """
        pass
    
    schema3 = method_no_type._mcp_schema
    print(f"  No type info -> {schema3['properties']['data']['type']}")
    assert schema3['properties']['data']['type'] == 'string', "Should default to string"
    
    # Test 4: Complex type from :type: with List[str]
    @mcp_tool()
    def method_list_type(self, names):
        """Method with list type in docstring.
        
        :type names: List[str]
        :param names: User names
        """
        pass
    
    schema4 = method_list_type._mcp_schema
    print(f"  :type: List[str] -> {schema4['properties']['names']}")
    assert schema4['properties']['names']['type'] == 'array'
    assert schema4['properties']['names']['items']['type'] == 'string'
    
    print("  ✓ Type priority tests passed!\n")


def test_mcp_decorator_integration():
    """Test MCP decorator with docstring parameter descriptions."""
    print("Testing MCP decorator integration...")
    
    @mcp_tool()
    def search_customers(self, name: str, limit: int = 10):
        """Search for customers by name.
        
        Args:
            name: Customer name to search for
            limit: Maximum number of results to return
        """
        return []
    
    schema = search_customers._mcp_schema
    print(f"  Generated schema: {schema}")
    
    assert 'description' in schema['properties']['name'], "Missing description for 'name'"
    assert schema['properties']['name']['description'] == "Customer name to search for"
    assert schema['properties']['limit']['description'] == "Maximum number of results to return"
    print("  ✓ MCP decorator integration passed!\n")


def test_mcp_decorator_without_parentheses():
    """Test MCP decorator without parentheses (@mcp_tool)."""
    print("Testing MCP decorator without parentheses...")
    
    # Test 1: Basic usage without parentheses
    @mcp_tool
    def simple_search(self, query: str):
        """Simple search method.
        
        :param query: Search query string
        """
        return []
    
    assert hasattr(simple_search, '_is_mcp_tool'), "Missing _is_mcp_tool attribute"
    assert simple_search._mcp_desc == "Simple search method."
    assert 'query' in simple_search._mcp_schema['properties']
    assert simple_search._mcp_schema['properties']['query']['type'] == 'string'
    assert simple_search._mcp_schema['properties']['query']['description'] == "Search query string"
    print(f"  Description: '{simple_search._mcp_desc}'")
    print(f"  Schema: {simple_search._mcp_schema}")
    
    # Test 2: Without parentheses but with complex types
    @mcp_tool
    def complex_method(self, names: list, data: dict):
        """Method with complex types.
        
        Args:
            names: List of names
            data: Data dictionary
        """
        return []
    
    assert complex_method._mcp_desc == "Method with complex types."
    assert complex_method._mcp_schema['properties']['names']['type'] == 'array'
    assert complex_method._mcp_schema['properties']['data']['type'] == 'object'
    print(f"  Complex types handled correctly")
    
    print("  ✓ Decorator without parentheses passed!\n")


def test_mcp_decorator_with_custom_description():
    """Test MCP decorator with custom description parameter."""
    print("Testing MCP decorator with custom description...")
    
    # Test 1: Custom description overrides docstring (keyword arg)
    @mcp_tool(description="Custom tool description")
    def method_with_custom_desc(self, param: str):
        """This should be ignored.
        
        :param param: Parameter description
        """
        return []
    
    assert method_with_custom_desc._mcp_desc == "Custom tool description"
    assert method_with_custom_desc._mcp_schema['properties']['param']['description'] == "Parameter description"
    print(f"  Custom description (keyword): '{method_with_custom_desc._mcp_desc}'")
    
    # Test 2: Positional argument style
    @mcp_tool("Positional description")
    def method_with_positional_desc(self, value: int):
        """This should also be ignored.
        
        :param value: Integer value
        """
        return []
    
    assert method_with_positional_desc._mcp_desc == "Positional description"
    assert method_with_positional_desc._mcp_schema['properties']['value']['description'] == "Integer value"
    print(f"  Custom description (positional): '{method_with_positional_desc._mcp_desc}'")
    
    # Test 3: Empty parentheses (should use docstring)
    @mcp_tool()
    def method_with_empty_parens(self, data: str):
        """Method with empty parens.
        
        :param data: Data parameter
        """
        return []
    
    assert method_with_empty_parens._mcp_desc == "Method with empty parens."
    print(f"  Empty parens description: '{method_with_empty_parens._mcp_desc}'")
    
    print("  ✓ Custom description tests passed!\n")


if __name__ == '__main__':
    print("=" * 60)
    print("Docstring Parser Tests")
    print("=" * 60 + "\n")
    
    try:
        test_google_style()
        test_numpy_style()
        test_sphinx_style()
        test_parse_docstring_complete()
        test_extract_tool_description()
        test_complex_types_from_docstring()
        test_type_priority()
        test_mcp_decorator_integration()
        test_mcp_decorator_without_parentheses()
        test_mcp_decorator_with_custom_description()
        
        print("=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
