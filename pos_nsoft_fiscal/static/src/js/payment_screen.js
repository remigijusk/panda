/** @odoo-module */
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, {
    async validateOrder(isForceValidate) {
        if (!this.pos.config.nsoft_enabled) {
            return super.validateOrder(...arguments);
        }

        const order = this.currentOrder;
        
        // Jokių gudravimų - tiesioginis Odoo komandų kvietimas
        const trueTotal = order.get_total_with_tax();
        const orderLines = order.get_orderlines();
        
        const linesData = orderLines.map(line => {
            const product = line.get_product();
            return {
                qty: line.get_quantity(),
                price: line.get_unit_price(),
                total: line.get_price_with_tax(),
                name: product ? (product.display_name || product.name) : "Prekė"
            };
        });

        const orderData = {
            config_id: this.pos.config.id,
            true_total: trueTotal,
            lines: linesData
        };

        try {
            const orm = this.env.services.orm;
            const result = await orm.call("pos.order", "action_send_receipt_to_nsoft", [orderData]);
            
            if (result && result.success) {
                order.nsoft_receipt_id = result.receipt_id;
                order.nsoft_error = false;
            } else {
                order.nsoft_receipt_id = false;
                order.nsoft_error = result ? result.error : "Nėra atsakymo iš Python serverio";
            }
        } catch (error) {
            order.nsoft_receipt_id = false;
            order.nsoft_error = "Sistemos klaida: " + error.message;
        }

        if (typeof order.export_for_printing === 'function' && !order._nsoft_patched) {
            const originalExport = order.export_for_printing.bind(order);
            order.export_for_printing = () => {
                const receipt = originalExport();
                receipt.nsoft_receipt_id = order.nsoft_receipt_id;
                receipt.nsoft_error = order.nsoft_error;
                return receipt;
            };
            order._nsoft_patched = true;
        }

        return super.validateOrder(...arguments);
    }
});
