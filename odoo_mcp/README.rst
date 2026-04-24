=================
Odoo MCP Framework
=================

.. image:: /odoo_mcp/static/description/icon.png
   :alt: Odoo MCP Framework Logo
   :align: center
   :width: 200px

.. image:: https://img.shields.io/badge/license-%20%20GNU%20LGPLv3%20-green?style=plastic&logo=gnu
   :target: https://www.gnu.org/licenses/lgpl-3.0.txt
   :alt: License: LGPL-3

.. image:: https://img.shields.io/badge/github-repo-blue?logo=github
   :target: https://github.com/chrisking94/odoo_addons/tree/main/odoo_mcp
   :alt: Github Repo

**Connect Odoo ERP to AI Agents with One Line of Code**

This module transforms your Odoo instance into a **Model Context Protocol (MCP) Server**, enabling seamless integration with AI agents like Claude, ChatGPT, Cursor, and other Large Language Models (LLMs).

The standout feature is its **simplicity**: expose any Odoo model method to AI agents with just one decorator line.

Key Features
============

* **One-Line Setup**: Use ``@mcp_tool`` decorator to expose methods instantly
* **Type-Safe**: Automatic JSON schema generation from Python type hints
* **Modern Protocol**: Implements MCP Streamable HTTP transport (2025-03-26)
* **Zero Config**: No additional setup required beyond installation
* **Production Ready**: Built-in error handling, logging, and CORS support

Quick Start
===========

1. Install the module in your Odoo instance
2. Decorate your model methods with ``@mcp_tool``
3. Configure your MCP client to connect to ``http://your-odoo:8069/mcp``

Usage Example
=============

Basic Tool Definition
---------------------

Add the decorator to any model method you want to expose:

.. code-block:: python

    from odoo.addons.odoo_mcp import mcp_tool  # IDE might complain package missing, but don't worry, odoo can find it.
    from odoo import models

    class ResPartner(models.Model):
        _inherit = 'res.partner'
        
        @mcp_tool(description="Search for customers by name")
        def search_customers(self, name: str):
            """Search customers and return their details."""
            partners = self.search([('name', 'ilike', name)], limit=10)
            return [{
                'id': p.id,
                'name': p.name,
                'email': p.email,
                'phone': p.phone
            } for p in partners]

Advanced Type Hints
-------------------

The decorator automatically generates JSON schemas from Python type annotations:

.. code-block:: python

    from typing import List, Optional
    
    @mcp_tool(description="Get customer orders")
    def get_customer_orders(
        self, 
        partner_id: int,
        status: Optional[str] = None,
        limit: int = 10
    ):
        """Retrieve orders for a specific customer."""
        domain = [('partner_id', '=', partner_id)]
        if status:
            domain.append(('state', '=', status))
        
        orders = self.env['sale.order'].search(domain, limit=limit)
        return [{
            'id': o.id,
            'name': o.name,
            'total': o.amount_total,
            'status': o.state
        } for o in orders]

Supported Types
---------------

The decorator supports these Python type annotations:

* Basic types: ``str``, ``int``, ``float``, ``bool``
* Collections: ``List[str]``, ``Dict``, ``Tuple[int, ...]``
* Optional: ``Optional[str]`` (automatically sets default to null)
* Default values are extracted and included in the schema

Client Configuration
====================

Your MCP endpoint will be available at: ``http://your-odoo-server:8069/mcp``

ChatWise
--------

1. Open ChatWise settings
2. Navigate to MCP Servers
3. Add new server → Select "Streamable HTTP"
4. Enter your Odoo URL: ``http://localhost:8069/mcp``

Cursor
------

1. Go to Settings → MCP
2. Click "Add Server"
3. Choose Streamable HTTP transport
4. Configure endpoint URL

Claude Desktop
--------------

Edit your ``config.json``:

.. code-block:: json

    {
      "mcpServers": {
        "odoo": {
          "url": "http://localhost:8069/mcp",
          "transport": "streamable-http"
        }
      }
    }

Architecture
============

Streamable HTTP Transport
-------------------------

This module implements the latest MCP protocol specification (2025-03-26) using Streamable HTTP transport:

* **GET /mcp**: Establishes SSE stream for server-to-client notifications
* **POST /mcp**: Receives JSON-RPC 2.0 requests from clients

The implementation uses a monkey patch to bypass Odoo's strict request type checking, allowing both GET and POST requests on the same endpoint while maintaining full control over response formatting.

Protocol Flow
-------------

1. Client connects via GET to establish SSE stream
2. Client sends ``initialize`` request via POST
3. Server responds with protocol version and capabilities
4. Client sends ``notifications/initialized`` (no response needed)
5. Client can now call ``tools/list`` and ``tools/call``

For Developers
==============

Debugging
---------

Enable debug logging to see MCP activity:

.. code-block:: bash

    odoo-bin --log-handler=odoo.addons.odoo_mcp.controllers.main:DEBUG

This will log:
* Received MCP methods and parameters
* Found tools during scanning
* Tool execution errors with full tracebacks

Creating Custom Tools
---------------------

Best practices for creating MCP tools:

1. **Use descriptive names**: The method name should clearly indicate its purpose
2. **Add type hints**: Enables automatic schema generation
3. **Write clear descriptions**: Helps AI agents understand when to use the tool
4. **Return simple structures**: Dicts and lists serialize best to JSON
5. **Handle errors gracefully**: Return meaningful error messages

Example:

.. code-block:: python

    @mcp_tool(description="Calculate product profit margin")
    def calculate_margin(self, product_id: int, cost: float):
        """Calculate profit margin for a product given its cost."""
        try:
            product = self.env['product.product'].browse(product_id)
            if not product.exists():
                return {'error': f'Product {product_id} not found'}
            
            revenue = product.list_price
            margin = ((revenue - cost) / revenue) * 100 if revenue else 0
            
            return {
                'product': product.name,
                'revenue': revenue,
                'cost': cost,
                'margin_percent': round(margin, 2)
            }
        except Exception as e:
            return {'error': str(e)}

Testing
=======

A test script is provided to verify your MCP server setup:

.. code-block:: bash

    python test_mcp.py http://localhost:8069

This will test:
* SSE stream connection
* Initialize handshake
* Tool listing
* Tool execution (if configured)

Troubleshooting
===============

No tools found
--------------

If ``tools/list`` returns an empty list:

1. Ensure your module with ``@mcp_tool`` decorated methods is installed
2. Check that methods are defined on models (not regular Python classes)
3. Verify methods don't start with underscore (private methods are skipped)
4. Enable debug logging to see scanning results

Connection errors
-----------------

If clients can't connect:

1. Verify Odoo is running and accessible
2. Check firewall settings allow connections to port 8069
3. Ensure the URL format is correct: ``http://host:port/mcp``
4. For remote access, configure Odoo's ``--db_host`` and network settings

Protocol errors
---------------

If you see JSON-RPC errors:

1. Check Odoo logs for detailed error messages
2. Verify your MCP client supports Streamable HTTP transport
3. Ensure you're using MCP protocol version 2025-03-26 or compatible

Bug Tracker
===========

Bugs are tracked on `GitHub Issues <https://github.com/chrisking94/odoo_addons/issues>`_.

Maintainer
==========

.. image:: https://avatars.githubusercontent.com/u/29966935
   :alt: Chris King Github Home
   :target: https://github.com/chrisking94
   :width: 80px

This module is maintained by **Chris**.
