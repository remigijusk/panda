/** @odoo-module */
import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { patch } from "@web/core/utils/patch";

patch(ReceiptScreen.prototype, {
    async downloadKpoPdf() {
        try {
            const order = this.currentOrder || this.props.order;
            if (!order) {
                return alert("Nerastas užsakymas.");
            }

            // 1. Patikriname ar apmokėta per KPO
            const lines = typeof order.get_paymentlines === 'function' ? order.get_paymentlines() : (order.paymentlines || []);
            const hasKPO = lines.some(line => 
                line.payment_method && 
                line.payment_method.name && 
                line.payment_method.name.toUpperCase().includes('KPO')
            );

            if (!hasKPO) {
                return alert("Šiam užsakymui nebuvo naudotas KPO mokėjimo būdas.");
            }

            // 2. Gauname užsakymo ID iš duomenų bazės
            let backendId = order.backendId || order.id;

            if (!backendId || typeof backendId !== 'number') {
                const posReference = order.name;
                const result = await this.env.services.orm.search('pos.order', [['pos_reference', '=', posReference]], { limit: 1 });
                
                if (result && result.length > 0) {
                    backendId = result[0];
                } else {
                    return alert("Užsakymas dar išsaugomas. Palaukite 2 sekundes ir paspauskite vėl.");
                }
            }

            // 3. Atidarome PDF. Kadangi tai daroma iškart po fizinio pelės paspaudimo, naršyklė jo NEBLOKUOS.
            const url = '/report/pdf/l10n_lt_kpo_kio.action_report_kpo_kio_pos/' + backendId;
            window.open(url, '_blank');

        } catch (error) {
            console.error("Klaida spausdinant KPO:", error);
            alert("Sistemos klaida. KPO atspausdinti nepavyko.");
        }
    }
});
