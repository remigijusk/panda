/** @odoo-module */
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, {
    async validateOrder(isForceValidate) {
        if (!this.pos.config.nsoft_enabled) {
            return super.validateOrder(...arguments);
        }

        const order = this.currentOrder;
        this.pos.last_nsoft_receipt_id = null; // Išvalome seną ID
        
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

        // TOBULAS DUOMENŲ PAKETAS: Pridedame nSoft nustatymus, kad Python nereikėtų jų ieškoti
        const orderData = {
            api_url: this.pos.config.nsoft_api_url,
            pos_id: this.pos.config.nsoft_pos_id,
            token: this.pos.config.nsoft_token,
            true_total: trueTotal,
            lines: linesData
        };

        try {
            const orm = this.env.services.orm;
            const result = await orm.call("pos.order", "action_send_receipt_to_nsoft", [orderData]);
            
            if (result && result.success) {
                this.pos.last_nsoft_receipt_id = result.receipt_id;
            } else {
                console.error("nSoft serverio klaida:", result ? result.error : "Nėra atsakymo");
            }
        } catch (error) {
            console.error("Klaida susisiekiant su Python:", error);
        }

        return super.validateOrder(...arguments);
    }
});
