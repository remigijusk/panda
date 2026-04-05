/** @odoo-module */
import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { patch } from "@web/core/utils/patch";

patch(ReceiptScreen.prototype, {
    
    // Nustato, ar mygtukas matomas, ar paslėptas
    getKpoBtnStyle() {
        try {
            // 1. Tikriname nustatymą
            const config = this.pos?.config || this.env?.services?.pos?.config;
            if (!config || config.iface_print_kpo === false) {
                return "display: none;";
            }
            
            // 2. Tikriname, ar naudotas KPO mokėjimo būdas
            const order = this.props?.order || this.currentOrder || (this.pos && this.pos.get_order());
            if (!order) return "display: none;";
            
            const lines = typeof order.get_paymentlines === 'function' ? order.get_paymentlines() : (order.paymentlines || []);
            const hasKpo = lines.some(l => ((l.payment_method && l.payment_method.name) || l.name || '').toUpperCase().includes('KPO'));
            
            if (!hasKpo) {
                return "display: none;";
            }
            
            // Jei viskas tinka - grąžiname mygtuko dizainą (matomą)
            return "margin-top: 10px; background-color: #00A09D; color: white; border: none; padding: 15px; width: 100%; border-radius: 5px; font-weight: bold; font-size: 16px; cursor: pointer;";
        } catch (e) {
            console.error("KPO mygtuko stiliaus klaida:", e);
            return "display: none;"; // Saugiklis: jei klaida, paslepiame mygtuką ir leidžiame dirbti toliau
        }
    },

    // PDF spausdinimo funkcija
    async clickKpoBtn() {
        try {
            const order = this.props?.order || this.currentOrder || (this.pos && this.pos.get_order());
            if (!order) return alert("Sistemos klaida: nerastas užsakymas.");

            let backendId = order.backendId || order.id;
            let posRef = order.name || order.pos_reference;

            if (!backendId || typeof backendId !== 'number') {
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
                alert("Užsakymas dar išsaugomas serveryje. Palaukite kelias sekundes ir spauskite vėl.");
            }
        } catch (error) {
            console.error("KPO spausdinimo klaida:", error);
            alert("Įvyko sistemos klaida bandant spausdinti.");
        }
    }
});
