/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import BarcodePickingModel from "@stock_barcode/models/barcode_picking_model";

patch(BarcodePickingModel.prototype, {
    /**
     * Don't flag serial-tracked lines as faulty when qty_done > reserved_uom_qty.
     * The source location will be corrected at validation time by fix_serial_source_location,
     * so the "extra" line (reserved_uom_qty=0, qty_done=1) from scanning a serial at a
     * different location is intentional and should not show red.
     */
    lineIsFaulty(line) {
        if (line.product_id?.tracking === "serial" && (line.lot_id || line.lot_name)) {
            return false;
        }
        return super.lineIsFaulty(line);
    },
});
