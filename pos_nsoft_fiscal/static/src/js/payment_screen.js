/** @odoo-module */
/**
 * nSoft fiscalization - frontend patch (Odoo 19 OWL)
 *
 * Backend saves nsoft_receipt_id to pos.order via _process_order.
 * _loader_params_pos_order loads this field into POS client.
 *
 * In Odoo 19, OrderReceipt template receives props.data from ReceiptScreen.
 * We patch ReceiptScreen to inject nsoft fields into the receipt data.
 */

import { patch } from "@web/core/utils/patch";
import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";

patch(ReceiptScreen.prototype, {
    get nextScreen() {
        return super.nextScreen;
    },

    get receiptData() {
        const data = super.receiptData;
        try {
            const order = this.currentOrder;
            if (order && data) {
                data.nsoft_receipt_id = order.nsoft_receipt_id || false;
                data.nsoft_error = order.nsoft_error || false;
            }
        } catch (e) {
            // Silent fail - do not break receipt if patching fails
        }
        return data;
    },
});
