/** @odoo-module */
import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { patch } from "@web/core/utils/patch";
import { onMounted } from "@odoo/owl";

patch(ReceiptScreen.prototype, {
    setup() {
        super.setup(...arguments);
        
        onMounted(() => {
            this.autoPrintKPO();
        });
    },

    async autoPrintKPO() {
        try {
            // Paimame užsakymo duomenis
            const order = this.props.order || this.currentOrder;
            if (!order || order.kpo_auto_printed) return;

            // Labai patikimas būdas patikrinti, ar naudotas KPO
            let hasKPO = false;
            const receiptData = typeof order.export_for_printing === 'function' ? order.export_for_printing() : null;
            
            if (receiptData && receiptData.paymentlines) {
                hasKPO = receiptData.paymentlines.some(p => (p.name || '').toUpperCase().includes('KPO'));
            } else if (order.paymentlines) {
                hasKPO = order.paymentlines.some(p => {
                    const name = (p.payment_method && p.payment_method.name) || p.name || '';
                    return name.toUpperCase().includes('KPO');
                });
            }

            if (!hasKPO) return;

            order.kpo_auto_printed = true; // Pažymime, kad procesas prasidėjo
            const posReference = order.name; // Čekio numeris, kurio ieškosime serveryje
            
            // Ciklas, kuris klausia serverio, ar užsakymas jau išsaugotas
            let attempts = 0;
            const checkInterval = setInterval(async () => {
                attempts++;
                try {
                    // Kreipiamės TIESIAI į Odoo duomenų bazę ieškodami šio čekio
                    const result = await this.env.services.orm.search('pos.order', [['pos_reference', '=', posReference]], { limit: 1 });
                    
                    // Jei serveris rado užsakymą ir grąžino jo ID
                    if (result && result.length > 0) {
                        clearInterval(checkInterval);
                        const backendId = result[0]; // Tikrasis duomenų bazės ID
                        
                        const url = '/report/pdf/l10n_lt_kpo_kio.action_report_kpo_kio_pos/' + backendId;
                        const newWindow = window.open(url, '_blank');
                        
                        // Jei langas neatsidarė dėl naršyklės blokavimo
                        if (!newWindow || newWindow.closed || typeof newWindow.closed == 'undefined') {
                            alert("DĖMESIO! Naršyklė užblokavo KPO PDF langą. Adreso juostos dešinėje pusėje paspauskite ant raudono ženkliuko ir pasirinkite 'Visada leisti iššokančius langus'.");
                        }
                    } else if (attempts > 10) { 
                        // Po 10 sekundžių nustojame ieškoti
                        clearInterval(checkInterval);
                    }
                } catch (rpcError) {
                    // Ignoruojame laikinas ryšio klaidas ir bandome toliau
                }
            }, 1000); // Klausiame serverio kas 1 sekundę

        } catch (error) {
            console.error("KPO spausdinimo procesas nutrūko:", error);
        }
    }
});
