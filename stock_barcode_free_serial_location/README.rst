===========================================
Stock Barcode - Free Serial Location Pick
===========================================

An Odoo 17 module that fixes barcode picking stock integrity in two ways:

1. **Serial source location correction** — when a serial is physically picked from
   a different location than Odoo reserved, the move line ``location_id`` is
   corrected at validation.
2. **Reserved quantity enforcement** — operators cannot add products that are not
   on the transfer, or scan more units than were reserved (all tracking types).

**Author:** John Ashurst
**Company:** SJR Nebula
**License:** LGPL-3
**Version:** 17.0.1.0.0

When using the Odoo Barcode app for picking operations with serial-tracked
products, Odoo reserves stock from a specific source location (e.g. *LocA*).
If an operator physically picks the item from a different location (e.g. *LocB*),
Odoo does **not** update the source location on the move line. This results in:

- **-1 (negative) stock** at the physically-picked location (LocB)
- **Phantom +1 stock** remaining at the reserved location (LocA)

Additionally, Odoo's default barcode model allows operators to add products that
were never reserved on the transfer, or to scan more units than reserved, which
leads to over-picking and incorrect stock levels.

This module addresses both problems. Operators can scan serials from any
physical location (location is corrected at validate), while scans that would
add unreserved products or exceed reserved quantities are blocked immediately
with a danger notification.

Overview
========

**Location correction (serial-tracked products)**

Odoo's reservation system assigns a specific ``location_id`` to each
``stock.move.line`` when a picking is confirmed. The Barcode app JS model
(``BarcodePickingModel``) finds the reserved move line when a serial is scanned
and marks it as done, but never updates ``location_id`` to reflect where the
serial was physically collected from. The result is that the stock move is
recorded as ``LocA -> Destination`` even though the item came from ``LocB``.

At validation, this module queries ``stock.quant`` for each done serial and
writes the correct source location on the move line before Odoo records the
stock move.

**Reserved quantity enforcement (all product types)**

During scanning, the patched barcode model compares the total ``qty_done`` for
each product against the quantity reserved on the transfer when the operation
was opened. Scans that would add a product with no reservation, or push
``qty_done`` above that cap, are rejected with an in-app danger notification.
This applies to serial, lot, and untracked products alike.

Installation
============

1. Copy the ``stock_barcode_free_serial_location`` folder to your Odoo addons
   directory (alongside your other custom addons).
2. Update the apps list: **Settings → Apps → Update Apps List**.
3. Search for *"Stock Barcode - Free Serial Location Pick"* and install.

Dependencies
============

* ``stock_barcode`` (standard Odoo Barcode app)

Configuration
=============

No configuration is required. The module works automatically for all picking
operations once installed.

Usage
=====

Warehouse operators can continue using the Barcode app with two guardrails:

1. Open a picking in the Barcode app.
2. Scan products and serials as usual — serials may be picked from any location;
   the source ``location_id`` is corrected automatically at **Validate**.
3. If you scan a product that is not on the transfer, or scan more units than
   reserved, a danger notification is shown and the scan is blocked immediately
   (no confirmation dialog).
4. Press **Validate**.

Features
========

- **Auto-corrects source location** for serial-tracked move lines at validation
  time; operators never need to manually override the source location
- **Smart serial line matching** — when a serial is scanned, the barcode model
  finds an unstarted reserved line for that product and updates it instead of
  creating a duplicate move line
- **Reserved quantity enforcement** — blocks adding unreserved products and
  over-scanning for any tracking type (serial, lot, or none), with an immediate
  danger notification. Applies to warehouse flow operations (Receipts,
  Deliveries, Pick, Pack); standalone Internal Transfers keep Odoo's default
  behaviour of allowing extra products
- **No extra steps** required from warehouse operators beyond normal scanning
- **No UI changes** — works silently in the background
- **Safe fallback** — skips location correction when the serial cannot be found
  in stock; Odoo's standard validation error surfaces these cases
- **Never rewrites completed movements** — lines already in state ``done`` are
  left untouched, so re-validating a picking cannot reverse a transfer that has
  already happened

Technical Notes
===============

The module operates across two layers:

