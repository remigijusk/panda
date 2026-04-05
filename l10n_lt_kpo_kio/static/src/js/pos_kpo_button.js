/** @odoo-module */
import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { patch } from "@web/core/utils/patch";

patch(ReceiptScreen.prototype, {
    async downloadKPO() {
        const order = this.currentOrder;
        if (!order) return;

        // SAUGIKLIS: Ar šiam užsakymui buvo naudotas "KPO" mokėjimo būdas? (Odoo 17+ standartas)
        const paymentlines = order.get_paymentlines();
        const hasKPO = paymentlines.some(line => line.payment_method.name.toUpperCase().includes('KPO'));
        
        if (!hasKPO) {
            alert("Šiam užsakymui nebuvo naudotas KPO mokėjimo būdas, spausdinimas negalimas.");
            return;
        }

        // Patikriname, ar užsakymas jau išsiųstas į serverį
        if (!order.backendId) {
            alert("Užsakymas dar apdorojamas sistemoje. Prašome palaukti kelias sekundes ir bandyti vėl.");
            return;
        }

        // Atidarome sugeneruotą KPO PDF naujame lange
        const url = '/report/pdf/l10n_lt_kpo_kio.action_report_kpo_kio_pos/' + order.backendId;
        window.open(url, '_blank');
    }
});
