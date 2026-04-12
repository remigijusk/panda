/** @odoo-module */
/**
 * nSoft fiscalization - frontend patch (Odoo 19 OWL)
 *
 * The backend already saves nsoft_receipt_id to pos.order via _process_order.
 * _loader_params_pos_order loads this field into the POS client.
 * This patch injects nsoft fields into the receipt props so the template can render them.
 */

import { patch } from "@web/core/utils/patch";
import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";

patch(ReceiptScreen.prototype, {
    get orderUiState() {
        const state = super.orderUiState;
        return state;
    },

    get receiptData() {
        const data = super.receiptData || {};
        const order = this.currentOrder;
        if (order) {
            data.nsoft_receipt_id = order.nsoft_receipt_id || false;
            data.nsoft_error = order.nsoft_error || false;
        }
        return data;
    },
});
