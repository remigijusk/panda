/** @odoo-module */
import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { patch } from "@web/core/utils/patch";
import { onMounted } from "@odoo/owl";

patch(ReceiptScreen.prototype, {
    setup() {
        if (super.setup) {
            super.setup(...arguments);
        }
        
        onMounted(() => {
            setTimeout(() => {
                const btn = document.getElementById('kpo_magic_btn');
                if (btn) {
                    this.initKpoButton(btn);
                }
            }, 300);
        });
    },

    initKpoButton(btn) {
        // 1. PATIKRINAME NUSTATYMĄ: Ar šiam POS įjungtas KPO mygtukas?
        const pos = this.pos || (this.env && this.env.services && this.env.services.pos);
        if (!pos || !pos.config || !pos.config.iface_print_kpo) {
            return; // Jei nustatymas išjungtas - tiesiog baigiame darbą, mygtukas liks nematomas
        }

        const order = this.props?.order || this.currentOrder || pos.get_order();
        if (!order) return;

        // 2. PATIKRINAME: Ar apmokėta per KPO?
        const lines = typeof order.get_paymentlines === 'function' ? order.get_paymentlines() : (order.paymentlines || []);
        const hasKpo = lines.some(l => ((l.payment_method && l.payment_method.name) || l.name || '').toUpperCase().includes('KPO'));

        if (hasKpo) {
            // Nustatymas įjungtas IR apmokėta KPO -> Parodome mygtuką
            btn.style.display = 'block'; 
            
            btn.onclick = async () => {
                try {
                    btn.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Spausdinama...';
                    
                    let backendId = order.backendId || order.id;
                    let posRef = order.name || order.pos_reference;
                    
                    // Jei užsakymas dar neturi serverio ID, paklausiame serverio tiesiogiai
                    if (!backendId || typeof backendId !== 'number') {
                        const res = await this.env.services.orm.search('pos.order', [['pos_reference', '=', posRef]], { limit: 1 });
                        if (res && res.length > 0) {
                            backendId = res[0];
                        }
                    }

                    if (backendId) {
                        window.open('/report/pdf/l10n_lt_kpo_kio.action_report_kpo_kio_pos/' + backendId, '_blank');
                        btn.innerHTML = '<i class="fa fa-check"></i> KPO Atspausdintas';
                    } else {
                        alert("Užsakymas vis dar išsaugomas serveryje. Palaukite kelias sekundes ir bandykite vėl.");
                        btn.innerHTML = '<i class="fa fa-print"></i> KPO (A4)';
                    }
                } catch (error) {
                    console.error("Spausdinimo klaida:", error);
                    alert("Sistemos klaida spausdinant KPO.");
                    btn.innerHTML = '<i class="fa fa-print"></i> KPO (A4)';
                }
            };
        }
    }
});
