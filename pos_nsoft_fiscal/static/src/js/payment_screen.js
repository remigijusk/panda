/** @odoo-module */
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

patch(PaymentScreen.prototype, {
    async validateOrder(isForceValidate) {
        // 1. Paimame krepšelio duomenis (Odoo 19 formatu)
        const order = this.currentOrder || this.pos.get_order();
        const orderData = order.export_as_JSON();

        try {
            // 2. Siunčiame duomenis į mūsų Python funkciją serveryje
            const result = await this.env.services.orm.call(
                'pos.order',
                'action_send_receipt_to_nsoft',
                [orderData]
            );

            // 3. Tikriname atsakymą iš nSoft (i.EKA)
            if (result && result.success) {
                // SĖKMĖ: Leidžiame Odoo tęsti darbą ir atspausdinti kvitą
                return super.validateOrder(isForceValidate);
            } else {
                // KLAIDA: nSoft atmetė kvitą (pvz. blogas PVM, nerastas ID ir pan.)
                const errorMessage = result && result.error ? result.error : "Nežinoma klaida iš i.EKA.";
                this.env.services.dialog.add(AlertDialog, {
                    title: "Fiskalizacijos klaida",
                    body: errorMessage,
                });
                return false; // Užblokuojame užsakymo patvirtinimą!
            }
        } catch (error) {
            // TINKLO KLAIDA: Dingo internetas tarp kasos ir serverio
            this.env.services.dialog.add(AlertDialog, {
                title: "Ryšio klaida (Offline)",
                body: "Nepavyko susisiekti su serveriu. Darbas be interneto yra draudžiamas.",
            });
            return false; // Užblokuojame užsakymo patvirtinimą!
        }
    }
});
