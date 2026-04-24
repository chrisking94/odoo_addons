{
    'name': 'Odoo MCP Framework',
    'version': '15.0.1.0.0',
    'summary': 'Native Model Context Protocol (MCP) Server for Odoo',
    'description': """
        This addon provides a framework to turn Odoo into a MCP Server.
        Developers can use the `@mcp_tool` decorator to expose ORM methods 
        to AI Agents and LLMs.
    """,
    'category': 'Tools/AI',
    'author': 'Chris',
    'website': 'https://github.com/chrisking94/odoo_addons/tree/main/odoo_mcp',
    'license': 'LGPL-3',
    'depends': ['base'],
    'external_dependencies': {
        'python': [],
    },
    'data': [
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
