/** @odoo-module */
/**
 * nSoft fiscalization - frontend patch (Odoo 19 OWL)
 *
 * ALL fiscalization logic has been moved to the Python backend
 * (pos.order._process_order). This thin patch only ensures that
 * nsoft_receipt_id and nsoft_error, which are already loaded from
 * the database into the POS order object via _loader_params_pos_order,
 * are forwarded into the receipt template data object so OWL can render them.
 */

import { Order } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";

patch(Order.prototype, {
        export_for_printing() {
                    const result = super.export_for_printing(...arguments);
                    result.nsoft_receipt_id = this.nsoft_receipt_id || false;
                    result.nsoft_error = this.nsoft_error || false;
                    return result;
        },
});
