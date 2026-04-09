/** @odoo-module */
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
    },
    
    async validateOrder(isForceValidate) {
        // 1. ABSOLIUTUS SAUGIKLIS: Jei varnelė nuimta, šis kodas nevykdomas!
        if (!this.pos.config.nsoft_enabled) {
            return super.validateOrder(...arguments);
        }

        const order = this.currentOrder;
        const sessionId = this.pos.session ? this.pos.session.id : (this.pos.pos_session ? this.pos.pos_session.id : null);
        
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

        try {
            const result = await this.orm.call("pos.order", "action_send_receipt_to_nsoft", [orderData]);
            if (result.success) {
                order.nsoft_receipt_id = result.receipt_id || "Registruota";
            }
        } catch (error) {
            console.error("nSoft klaida:", error);
        }

        // Įrašome ID į spausdinimo duomenis
        if (!order._nsoft_patched && typeof order.export_for_printing === 'function') {
            const originalExport = order.export_for_printing.bind(order);
            order.export_for_printing = (...args) => {
                const receipt = originalExport(...args);
                receipt.nsoft_receipt_id = order.nsoft_receipt_id;
                return receipt;
            };
            order._nsoft_patched = true;
        }

        return super.validateOrder(...arguments);
    }
});