**Python (server-side) — location correction**

``stock.move.line.fix_serial_source_location()``
  For each serial-tracked line in the recordset, searches ``stock.quant`` for
  a positive internal quant matching the serial number. If found in a different
  location than the reserved one, updates ``location_id`` on the move line.

  Lines already in state ``done`` are skipped. This is a correctness
  requirement, not a defensive nicety: writing ``location_id`` on a done move
  line makes Odoo reverse the completed movement
  (``stock/models/stock_move_line.py:502-521``) — it takes the quantity back off
  the destination, returns it to the old source, then re-applies the move from
  the new source. Since a validated picking has already deposited the serial at
  its destination, running the fix again would rewrite the source *to* the
  destination, undo the transfer and return the serial to where it started,
  while the picking still displays as done. Odoo records this in the chatter as
  "The done move line has been corrected."

``stock.picking.button_validate()``
  Before delegating to the standard validation flow, collects the serial-tracked
  lines that are not yet done and calls ``fix_serial_source_location()``.

  The not-done filter matters. ``button_validate()`` is re-entered routinely — a
  double-click on Validate, or the backorder wizard calling it a second time
  (``stock/wizard/stock_backorder_confirmation.py:67``). Odoo's own ``super()``
  is harmless in that situation because done moves are filtered out
  (``stock/models/stock_move.py:1914``), but this override runs *before*
  ``super()``, so it must exclude done lines itself.

``stock.picking._get_stock_barcode_data()``
  Adds an ``enforce_reservation_limit`` flag to the barcode client config. It is
  false for standalone Internal Transfers and true for everything else. Pick,
  Pack and Internal Transfer all share ``picking_type.code == 'internal'``, so
  the operation type is compared against the warehouse's ``int_type_id`` foreign
  key, which is stable, rather than against the user-editable ``sequence_code``
  prefix.

**JavaScript (client-side) — scanning behaviour**

``BarcodePickingModel._isOverReserved()`` (new)
  Helper shared by the patches below. Sums ``reserved_uom_qty`` for the product
  across ``pageLines`` and compares it against the running ``qty_done`` total.
  Returns true and raises a danger notification when the product has no
  reservation on the transfer, or when the requested delta would exceed it.
  Inert when ``config.enforce_reservation_limit`` is false.

``BarcodePickingModel.createNewLine()`` (patch)
  For serial-tracked products, searches ``pageLines`` for an unstarted reserved
  line for that product. If found, redirects to ``updateLine()`` on that line
  instead of creating a new one, so the Python validation step can correct
  ``location_id`` when needed.

  For all product types, rejects the scan when the product has no reservation
  on the transfer or when adding one more unit would exceed the reserved total.

  Before redirecting, it points ``lastScanned.sourceLocation`` at the reserved
  line's own location. Odoo's ``updateLine()`` stamps that value onto
  ``line.location_id`` whenever the caller does not pass one explicitly
  (``stock_barcode/static/src/models/barcode_picking_model.js:214-216``), so
  without this the redirect would overwrite the reserved line's source.

``BarcodePickingModel.updateLine()`` (patch)
  Enforces the reserved cap on every quantity increment that carries a
  ``qty_done`` (barcode scans and the + button), including the increments routed
  here by the ``createNewLine()`` patch above.

Edge Cases
==========

* **Serial in transit on another picking:** quant still shows original location;
  source location is corrected to that location.
* **Serial does not exist in stock:** quant query returns nothing; location is
  unchanged and standard Odoo validation error is raised.
* **Scan exceeds reserved quantity:** danger notification; scan blocked for
  all product types.
* **Product not on the transfer:** danger notification; scan blocked immediately
  (Odoo's "add extra product?" confirmation is not shown).
* **Lot or untracked products:** source location fix is skipped at validation;
  reserved quantity enforcement still applies during scanning.
* **Standalone internal transfer:** reserved quantity guard is disabled;
  operators may add arbitrary products. Pick and Pack stay guarded.
* **Source location already correct:** no write is performed.
* **Picking validated twice** (double-click, or backorder wizard re-entry): the
  second pass skips all done lines, so the completed transfer is left intact.

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
