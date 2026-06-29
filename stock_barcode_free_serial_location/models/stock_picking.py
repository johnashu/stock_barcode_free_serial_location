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
        """
        done_serial_lines = self.move_line_ids.filtered(
            lambda l: l.qty_done > 0
            and l.product_id.tracking == "serial"
            and l.lot_id
            and l.company_id == self.company_id
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
