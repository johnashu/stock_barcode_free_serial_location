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
        - The line is already done (see below)
        - The product is not serial-tracked
        - No lot/serial is set on the line
        - No positive internal quant can be found for the serial (Odoo's own
          validation will surface this as an error)
        - The quant location already matches the move line location

        The done check is critical, not defensive. Writing ``location_id`` on a
        done move line makes Odoo *reverse* the completed movement
        (odoo/addons/stock/models/stock_move_line.py:502-521): it takes the
        quantity back off the destination, returns it to the old source, then
        re-applies the move from the new source. On a picking that has already
        been validated the serial's quant now sits at the *destination*, so this
        method would rewrite the source to the destination, undo the transfer and
        return the serial to where it started -- while the picking still reads as
        done. Odoo logs it as "The done move line has been corrected."
        """
        for line in self:
            if line.state == "done":
                continue

            if line.product_id.tracking != "serial" or not line.lot_id:
                continue

            actual_quant = (
                self.env["stock.quant"]
                .sudo()
                .search(
                    [
                        ("lot_id", "=", line.lot_id.id),
                        ("product_id", "=", line.product_id.id),
                        ("company_id", "=", line.company_id.id),
                        ("quantity", ">", 0),
                        ("location_id.usage", "=", "internal"),
                    ],
                    limit=1,
                )
            )

            if actual_quant and actual_quant.location_id != line.location_id:
                line.location_id = actual_quant.location_id
