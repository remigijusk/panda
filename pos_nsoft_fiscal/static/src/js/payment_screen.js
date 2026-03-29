/** @odoo-module */
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { Order } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

// 1. GLOBALUS KOSMETINIS KVITO PATAISYMAS
patch(Order.prototype, {
    export_for_printing() {
        const receipt = super.export_for_printing(...arguments);
        
        // Išvalome Odoo vertimų šiukšles viršuje
        if (receipt.name) {
            receipt.name = receipt.name.replace('PVM mok. kodas Bilietas', 'Kvitas').replace('Bilietas', 'Kvitas');
        }
        if (receipt.tracking_number && !String(receipt.tracking_number).includes('Užsakymo')) {
            receipt.tracking_number = 'Užsakymo nr. ' + receipt.tracking_number;
        }
        
        // GRIEŽTAI ištriname apatinius dubliuojamus rekvizitus (liks tik tavo graži Antraštė)
        if (receipt.company) {
            receipt.company.vat = false;
            receipt.company.company_registry = false;
            receipt.company.contact_address = false;
            receipt.company.phone = false;
            receipt.company.email = false;
            receipt.company.website = false;
        }
        
        return receipt;
    }
});

// 2. FISKALIZACIJOS LOGIKA
patch(PaymentScreen.prototype, {
    async validateOrder(isForceValidate) {
        const order = this.currentOrder || this.pos.get_order();
        
        const orderLines = order.get_orderlines ? order.get_orderlines() : order.lines || [];
        const lines = orderLines.map(line => ({
            name: line.get_product ? line.get_product().display_name : (line.product?.display_name || "Prekė"),
            qty: line.get_quantity ? line.get_quantity() : (line.qty || 0),
            price: line.get_unit_price ? line.get_unit_price() : (line.price_unit || 0),
            total: line.get_price_with_tax ? line.get_price_with_tax() : (line.price_subtotal_incl || 0)
        }));

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

                // Saugus i.EKA ID prikabinimas
                if (typeof order.export_for_printing === 'function' && !order.hasOwnProperty('export_for_printing_nsoft')) {
                    const original_print = order.export_for_printing.bind(order);
                    order.export_for_printing_nsoft = true;
                    order.export_for_printing = function() {
                        const rec = original_print();
                        rec.nsoft_id = this.nsoft_id;
                        return rec;
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
