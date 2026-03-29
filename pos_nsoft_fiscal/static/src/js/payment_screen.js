/** @odoo-module */
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

patch(PaymentScreen.prototype, {
    async validateOrder(isForceValidate) {
        const order = this.currentOrder || this.pos.get_order();
        
        // Saugiai surenkame prekes
        const orderLines = order.get_orderlines ? order.get_orderlines() : order.lines || [];
        const lines = orderLines.map(line => ({
            name: line.get_product ? line.get_product().display_name : (line.product?.display_name || "Prekė"),
            qty: line.get_quantity ? line.get_quantity() : (line.qty || 0),
            price: line.get_unit_price ? line.get_unit_price() : (line.price_unit || 0),
            total: line.get_price_with_tax ? line.get_price_with_tax() : (line.price_subtotal_incl || 0)
        }));

        // Paimame TIKRĄJĄ sumą (su jau įskaičiuotais apvalinimais)
        const trueTotal = order.get_total_with_tax ? order.get_total_with_tax() : (order.amount_total || 0);

        const orderData = {
            lines: lines,
            name: order.name,
            true_total: trueTotal
        };

        try {
            const result = await this.env.services.orm.call(
                'pos.order',
                'action_send_receipt_to_nsoft',
                [orderData]
            );

            if (result && result.success) {
                order.nsoft_id = result.receipt_id;
                
                if (typeof order.export_as_JSON === 'function') {
                    const original_json = order.export_as_JSON.bind(order);
                    order.export_as_JSON = function() {
                        const json = original_json();
                        json.nsoft_id = this.nsoft_id;
                        return json;
                    };
                }

                if (typeof order.export_for_printing === 'function') {
                    const original_print = order.export_for_printing.bind(order);
                    order.export_for_printing = function() {
                        const receipt = original_print();
                        receipt.nsoft_id = this.nsoft_id;
                        return receipt;
                    };
                }

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
