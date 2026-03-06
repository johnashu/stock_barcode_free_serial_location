/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import BarcodePickingModel from "@stock_barcode/models/barcode_picking_model";

patch(BarcodePickingModel.prototype, {
    createNewLine(params) {
        const product = params.fieldsParams?.product_id;

        if (product?.tracking === "serial") {

            const reservedLine = this.pageLines.find(
                (line) =>
                    line.product_id.id === product.id &&
                    !this.getQtyDone(line) &&
                    line.reserved_uom_qty > 0
            );

            if (reservedLine) {
                this.lastScanned.sourceLocation = reservedLine.location_id;
                return this.updateLine(reservedLine, params.fieldsParams).then(() => reservedLine);
            } 
        }

        return super.createNewLine(params);
    },
});
