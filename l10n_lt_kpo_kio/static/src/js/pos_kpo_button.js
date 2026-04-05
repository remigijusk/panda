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

    autoPrintKPO() {
        try {
            // Skaitome TIKRĄJĮ ką tik užbaigtą užsakymą iš kvito ekrano savybių!
            const order = this.props.order || this.currentOrder;
            
            if (!order || order.kpo_auto_printed) return;

            const lines = typeof order.get_paymentlines === 'function' ? order.get_paymentlines() : (order.paymentlines || []);
            const hasKPO = lines.some(line => 
                line.payment_method && 
                line.payment_method.name && 
                line.payment_method.name.toUpperCase().includes('KPO')
            );

            if (hasKPO) {
                let attempts = 0;
                const checkInterval = setInterval(() => {
                    // Užbaigtas užsakymas gauna backendId, kai pasiekia serverį
                    const backendId = order.backendId || order.id;
                    
                    // Tikriname ar gavome realų ID (skaičių) iš serverio
                    if (backendId && typeof backendId === 'number') {
                        clearInterval(checkInterval);
                        order.kpo_auto_printed = true;
                        
                        const url = '/report/pdf/l10n_lt_kpo_kio.action_report_kpo_kio_pos/' + backendId;
                        
                        // Atidarome PDF
                        const newWindow = window.open(url, '_blank');
                        
                        // Patikriname ar naršyklė neužblokavo "Iššokančio lango" (Pop-up)
                        if (!newWindow || newWindow.closed || typeof newWindow.closed == 'undefined') {
                            alert("DĖMESIO: Jūsų naršyklė UŽBLOKAVO automatinį KPO langą! Prašome adreso juostos dešinėje pusėje paspausti ant raudono ženkliuko ir pasirinkti 'Visada leisti iššokančius langus'.");
                        }
                    }
                    
                    attempts++;
                    if (attempts > 50) {
                        clearInterval(checkInterval); // Nutraukiame paiešką po 10 sekundžių, jei nėra interneto
                    }
                }, 200); // Tikriname kas 0.2 sekundės
            }
        } catch (error) {
            console.error("KPO spausdinimo klaida:", error);
        }
    }
});
