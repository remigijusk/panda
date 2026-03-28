/** @odoo-module */
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

patch(PaymentScreen.prototype, {
    async validateOrder(isForceValidate) {
        const order = this.currentOrder || this.pos.get_order();
        
        // Paimame tik prekes
        const lines = (order.lines || []).map(l => ({
            name: l.product_name || l.product?.display_name || "Prekė",
            qty: l.qty || 0,
            price: l.price_unit || 0,
            total: l.price_subtotal_incl || (l.qty * l.price_unit)
        }));

        const orderData = {
            lines: lines,
            name: order.name
        };

        try {
            const result = await this.env.services.orm.call(
                'pos.order',
                'action_send_receipt_to_nsoft',
                [orderData]
            );

            if (result && result.success) {
                order.nsoft_id = result.receipt_id;
                const original_json = order.export_as_JSON;
                order.export_as_JSON = function() {
                    const json = original_json.apply(this, arguments);
                    json.nsoft_id = this.nsoft_id;
                    return json;
                };
                return super.validateOrder(isForceValidate);
            } else {
                this.env.services.dialog.add(AlertDialog, {
                    title: "Fiskalizacijos klaida",
                    body: result.error || "Nepavyko užregistruoti i.EKA",
                });
                return false;
            }
        } catch (error) {
            this.env.services.dialog.add(AlertDialog, {
                title: "Ryšio klaida",
                body: "Nepavyko susisiekti su serveriu.",
            });
            return false;
        }
    }
});
