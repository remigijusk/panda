/** @odoo-module */
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Order } from "@point_of_sale/app/store/models";

// Patch'iname Order modelį, kad jis mokėtų saugoti nsoft_id
patch(Order.prototype, {
    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        json.nsoft_id = this.nsoft_id || null;
        return json;
    },
});

patch(PaymentScreen.prototype, {
    async validateOrder(isForceValidate) {
        const order = this.currentOrder || this.pos.get_order();
        
        // Surenkame duomenis siuntimui
        const orderData = {
            lines: order.get_orderlines().map(l => [0, 0, {
                full_product_name: l.product.display_name,
                qty: l.get_quantity(),
                price_unit: l.get_unit_price(),
                price_subtotal_incl: l.get_price_with_tax(),
            }]),
            amount_total: order.get_total_with_tax()
        };

        try {
            const result = await this.env.services.orm.call(
                'pos.order',
                'action_send_receipt_to_nsoft',
                [orderData]
            );

            if (result && result.success) {
                // Įrašome gautą ID į krepšelį
                order.nsoft_id = result.receipt_id;
                // Patvirtiname užsakymą Odoo sistemoje
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
                body: "Serveris nepasiekiamas. Patikrinkite internetą.",
            });
            return false;
        }
    }
});
