================
Web Widget YAML
================

.. image:: /web_widget_yaml/static/description/icon.png
   :alt: Web Widget YAML Logo
   :align: center
   :width: 200px

.. image:: https://img.shields.io
   :target: http://www.gnu.org
   :alt: License: LGPL-3

.. image:: https://img.shields.io
   :target: https://github.com
   :alt: OCA/web

This module provides a dedicated YAML code editor widget for Odoo form views, 
extending the capabilities of the standard Ace Editor.

The standout feature of this addon is its **flexibility**: unlike the standard
Odoo Ace widget, this one allows developers to pass any configuration option
directly via the ``options`` attribute in the XML view.

Usage
=====

To apply the YAML editor to a field, use ``widget="yaml"`` in your XML view:

.. code-block:: xml

    <field name="my_yaml_config"
           widget="yaml"
           options="{'fontSize': 14, 'theme': 'ace/theme/monokai', 'minLines': 15}"/>

Advanced Configuration
======================

This widget supports all standard Ace Editor options. You can find a complete list of
supported configuration keys and their values in the `Official Ace Configuration Wiki <https://github.com/ajaxorg/ace/wiki/Configuring-Ace>`_.

Commonly used options include:
* ``theme``: Visual style (e.g., ``'ace/theme/monokai'``, ``'ace/theme/chrome'``).
* ``fontSize``: Text size in pixels (e.g., ``14``).
* ``minLines`` / ``maxLines``: Control editor height.
* ``showPrintMargin``: Show or hide the vertical guide line.

Bug Tracker
===========

Bugs are tracked on `GitHub Issues <https://github.com>`_.

Maintainer
==========

.. image:: https://odoo-community.org
   :alt: Odoo Community Association
   :target: https://odoo-community.org

This module is maintained by the OCA.
