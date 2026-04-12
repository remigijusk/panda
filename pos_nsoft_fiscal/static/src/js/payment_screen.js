/** @odoo-module */
/**
 * nSoft fiscalization - frontend patch (Odoo 19 OWL)
 *
 * Patches Order.export_for_printing() to forward nsoft_receipt_id
 * and nsoft_error fields (already loaded from DB via _loader_params_pos_order)
 * into the receipt template data so OWL can render them.
 */

import { patch } from "@web/core/utils/patch";
import { PosOrder } from "@point_of_sale/app/models/pos_order";

patch(PosOrder.prototype, {
    export_for_printing() {
        const result = super.export_for_printing(...arguments);
        result.nsoft_receipt_id = this.nsoft_receipt_id || false;
        result.nsoft_error = this.nsoft_error || false;
        return result;
    },
});
