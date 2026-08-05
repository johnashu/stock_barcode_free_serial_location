# -*- coding: utf-8 -*-
from odoo import models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def button_validate(self):
        """Validate the picking, correcting serial source locations first.

        Before delegating to the standard validation flow, find all serial-tracked
        move lines that have been marked as done and auto-correct their source
        location to match where the serial actually lives in stock. This handles
        the case where a barcode operator picks a serial from a location different
        to the one Odoo originally reserved, which would otherwise produce negative
        stock at the physical pick location.

        Already-done lines are excluded. ``button_validate()`` can legitimately be
        re-entered on a picking that is already done -- a double-click, or the
        backorder wizard calling it a second time
        (odoo/addons/stock/wizard/stock_backorder_confirmation.py:67) -- and
        Odoo's own ``super()`` is a no-op in that case because done moves are
        filtered out at odoo/addons/stock/models/stock_move.py:1914. This override
        runs *before* ``super()``, so without this guard it would still rewrite the
        source location of lines whose stock has already moved, reversing the
        transfer. See ``fix_serial_source_location`` for the mechanism.

        There is deliberately no company filter here. ``self.move_line_ids`` are
        by definition the lines of this picking, and each line's ``company_id``
        is copied from its move (or the picking) at creation
        (odoo/addons/stock/models/stock_move_line.py:343-346), so the comparison
        never excluded anything. The company filter that does matter is on the
        quant search in ``fix_serial_source_location``, which is scoped to
        ``line.company_id``.
        """
        done_serial_lines = self.move_line_ids.filtered(
            # lambda l: l.state != "done"
            # and
            l.qty_done > 0 and l.product_id.tracking == "serial" and l.lot_id
        )
        done_serial_lines.fix_serial_source_location()
        return super().button_validate()

    def _get_stock_barcode_data(self):
        """Add a barcode-only flag for the reserved-quantity guard in JS.

        Receipts, deliveries, pick and pack should block over-scanning in the
        barcode app. Standalone internal transfers should not — operators may
        add arbitrary products when moving stock between locations.

        Pick, pack and internal transfer all share picking_type.code ==
        'internal', so we cannot use that alone. Instead we compare this
        operation type to the warehouse's int_type_id FK (stable; unlike the
        user-editable sequence_code prefix).
        """
        data = super()._get_stock_barcode_data()
        picking_type = self.picking_type_id
        enforce_reservation_limit = True

        if picking_type.code == "internal":
            warehouse = picking_type.warehouse_id
            enforce_reservation_limit = (
                not warehouse or picking_type.id != warehouse.int_type_id.id
            )
        data["config"]["enforce_reservation_limit"] = enforce_reservation_limit
        return data
