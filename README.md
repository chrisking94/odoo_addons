# Odoo Addons

Welcome to this Odoo addons repository.  
This collection contains custom modules designed to enhance the Odoo user experience and provide developers with more flexible tools.

---

## 🛠 Available Addons

| Module Name          | Description                                                                 | Link                                  |
|----------------------|-----------------------------------------------------------------------------|---------------------------------------|
| Odoo MCP Framework   | [NEW] Transform Odoo into AI-ready MCP Server with one decorator.           | [View Module](./odoo_mcp)             |
| Web Widget Pill Icon | Dynamic icons & semantic colors for any field via XML options.              | [View Module](./web_widget_pill_icon) |
| Web Widget YAML      | Advanced YAML editor with customizable Ace editor options.                  | [View Module](./web_widget_yaml)      |

---

## 🚀 Featured: Odoo MCP Framework

The **Odoo MCP Framework** transforms your Odoo instance into a Model Context Protocol (MCP) Server, enabling seamless integration with AI agents and LLMs.

### Key Highlights:

- **One-Line Setup**: Expose methods to AI with `@mcp_tool` decorator
- **Type-Safe**: Automatic JSON schema generation from Python type hints
- **Modern Protocol**: Implements MCP Streamable HTTP (2025-03-26)
- **Zero Config**: Install and start decorating—no additional setup needed
- **Production Ready**: Built-in error handling, logging, and CORS support

### Quick Example:

```python
from odoo.addons.odoo_mcp import mcp_tool

@mcp_tool(description="Search customers by name")
def search_customers(self, name: str):
    partners = self.search([('name', 'ilike', name)])
    return [{'id': p.id, 'name': p.name} for p in partners]
```

---

## 💎 Also Available: Web Widget Pill Icon

The **Web Widget Pill Icon** is a highly flexible, pure frontend widget that transforms boring text, selection, or numeric fields into stylish "Pills" or "Badges".

### Key Highlights:

- **Decoupled Logic**: Configure icons and semantic colors (`success`, `danger`, `warning`) entirely in the XML `options` attribute.
- **Type Agnostic**: Works seamlessly with `Selection`, `Char`, `Integer`, and `Many2one` fields.
- **Visual Polish**: Includes built-in CSS fixes for Odoo 15 List View alignment and selection issues.
- **Easy Styling**: Supports global base classes like `pill`, `outline`, and `sm`.

---

## ⚙️ Also Available: Web Widget YAML

If you need advanced configuration management, check out **Web Widget YAML**, which provides a dedicated YAML code editor extending the standard Ace Editor.

---

💡 If you find these modules useful, please consider giving this repository a **Star**! 🌟