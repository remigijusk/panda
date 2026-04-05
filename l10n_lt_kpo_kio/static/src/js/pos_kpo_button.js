/** @odoo-module */
import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { patch } from "@web/core/utils/patch";
import { onMounted } from "@odoo/owl";

patch(ReceiptScreen.prototype, {
    setup() {
        super.setup(...arguments);
        
        // Šis kodas įvykdomas automatiškai, kai atidaromas Čekio/Sąskaitos langas
        onMounted(() => {
            try {
                const pos = this.pos || (this.env && this.env.services && this.env.services.pos);
                if (!pos) return;
                
                const order = pos.get_order();
                if (!order || !order.backendId) return;

                // Apsauga: jei KPO jau atspausdintas šiam užsakymui, antro neatidarinėjame (pvz., jei F5)
                if (order.kpo_auto_printed) return;

                // Patikriname, ar apmokėta per KPO
                const lines = typeof order.get_paymentlines === 'function' ? order.get_paymentlines() : (order.paymentlines || []);
                const hasKPO = lines.some(line => 
                    line.payment_method && 
                    line.payment_method.name && 
                    line.payment_method.name.toUpperCase().includes('KPO')
                );

                // Jei naudotas KPO – automatiškai iššoka PDF langas naujame skirtuke
                if (hasKPO) {
                    order.kpo_auto_printed = true; // Pažymime, kad jau atidarėme
                    const url = '/report/pdf/l10n_lt_kpo_kio.action_report_kpo_kio_pos/' + order.backendId;
                    window.open(url, '_blank');
                }
            } catch (error) {
                console.error("KPO automatinio spausdinimo klaida:", error);
            }
        });
    }
});
