/** @odoo-module */
import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { patch } from "@web/core/utils/patch";

patch(ReceiptScreen.prototype, {
    // Saugiai grąžiname tiesioginę nuorodą į PDF failą
    get kpoDownloadUrl() {
        try {
            const order = this.props?.order || this.currentOrder;
            if (!order) return false;

            // 1. Patikriname ar apmokėta per KPO
            const lines = typeof order.get_paymentlines === 'function' ? order.get_paymentlines() : (order.paymentlines || []);
            const hasKpo = lines.some(l => ((l.payment_method && l.payment_method.name) || l.name || '').toUpperCase().includes('KPO'));
            
            if (!hasKpo) return false; // Nėra KPO - nerodome nieko

            // 2. Ieškome užsakymo ID
            const backendId = order.backendId || order.id;
            
            if (backendId && typeof backendId === 'number') {
                // Turime ID - grąžiname tikslią PDF nuorodą
                return `/report/pdf/l10n_lt_kpo_kio.action_report_kpo_kio_pos/${backendId}`;
            }
            
            // Jei orderis KPO, bet dar neišsisaugojo serveryje
            return 'loading';

        } catch (e) {
            console.error("KPO nuorodos klaida:", e);
            return false;
        }
    }
});
