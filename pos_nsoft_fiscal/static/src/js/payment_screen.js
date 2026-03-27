/** @odoo-module */
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

patch(PaymentScreen.prototype, {
    async validateOrder(isForceValidate) {
        const order = this.currentOrder || this.pos.get_order();
        
        // 1. UNIVERSALUS DUOMENŲ IŠTRAUKĖJAS (Nebebijome Odoo 19 pokyčių)
        let orderData = null;
        if (typeof order.export_as_JSON === 'function') orderData = order.export_as_JSON();
        else if (typeof order.serialize === 'function') orderData = order.serialize();
        else if (typeof order.exportAsJSON === 'function') orderData = order.exportAsJSON();
        else if (typeof order.toJson === 'function') orderData = order.toJson();
        
        // Jei Odoo nerado jokių funkcijų, patys surenkame prekes ir mokėjimus:
        if (!orderData) {
            const lines = typeof order.get_orderlines === 'function' ? order.get_orderlines() : (order.lines || []);
            const payments = typeof order.get_paymentlines === 'function' ? order.get_paymentlines() : (order.paymentlines || []);
            
            orderData = {
                lines: lines.map(l => [0, 0, {
                    full_product_name: l.full_product_name || (l.get_full_product_name && l.get_full_product_name()) || (l.product && l.product.display_name) || 'Prekė',
                    qty: l.qty !== undefined ? l.qty : (l.get_quantity && l.get_quantity()) || 1,
                    price_unit: l.price !== undefined ? l.price : (l.get_unit_price && l.get_unit_price()) || 0,
                    price_subtotal_incl: l.price_subtotal_incl !== undefined ? l.price_subtotal_incl : (l.get_price_with_tax && l.get_price_with_tax()) || 0,
                    tax_ids: l.tax_ids || []
                }]),
                statement_ids: payments.map(p => [0, 0, {
                    amount: p.amount !== undefined ? p.amount : (p.get_amount && p.get_amount()) || 0
                }])
            };
        }

        try {
            // 2. Siunčiame surinktus duomenis į Python variklį
            const result = await this.env.services.orm.call(
                'pos.order',
                'action_send_receipt_to_nsoft',
                [orderData]
            );

            // 3. Tikriname atsakymą iš i.EKA
            if (result && result.success) {
                // SĖKMĖ: Leidžiame Odoo tęsti darbą ir atspausdinti kvitą
                return super.validateOrder(isForceValidate);
            } else {
                // KLAIDA: nSoft atmetė kvitą
                const errorMessage = result && result.error ? result.error : "Nežinoma klaida iš i.EKA.";
                this.env.services.dialog.add(AlertDialog, {
                    title: "Fiskalizacijos klaida",
                    body: errorMessage,
                });
                return false; // Užblokuojame užsakymą!
            }
        } catch (error) {
            // TINKLO KLAIDA: Dingęs internetas
            this.env.services.dialog.add(AlertDialog, {
                title: "Ryšio klaida (Offline)",
                body: "Nepavyko susisiekti su serveriu. Darbas be interneto yra draudžiamas.",
            });
            return false; // Užblokuojame užsakymą!
        }
    }
});
