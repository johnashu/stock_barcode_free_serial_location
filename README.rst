=============================================
Stock Barcode - Free Serial Location Pick
=============================================

.. |badge1| image:: https://img.shields.io/badge/licence-LGPL--3-blue.png
    :target: http://www.gnu.org/licenses/lgpl-3.0-standalone.html
    :alt: License: LGPL-3

.. |badge2| image:: https://img.shields.io/badge/odoo-17.0-blueviolet
    :alt: Odoo 17.0

|badge1| |badge2|

When using the Odoo Barcode app for picking operations with serial-tracked
products, Odoo reserves stock from a specific source location (e.g. *LocA*).
If an operator physically picks the item from a different location (e.g. *LocB*),
Odoo records the stock move from the originally-reserved location (*LocA*) — not
from where the item was actually taken. This results in:

- **Negative stock (-1)** at the reserved location (*LocA*) — because the serial's
  quant is at *LocB*, not *LocA*
- **Phantom stock (+1)** remaining at the physically-picked location (*LocB*) —
  the serial was never moved out of there in the system

This module eliminates that problem by automatically correcting the source
location on serial-tracked move lines at validation time, with no extra steps
required from warehouse staff.

**Table of contents**

.. contents::
   :local:

Problem in Detail
=================

Odoo's reservation system assigns a specific ``location_id`` to each
``stock.move.line`` when a picking is confirmed. The Barcode app JS model
(``BarcodePickingModel``) finds the reserved move line when a serial is scanned
and assigns the scanned serial to it — but the move line's ``location_id`` remains
set to the originally-reserved location (*LocA*). When the picking is validated,
the stock move is recorded as *LocA → Destination* even though the serial's
actual quant lives at *LocB*. This causes negative stock at *LocA* and leaves
the serial's quant intact at *LocB*.

Installation
============

1. Copy the ``stock_barcode_free_serial_location`` folder to your Odoo addons
   directory (alongside your other custom addons).
2. Update the apps list: **Settings → Apps → Update Apps List**.
3. Search for *"Stock Barcode - Free Serial Location Pick"* and install.

**Dependency:** Requires the ``stock_barcode`` module (standard Odoo Barcode app).

Configuration
=============

No configuration is required. The module works automatically for all picking
operations once installed.

Usage
=====

Warehouse operators can continue using the Barcode app exactly as before:

1. Open a picking in the Barcode app.
2. Scan any serial number — regardless of which location Odoo originally
   reserved it from.
3. Press **Validate**.

At validation, the module queries ``stock.quant`` to find where each scanned
serial actually has positive stock and updates the move line's source location
accordingly before Odoo records the stock move.

Features
========

- **Auto-corrects source location** for serial-tracked move lines on validate
- **No extra steps** required from warehouse operators
- **No UI changes** — fully transparent to users
- **Non-intrusive** — only processes serial-tracked lines with ``qty_done > 0``
- **Safe fallback** — skips lines where the serial cannot be found in stock;
  Odoo's standard validation error will surface these naturally
- **Lot-tracked products unaffected** — behaviour unchanged for lot or
  untracked products

Technical Notes
===============

The fix is applied in two layers:

JS patch — ``BarcodePickingModel.createNewLine``
    Intercepts the point where Odoo would otherwise create a duplicate move line.
    When a serial is scanned and no matching reserved line is found, the patch
    locates the first unstarted reserved line for that product and assigns the
    scanned serial to it directly, avoiding a spurious extra line.

``stock.move.line.fix_serial_source_location()``
    For each line in the recordset, searches ``stock.quant`` for a positive
    internal quant matching the serial. If found in a different location than
    the reserved one, updates ``location_id`` on the move line.

``stock.picking.button_validate()``
    Before delegating to the standard validation flow, collects all done
    serial-tracked lines and calls ``fix_serial_source_location()``.

**Edge cases:**

+------------------------------------------+------------------------------------------+
| Scenario                                 | Behaviour                                |
+==========================================+==========================================+
| Serial in transit on another picking     | Quant still shows original location;     |
|                                          | source location corrected to that        |
|                                          | location.                                |
+------------------------------------------+------------------------------------------+
| Serial does not exist in stock           | Quant query returns nothing; location    |
|                                          | unchanged — standard Odoo error raised.  |
+------------------------------------------+------------------------------------------+
| Lot / untracked products                 | Skipped entirely — unchanged behaviour.  |
+------------------------------------------+------------------------------------------+
| Source location already correct          | No write performed.                      |
+------------------------------------------+------------------------------------------+

Support
=======

For support, please contact SJR Nebula:

- Website: https://sjr.ie
- Email: info@sjr.ie

Credits
=======

Authors
-------

* SJR Nebula

Contributors
------------

* John Ashurst
