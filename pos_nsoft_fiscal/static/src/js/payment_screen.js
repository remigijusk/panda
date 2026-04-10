/** @odoo-module */
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, {
    async validateOrder(isForceValidate) {
        // 1. Saugiklis: jeigu nSoft išjungtas, tęsiame darbą standartiškai
        if (!this.pos.config.nsoft_enabled) {
            return super.validateOrder(...arguments);
        }

        const order = this.currentOrder;
        const sessionId = this.pos.session ? this.pos.session.id : (this.pos.pos_session ? this.pos.pos_session.id : null);
        
        // 2. Ištraukiame užsakymo duomenis
        const getVal = (obj, prop) => typeof obj[prop] === 'function' ? obj[prop]() : obj[prop];
        const trueTotal = getVal(order, 'get_total_with_tax') || order.amount_total || 0;
        const orderLines = getVal(order, 'get_orderlines') || order.lines || [];
        
        const linesData = orderLines.map(line => {
            const qty = getVal(line, 'get_quantity') || line.qty || 1;
            const price = getVal(line, 'get_unit_price') || line.price_unit || 0;
            const total = getVal(line, 'get_price_with_tax') || line.price_subtotal_incl || 0;
            let name = "Prekė";
            const product = getVal(line, 'get_product') || line.product;
            if (product) name = product.display_name || product.name || "Prekė";
            return { qty, price, total, name };
        });

        const orderData = {
            pos_session_id: sessionId,
            true_total: trueTotal,
            lines: linesData
        };

        // 3. Fone, prieš atspausdinant čekį, paprašome nSoft sugeneruoti ID
        try {
            const orm = this.env.services.orm;
            const result = await orm.call("pos.order", "action_send_receipt_to_nsoft", [orderData]);
            if (result && result.success) {
                order.nsoft_receipt_id = result.receipt_id;
            } else {
                order.nsoft_receipt_id = "Klaida: Nepavyko gauti ID";
            }
        } catch (error) {
            console.error("nSoft klaida:", error);
            order.nsoft_receipt_id = "Ryšio klaida";
        }

        // 4. Atiduodame gautą ID atspausdinimui į kvitą
        if (typeof order.export_for_printing === 'function' && !order.nsoft_patched) {
            const originalExport = order.export_for_printing.bind(order);
            order.export_for_printing = () => {
                const receipt = originalExport();
                receipt.nsoft_receipt_id = order.nsoft_receipt_id;
                return receipt;
            };
            order.nsoft_patched = true;
        }

        // Tęsiame Odoo darbą
        return super.validateOrder(...arguments);
    }
});
