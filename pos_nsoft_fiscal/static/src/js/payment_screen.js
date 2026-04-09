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
        
        const orderData = {
            pos_session_id: this.pos.pos_session.id,
            true_total: order.get_total_with_tax(),
            lines: order.get_orderlines().map(line => ({
                qty: line.get_quantity(),
                price: line.get_unit_price(),
                total: line.get_price_with_tax(),
                name: line.get_product().display_name
            }))
        };

        try {
            const result = await this.orm.call(
                "pos.order",
                "action_send_receipt_to_nsoft",
                [[0], orderData]
            );

            // Priskiriame ID prie užsakymo, atsižvelgiant į tai, ar nSoft įjungtas
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
            console.error(error);
            return false;
        }

        // 100% SAUGUS BŪDAS ĮTERPTI DUOMENIS Į ČEKĮ (Be jokių pavojingų importų)
        if (!order._nsoft_patched && typeof order.export_for_printing === 'function') {
            const originalExport = order.export_for_printing.bind(order);
            order.export_for_printing = (...args) => {
                const receipt = originalExport(...args);
                // Įklijuojame nSoft ID į spausdinimo duomenis
                receipt.nsoft_receipt_id = order.nsoft_receipt_id;
                return receipt;
            };
            order._nsoft_patched = true;
        }

        // Tęsiame Odoo pardavimą
        return super.validateOrder(...arguments);
    }
});
