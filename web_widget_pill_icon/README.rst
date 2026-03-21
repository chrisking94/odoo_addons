======================
Web Widget Pill Icon
.. image:: img.shields.io
:target: www.gnu.org
:alt: License: LGPL-3
This module provides a highly flexible, pure frontend widget to transform any text, selection, or numeric field into a stylish "Pill" or "Badge" with dynamic icons and semantic colors.
The standout feature is its decoupling from the backend: you can configure icons and styles entirely within the XML view options, making your list and form views significantly more recognizable without touching Python code.
Key Features

* Type Agnostic: Works with Selection, Char, Integer, Float, and Many2one fields.
* Always Readonly: Designed as a visualization tool; it maintains its clean UI even when the form is in Edit mode.
* Semantic Mapping: Map specific database values to FontAwesome icons and CSS classes.
* Smart Alignment: Custom CSS fixes common Odoo "drifting" issues when clicking rows in List View.
* Built-in Utility Classes: Includes pre-defined styles like pill, outline, and soft semantic colors (success, danger, etc.).

Usage
To apply the widget, use widget="pill_icon" and provide a values mapping in the options attribute:
.. code-block:: xml
Configuration Options
The widget accepts two main keys in the options dictionary:

   1. base (String)

------------------------------
Global CSS classes applied to the widget container. Recommended built-in classes:

* pill: Rounder corners and standard padding.
* outline: Transparent background with a colored border.
* sm / lg: Adjusts the scale of the pill.


   1. values (Dictionary)

------------------------------
A mapping where the Key is the field's raw value and the Value is a string containing:

* Icons: Any FontAwesome 4.7 class (e.g., fa-star, fa-pencil).
* Colors: Semantic classes like success, warning, danger, info, primary, or muted.

CSS Utility Reference
This module includes a built-in stylesheet with optimized "Soft UI" colors:
+-----------+-----------------------+-----------------------+
| Class | Background (Light) | Text Color |
+===========+=======================+=======================+
| success | Soft Green | Dark Green |
+-----------+-----------------------+-----------------------+
| warning | Soft Yellow | Dark Gold |
+-----------+-----------------------+-----------------------+
| danger | Soft Red | Dark Red |
+-----------+-----------------------+-----------------------+
| info | Soft Blue | Dark Blue |
+-----------+-----------------------+-----------------------+
| primary | Soft Royal Blue | Dark Royal Blue |
+-----------+-----------------------+-----------------------+
| muted | Light Grey | Dark Grey |
+-----------+-----------------------+-----------------------+
Bug Tracker
Bugs are tracked on GitHub Issues <https://github.com/chrisking94/odoo_addons/issues>_.
Maintainer
.. image:: https://avatars.githubusercontent.com/u/29966935
:alt: Chris King Github Home
:target: https://github.com/chrisking94
:width: 80px
