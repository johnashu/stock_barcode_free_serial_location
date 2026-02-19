# -*- coding: utf-8 -*-
{
    "name": "Stock Barcode - Free Serial Location Pick",
    "version": "17.0.1.0.0",
    "category": "Inventory/Inventory",
    "summary": "Pick serial-tracked products from any location, not just the reserved one",
    "description": """
Stock Barcode - Free Serial Location Pick
==========================================

When using the Odoo Barcode app for picking operations with serial-tracked
products, Odoo reserves stock from a specific source location (e.g. LocA).
If an operator physically picks the item from a different location (e.g. LocB),
Odoo does not update the source location on the move line. This results in
negative stock at LocB and phantom stock remaining at LocA — a known limitation
of the default barcode picking flow.

This module corrects the source location on serial-tracked move lines
automatically at validation time. It looks up where each scanned serial
actually lives in stock and updates the move line's source location to match,
eliminating the negative stock problem without requiring any extra steps from
warehouse operators.

Features
--------
* Auto-corrects source location for serial-tracked move lines on validate
* Looks up actual serial quant to determine the real pick location
* No UI changes or extra steps required for warehouse staff
* Non-intrusive: only affects serial-tracked lines with qty_done > 0
* Safe: skips lines where the serial cannot be found in stock (surfaces as
  a normal Odoo validation error)

Technical Details
-----------------
* Overrides ``stock.picking.button_validate`` to fix locations pre-validation
* Extends ``stock.move.line`` with a helper method for location correction
* Queries ``stock.quant`` for the positive internal quant of each serial

Author: John Ashurst
Company: SJR Nebula
    """,
    "author": "SJR Nebula - John Ashurst",
    "website": "https://sjr.ie",
    "license": "LGPL-3",
    "depends": ["stock_barcode"],
    "installable": True,
    "auto_install": False,
    "application": False,
}
