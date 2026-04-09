/** @odoo-module */
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { Order } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

// Pridedame mūsų kintamąjį į kvito spausdinimo duomenis
patch(Order.prototype, {
    export_for_printing() {
        const receipt = super.export_for_printing(...arguments);
        receipt.nsoft_receipt_id = this.nsoft_receipt_id;
        return receipt;
    }
});

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

            // Jeigu Python kodas pasakė IGNORED (varnelė nuimta)
            if (result.ignored) {
                order.nsoft_receipt_id = false; // Nepaliekame jokio pėdsako!
            } 
            // Jeigu suveikė sėkmingai
            else if (result.success) {
                order.nsoft_receipt_id = result.receipt_id || "Registruota";
            } 
            // Jei atmetė nSoft serveris
            else {
                this.notification.add(result.error || "Fiskalizacijos klaida", { type: "danger" });
                return false;
            }
        } catch (error) {
            this.notification.add("Ryšio klaida su serveriu", { type: "danger" });
            console.error(error);
            return false;
        }

        // Tęsiame Odoo pardavimą
        return super.validateOrder(...arguments);
    }
});
