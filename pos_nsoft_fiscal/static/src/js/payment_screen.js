/** @odoo-module */
/**
 * nSoft fiscalization - frontend patch (Odoo 19)
 *
 * Extends PosOrder model to include nsoft fields in export_for_printing.
 * Backend saves nsoft_receipt_id via _process_order.
 * _loader_params_pos_order loads the field into POS client.
 */

import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    //@override
    export_for_printing(baseUrl, headerData) {
        const result = super.export_for_printing(baseUrl, headerData);
        result.nsoft_receipt_id = this.nsoft_receipt_id || false;
        result.nsoft_error = this.nsoft_error || false;
        return result;
    },
});
