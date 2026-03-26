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
Odoo does **not** update the source location on the move line. This results in:

- **-1 (negative) stock** at the physically-picked location (LocB)
- **Phantom +1 stock** remaining at the reserved location (LocA)

This module eliminates that friction. It automatically corrects source locations
at validation time **and** enforces reserved quantities in real time during
scanning — preventing both stock integrity issues and over-picking, for all
product tracking types.

**Table of contents**

.. contents::
   :local:

Problem in Detail
=================

Odoo's reservation system assigns a specific ``location_id`` to each
``stock.move.line`` when a picking is confirmed. The Barcode app JS model
(``BarcodePickingModel``) finds the reserved move line when a serial is scanned
and marks it as done — but never updates ``location_id`` to reflect where the
serial was physically collected from. The result is that the stock move is
recorded as ``LocA → Destination`` even though the item came from ``LocB``.

Additionally, Odoo's default barcode model does not prevent a user from scanning
more units than were reserved on the picking, which can lead to over-picking and
incorrect stock levels.

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
3. If you attempt to scan more units than the picking has reserved for a
   product, a warning notification is shown immediately and the scan is blocked.
4. Press **Validate**.

At validation, the module queries ``stock.quant`` to find where each scanned
serial actually has positive stock and updates the move line's source location
accordingly before Odoo records the stock move.

Features
========

- **Auto-corrects source location** for serial-tracked move lines at validation
  time — operators never need to manually override the source location
- **Smart serial line matching** — when a serial is scanned, the JS model
  finds the most appropriate unstarted reserved line rather than always creating
  a new one, preserving reservation integrity
- **Reserved quantity enforcement** — prevents scanning more units than reserved
  for *any* product type (serial, lot, or untracked), with an immediate
  in-app danger notification
- **No extra steps** required from warehouse operators — fully transparent
- **No UI changes** — works silently in the background
- **Safe fallback** — skips lines where the serial cannot be found in stock;
  Odoo's standard validation error will surface these naturally

Technical Notes
===============

The module operates across two layers:

**Python (server-side)**

``stock.move.line.fix_serial_source_location()``
    For each serial-tracked line in the recordset, searches ``stock.quant`` for
    a positive internal quant matching the serial number. If found in a different
    location than the reserved one, updates ``location_id`` on the move line.

``stock.picking.button_validate()``
    Before delegating to the standard validation flow, collects all done
    serial-tracked lines and calls ``fix_serial_source_location()``.

**JavaScript (client-side)**

``BarcodePickingModel.createNewLine()`` (patch)
    For serial-tracked products, searches ``pageLines`` for an unstarted
    reserved line for that product. If found, redirects to ``updateLine()``
    on that line instead of creating a new one, preserving the reservation.

    For all product types, checks whether the total ``qty_done`` across all
    lines for the product would exceed the total ``reserved_uom_qty``. If so,
    shows a danger notification and aborts the scan.

``BarcodePickingModel.updateLine()`` (patch)
    For all product types, checks whether the new ``qty_done`` value would push
    the total done quantity over the total reserved. If so, shows a danger
    notification and aborts the update. This covers subsequent scans of the same
    product where an existing line is incremented rather than a new one created.

**Edge cases:**

======================================  =======================================
Scenario                                Behaviour
======================================  =======================================
Serial in transit on another picking    Quant still shows original location;
                                        location corrected to that location.
Serial does not exist in stock          Quant query returns nothing; location
                                        unchanged - standard Odoo error raised.
Scan exceeds reserved quantity          Danger notification shown immediately;
                                        scan blocked for all product types.
Lot / untracked products                Source location fix skipped; quantity
                                        guard still applies.
Source location already correct         No write performed.
Product has no reservation              Quantity guard not applied (no reserved
                                        qty to enforce against).
======================================  =======================================

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
