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
        )
        done_serial_lines.fix_serial_source_location()
        return super().button_validate()
