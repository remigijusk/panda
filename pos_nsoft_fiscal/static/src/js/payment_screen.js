/** @odoo-module */
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";

patch(PaymentScreen.prototype, {
    async validateOrder(isForceValidate) {
        // 1. Paimame krepšelio duomenis
        const order = this.pos.get_order();
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
                this.env.services.popup.add(ErrorPopup, {
                    title: "Fiskalizacijos klaida",
                    body: errorMessage,
                });
                return false; // Užblokuojame užsakymo patvirtinimą!
            }
        } catch (error) {
            // TINKLO KLAIDA: Dingo internetas tarp kasos ir serverio
            this.env.services.popup.add(ErrorPopup, {
                title: "Ryšio klaida (Offline)",
                body: "Nepavyko susisiekti su serveriu. Darbas be interneto yra draudžiamas.",
            });
            return false; // Užblokuojame užsakymo patvirtinimą!
        }
    }
});
