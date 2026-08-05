# -*- coding: utf-8 -*-
{
    "name": "Stock Barcode - Free Serial Location Pick",
    "version": "17.0.0.1.3",
    "category": "Inventory/Inventory",
    "summary": "Pick serial-tracked products from any location, not just the reserved one",
    "description": """
Stock Barcode - Free Serial Location Pick
==========================================

When using the Odoo Barcode app for picking operations with serial-tracked
products, Odoo reserves stock from a specific source location (e.g. LocA).
If an operator physically picks the item from a different location (e.g. LocB),
Odoo records the stock move from the originally-reserved location (LocA). Since
the serial's actual quant is at LocB, this causes negative stock at LocA and
leaves phantom stock at LocB.

This module corrects the source location on serial-tracked move lines
automatically at validation time. It looks up where each scanned serial
actually lives in stock (via stock.quant) and updates the move line's source
location to match before Odoo records the stock move.

It also enforces reserved quantities during barcode scanning: operators cannot
add products that are not on the transfer or scan more units than were reserved.
This enforcement applies to warehouse flow operations (Receipts, Deliveries,
Pick and Pack) and is skipped for standalone Internal Transfers, which keep
Odoo's default behaviour of allowing extra products.

Features
--------
* Auto-corrects source location for serial-tracked move lines on validate
* Looks up actual serial quant to determine the real pick location
* Smart serial line matching — routes serial scans to the reserved move line
* Blocks unreserved products and over-scanning on warehouse flow operations
  (Receipts, Deliveries, Pick, Pack); standalone Internal Transfers are exempt
* No UI changes or extra steps required for warehouse staff
* Non-intrusive: location fix only affects serial-tracked lines with qty_done > 0
* Safe: skips lines where the serial cannot be found in stock (surfaces as
  a normal Odoo validation error)

Technical Details
-----------------
* JS patch on BarcodePickingModel (createNewLine, updateLine) for serial line
  matching and reserved-quantity enforcement
* Overrides ``stock.picking.button_validate`` to fix locations pre-validation
* Never touches lines already in state ``done``, so re-validating a picking
  (double-click, backorder wizard) cannot reverse a completed transfer
* Extends ``stock.move.line`` with a helper method for location correction
* Queries ``stock.quant`` for the positive internal quant of each serial

Author: SJR Nebula
Company: SJR Nebula
Email: info@sjr.ie
Website: https://sjr.ie
    """,
    "author": "SJR Nebula",
    "website": "https://sjr.ie",
    "email": "info@sjr.ie",
    "license": "LGPL-3",
    "depends": ["stock_barcode"],
    "assets": {
        "web.assets_backend": [
            "stock_barcode_free_serial_location/static/src/models/barcode_picking_model_patch.js",
        ],
    },
    "images": ["static/description/main_screenshot.png"],
    "installable": True,
    "auto_install": False,
    "application": False,
}
