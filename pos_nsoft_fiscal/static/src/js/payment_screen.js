/** @odoo-module */
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

patch(PaymentScreen.prototype, {
    async validateOrder(isForceValidate) {
        const order = this.currentOrder || this.pos.get_order();
        
        // Surenkame duomenis (Universalus būdas)
        const lines = order.get_orderlines().map(l => [0, 0, {
            full_product_name: l.product.display_name,
            qty: l.get_quantity(),
            price_unit: l.get_unit_price(),
            price_subtotal_incl: l.get_price_with_tax(),
        }]);

        const orderData = {
            lines: lines,
            amount_total: order.get_total_with_tax(),
            name: order.name
        };

        try {
            // 1. Siunčiame į serverį/nSoft
            const result = await this.env.services.orm.call(
                'pos.order',
                'action_send_receipt_to_nsoft',
                [orderData]
            );

            if (result && result.success) {
                // 2. IŠSAUGOME ID: Šis žingsnis dabar gudresnis. 
                // Mes tiesiog prikabiname ID prie užsakymo, kad Odoo jį nusiųstų automatiškai.
                order.nsoft_id = result.receipt_id;
                
                // Priverčiame Odoo įtraukti šį ID į galutinį siuntimą
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
                body: "Nepavyko susisiekti su Odoo serveriu.",
            });
            return false;
        }
    }
});
