/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import BarcodePickingModel from "@stock_barcode/models/barcode_picking_model";

patch(BarcodePickingModel.prototype, {
    /**
     * Returns true and shows a danger notification if adding qty (a delta)
     * to the current total qty_done would exceed the total reserved quantity
     * for the product across all pageLines.
     */
    _isOverReserved(product, qty) {
      if (!product?.id) return false;
      const productLines = this.pageLines.filter(
        (l) => l.product_id?.id === product.id,
      );
      const totalReserved = productLines.reduce(
        (sum, l) => sum + (l.reserved_uom_qty || 0),
        0,
      );
      if (!totalReserved) {
        this.notification(
          _t(
            "You cannot add %(product)s because it is not reserved on this transfer.",
            { product: product.display_name },
          ),
          { type: "danger" },
        );
        return true;
      }
      const doneSoFar = productLines.reduce(
        (sum, l) => sum + (this.getQtyDone(l) || 0),
        0,
      );
      if (doneSoFar + qty > totalReserved) {
        this.notification(
          _t(
            "You cannot scan more %(product)s than the reserved quantity (%(reserved)s).",
            { product: product.display_name, reserved: totalReserved },
          ),
          { type: "danger" },
        );
        return true;
      }
      return false;
    },

    createNewLine(params) {
        const product = params.fieldsParams?.product_id;

        if (product && this._isOverReserved(product, 1)) {
          return Promise.resolve(false);
        }
        if (product?.tracking === "serial") {

            const reservedLine = this.pageLines.find(
                (line) =>
                    line.product_id?.id === product.id &&
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

    updateLine(line, params) {
      const product = line.product_id || params.product_id;
      if (
        params.qty_done !== undefined &&
        product?.id &&
        this._isOverReserved(product, params.qty_done)
      ) {
        return Promise.resolve(false);
      }
      return super.updateLine(line, params);
      },
});
