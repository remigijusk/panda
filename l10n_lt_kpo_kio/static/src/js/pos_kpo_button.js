/** @odoo-module */
import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { patch } from "@web/core/utils/patch";

patch(ReceiptScreen.prototype, {
    
    // Šis metodas nusprendžia, ar rodyti mygtuką (susietas su this.isKpoReady XML faile)
    get isKpoReady() {
        try {
            // 1. Tikriname, ar įjungta varnelė nustatymuose
            const pos = this.pos || this.env?.services?.pos;
            if (!pos || !pos.config || !pos.config.iface_print_kpo) {
                return false; 
            }

            // 2. Tikriname, ar naudotas KPO mokėjimo būdas
            const order = this.currentOrder || this.props?.order || pos.get_order();
            if (!order) return false;

            const lines = typeof order.get_paymentlines === 'function' ? order.get_paymentlines() : (order.paymentlines || []);
            return lines.some(l => ((l.payment_method && l.payment_method.name) || l.name || '').toUpperCase().includes('KPO'));
        } catch (e) {
            console.error(e);
            return false;
        }
    },

    // PDF atidarymo komanda paspaudus mygtuką
    async printKpoPdf() {
        try {
            const order = this.currentOrder || this.props?.order || (this.env?.services?.pos && this.env.services.pos.get_order());
            if (!order) return alert("Nerastas užsakymas.");

            let backendId = order.backendId || order.id;
            
            // Jei nėra ID, gauname jį tiesiai iš serverio pagal čekio numerį
            if (!backendId || typeof backendId !== 'number') {
                let posRef = order.name || order.pos_reference;
                if (posRef) {
                    const res = await this.env.services.orm.search('pos.order', [['pos_reference', '=', posRef]], { limit: 1 });
                    if (res && res.length > 0) {
                        backendId = res[0];
                    }
                }
            }

            if (backendId && typeof backendId === 'number') {
                window.open(`/report/pdf/l10n_lt_kpo_kio.action_report_kpo_kio_pos/${backendId}`, '_blank');
            } else {
                alert("Užsakymas dar išsaugomas. Bandykite dar kartą po 2 sekundžių.");
            }
        } catch (error) {
            console.error("Spausdinimo klaida:", error);
            alert("Klaida spausdinant KPO.");
        }
    }
});
