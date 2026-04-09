/** @odoo-module */
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.notification = useService("notification");
    },
    
    async validateOrder(isForceValidate) {
        const order = this.currentOrder;
        
        // Saugus ištraukimo įrankis (apsaugo nuo Odoo versijų skirtumų)
        const getVal = (obj, prop) => typeof obj[prop] === 'function' ? obj[prop]() : obj[prop];
        
        // Apsaugotas sesijos ID
        const sessionId = this.pos.session ? this.pos.session.id : (this.pos.pos_session ? this.pos.pos_session.id : null);
        
        // Apsaugotas sumų ir eilučių ištraukimas
        const trueTotal = getVal(order, 'get_total_with_tax') || order.amount_total || 0;
        const orderLines = getVal(order, 'get_orderlines') || order.lines || [];
        
        const linesData = orderLines.map(line => {
            const qty = getVal(line, 'get_quantity') || line.qty || 1;
            const price = getVal(line, 'get_unit_price') || line.price_unit || 0;
            const total = getVal(line, 'get_price_with_tax') || line.price_subtotal_incl || 0;
            
            let name = "Prekė";
            const product = getVal(line, 'get_product') || line.product;
            if (product) {
                name = product.display_name || product.name || "Prekė";
            }
            return { qty, price, total, name };
        });

        const orderData = {
            pos_session_id: sessionId,
            true_total: trueTotal,
            lines: linesData
        };

        try {
            const result = await this.orm.call(
                "pos.order",
                "action_send_receipt_to_nsoft",
                [[0], orderData]
            );

            if (result.ignored) {
                order.nsoft_receipt_id = false; 
            } else if (result.success) {
                order.nsoft_receipt_id = result.receipt_id || "Registruota";
            } else {
                this.notification.add(result.error || "Fiskalizacijos klaida", { type: "danger" });
                return false;
            }
        } catch (error) {
            this.notification.add("Ryšio klaida su serveriu", { type: "danger" });
            console.error("nSoft klaida:", error);
            return false;
        }

        // Saugus čekio papildymas
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
