/** @odoo-module */
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

patch(PaymentScreen.prototype, {
    async validateOrder(isForceValidate) {
        const order = this.currentOrder || this.pos.get_order();
        
        // 1. DUOMENŲ SURINKIMAS (Odoo 19 tiesioginis būdas)
        // Odoo 19 naudoja tiesiog .lines, .qty, .price_unit ir t.t.
        const raw_lines = order.lines || [];
        const lines = raw_lines.map(l => [0, 0, {
            full_product_name: l.product_name || l.product?.display_name || "Prekė",
            qty: l.qty || 0,
            price_unit: l.price_unit || 0,
            price_subtotal_incl: l.price_subtotal_incl || 0,
        }]);

        const orderData = {
            lines: lines,
            amount_total: order.amount_total || 0,
            name: order.name
        };

        try {
            // 2. Kreipiamės į Python variklį
            const result = await this.env.services.orm.call(
                'pos.order',
                'action_send_receipt_to_nsoft',
                [orderData]
            );

            if (result && result.success) {
                // Išsaugome ID atmintyje
                order.nsoft_id = result.receipt_id;
                
                // Prikabiname ID prie galutinio JSON siuntimo
                const original_json = order.export_as_JSON;
                order.export_as_JSON = function() {
                    const json = original_json.apply(this, arguments);
                    json.nsoft_id = this.nsoft_id;
                    return json;
                };

                // Viskas gerai, tęsiame
                return super.validateOrder(isForceValidate);
            } else {
                this.env.services.dialog.add(AlertDialog, {
                    title: "Fiskalizacijos klaida",
                    body: result.error || "Nepavyko užregistruoti i.EKA",
                });
                return false;
            }
        } catch (error) {
            console.error("nSoft modulis pagavo klaidą:", error);
            this.env.services.dialog.add(AlertDialog, {
                title: "Sistemos klaida",
                body: "Įvyko klaida apdorojant kvitą. Patikrinkite naršyklės konsolę.",
            });
            return false;
        }
    }
});
