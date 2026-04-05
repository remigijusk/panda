/** @odoo-module */
import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { patch } from "@web/core/utils/patch";
import { onMounted } from "@odoo/owl";

patch(ReceiptScreen.prototype, {
    setup() {
        super.setup(...arguments);
        onMounted(() => { this.tryDownloadKPO(); });
    },
    async tryDownloadKPO() {
        try {
            const order = this.currentOrder;
            if (!order || order.kpo_auto_printed) return;
            const lines = typeof order.get_paymentlines === 'function' ? order.get_paymentlines() : (order.paymentlines || []);
            const hasKPO = lines.some(line => line.payment_method && line.payment_method.name && line.payment_method.name.toUpperCase().includes('KPO'));
            if (hasKPO) {
                let attempts = 0;
                const checkInterval = setInterval(() => {
                    if (order.backendId) {
                        clearInterval(checkInterval);
                        order.kpo_auto_printed = true;
                        const url = '/report/pdf/l10n_lt_kpo_kio.action_report_kpo_kio_pos/' + order.backendId;
                        const newWindow = window.open(url, '_blank');
                        if (!newWindow) { alert("DĖMESIO: Naršyklė užblokavo KPO langą. Prašome leisti iššokančius langus (Pop-ups) šiam adresui."); }
                    }
                    attempts++;
                    if (attempts > 60) clearInterval(checkInterval);
                }, 100);
            }
        } catch (e) { console.error("KPO klaida:", e); }
    }
});
