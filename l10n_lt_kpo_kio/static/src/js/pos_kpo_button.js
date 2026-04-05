/** @odoo-module */
import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { patch } from "@web/core/utils/patch";

patch(ReceiptScreen.prototype, {
    // Saugus metodas konfigūracijos nuskaitymui
    getKpoEnabled() {
        try {
            const pos = this.pos || (this.env && this.env.services && this.env.services.pos);
            return pos && pos.config && pos.config.iface_print_kpo;
        } catch (e) {
            console.error("KPO Mygtuko klaida:", e);
            return false;
        }
    },

    async downloadKPO() {
        try {
            const pos = this.pos || (this.env && this.env.services && this.env.services.pos);
            const order = pos.get_order(); // Odoo 19 standartas
            
            if (!order) {
                alert("Nerastas užsakymas.");
                return;
            }

            // Odoo 19 mokėjimų eilučių nuskaitymas (apsauga nuo versijų skirtumų)
            const lines = typeof order.get_paymentlines === 'function' ? order.get_paymentlines() : (order.paymentlines || []);
            
            const hasKPO = lines.some(line => 
                line.payment_method && 
                line.payment_method.name && 
                line.payment_method.name.toUpperCase().includes('KPO')
            );
            
            if (!hasKPO) {
                alert("Šiam užsakymui nebuvo naudotas KPO mokėjimo būdas, spausdinimas negalimas.");
                return;
            }

            const backendId = order.backendId || order.id;
            if (!backendId) {
                alert("Užsakymas dar apdorojamas sistemoje. Prašome palaukti kelias sekundes ir bandyti vėl.");
                return;
            }

            const url = '/report/pdf/l10n_lt_kpo_kio.action_report_kpo_kio_pos/' + backendId;
            window.open(url, '_blank');
        } catch (error) {
            console.error("Klaida spausdinant KPO:", error);
            alert("Nepavyko atspausdinti KPO.");
        }
    }
});
