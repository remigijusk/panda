/** @odoo-module */
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, {
    async validateOrder(isForceValidate) {
        const order = this.currentOrder;
        
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

        // PERDUODAME TIK KASOS ID. Python pats susiras slaptažodį DB!
        const orderData = {
            config_id: this.pos.config.id,
            true_total: trueTotal,
            lines: linesData
        };

        try {
            const orm = this.env.services.orm;
            const result = await orm.call("pos.order", "action_send_receipt_to_nsoft", [orderData]);
            
            if (result && result.success && result.receipt_id) {
                order.nsoft_receipt_id = result.receipt_id;
            } else {
                console.log("nSoft ignoravo arba atmetė:", result);
            }
        } catch (error) {
            console.error("Klaida bendraujant su Python:", error);
        }

        // Įskiepijame gautą ID į kvitą
        if (typeof order.export_for_printing === 'function' && !order._nsoft_patched) {
            const originalExport = order.export_for_printing.bind(order);
            order.export_for_printing = () => {
                const receipt = originalExport();
                receipt.nsoft_receipt_id = order.nsoft_receipt_id || false;
                return receipt;
            };
            order._nsoft_patched = true;
        }

        return super.validateOrder(...arguments);
    }
});
