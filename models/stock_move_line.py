# -*- coding: utf-8 -*-
from odoo import models


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    def fix_serial_source_location(self):
        """Update source location to match where each serial actually lives in stock.

        For each serial-tracked move line in the recordset, queries stock.quant for
        the actual positive internal quant of that serial. If the quant is in a
        different location than the reserved one on the move line, the move line's
        location_id is corrected before the picking is validated.

        This prevents negative stock at the physically-picked location and phantom
        stock remaining at the originally-reserved location when an operator picks
        a serial from a location other than the one Odoo reserved.

        Lines are skipped (left unchanged) when:
        - The product is not serial-tracked
        - No lot/serial is set on the line
        - No positive internal quant can be found for the serial (Odoo's own
          validation will surface this as an error)
        - The quant location already matches the move line location
        """
        for line in self:
            if line.product_id.tracking != "serial" or not line.lot_id:
                continue

            actual_quant = (
                self.env["stock.quant"]
                .sudo()
                .search(
                    [
                        ("lot_id", "=", line.lot_id.id),
                        ("product_id", "=", line.product_id.id),
                        ("quantity", ">", 0),
                        ("location_id.usage", "=", "internal"),
                    ],
                    limit=1,
                )
            )

            if actual_quant and actual_quant.location_id != line.location_id:
                line.location_id = actual_quant.location_id
