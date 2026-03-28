/** @odoo-module */
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

patch(PaymentScreen.prototype, {
    async validateOrder(isForceValidate) {
        const order = this.currentOrder || this.pos.get_order();
        
        // 1. DUOMENŲ SURINKIMAS (Odoo 19 "Deep Dive")
        const raw_lines = order.lines || [];
        const lines = raw_lines.map(l => {
            // Bandome ištraukti kainą ir kiekį visais įmanomais Odoo būdais
            const qty = typeof l.get_quantity === 'function' ? l.get_quantity() : (l.qty || 0);
            const price = typeof l.get_unit_price === 'function' ? l.get_unit_price() : (l.price_unit || 0);
            const totalWithTax = typeof l.get_price_with_tax === 'function' ? l.get_price_with_tax() : (l.price_subtotal_incl || (qty * price));

            return [0, 0, {
                full_product_name: l.product_name || l.product?.display_name || "Prekė",
                qty: qty,
                price_unit: price,
                price_subtotal_incl: totalWithTax,
            }];
        });

        const orderData = {
            lines: lines,
            amount_total: typeof order.get_total_with_tax === 'function' ? order.get_total_with_tax() : (order.amount_total || 0),
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
                
                // Išsaugojimo logika
                const original_json = order.export_as_JSON;
                order.export_as_JSON = function() {
                    const json = original_json.apply(this, arguments);
                    json.nsoft_id = this.nsoft_id;
                    return json;
                };

                return super.validateOrder(isForceValidate);
            } else {
                // Jei nSoft atmetė (kaip jūsų nuotraukoje), parodome jų lietuvišką pranešimą
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
