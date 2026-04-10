/** @odoo-module */
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, {
    async validateOrder(isForceValidate) {
        if (!this.pos.config.nsoft_enabled) {
            return super.validateOrder(...arguments);
        }

        const order = this.currentOrder;
        
        // 1. SAUGIAUSIAS BŪDAS: Traukiame duomenis tiesiai iš Odoo kvitų generatoriaus!
        let receiptData = {};
        try {
            if (typeof order.export_for_printing === 'function') {
                receiptData = order.export_for_printing();
            }
        } catch (e) {
            console.error("Nepavyko ištraukti čekio duomenų:", e);
        }

        // 2. Renkame sumas iš čekio (kur jos garantuotai egzistuoja ir yra teisingos)
        let trueTotal = receiptData.total_with_tax || order.amount_total || 0;
        let linesData = [];

        if (receiptData.orderlines && receiptData.orderlines.length > 0) {
            linesData = receiptData.orderlines.map(l => ({
                qty: l.quantity !== undefined ? l.quantity : 1,
                price: l.price !== undefined ? l.price : 0,
                total: l.price_display !== undefined ? l.price_display : (l.price_with_tax || 0),
                name: l.product_name || "Prekė"
            }));
        } else {
            // Atsarginis variantas, jei Odoo 19 atiduoda struktūrą kitaip
            const orderLines = order.lines || [];
            for (const line of orderLines) {
                let qty = line.qty !== undefined ? line.qty : (line.quantity || 1);
                let price = line.price_unit !== undefined ? line.price_unit : (line.price || 0);
                let total = line.price_subtotal_incl !== undefined ? line.price_subtotal_incl : (qty * price);
                let name = line.full_product_name || (line.product ? line.product.display_name : "Prekė");
                linesData.push({ qty, price, total, name });
            }
        }

        // Galutinis saugiklis nuo 0.00
        if (!trueTotal || trueTotal === 0) {
            trueTotal = linesData.reduce((sum, line) => sum + line.total, 0);
        }

        const orderData = {
            config_id: this.pos.config.id,
            true_total: trueTotal,
            lines: linesData
        };

        // 3. Siunčiame paruoštus, garantuotai ne nulinius duomenis į Python
        try {
            const orm = this.env.services.orm;
            const result = await orm.call("pos.order", "action_send_receipt_to_nsoft", [orderData]);
            
            if (result && result.success) {
                order.nsoft_receipt_id = result.receipt_id;
                order.nsoft_error = false;
            } else {
                order.nsoft_receipt_id = false;
                order.nsoft_error = result ? result.error : "Nėra atsakymo iš nSoft";
            }
        } catch (error) {
            order.nsoft_receipt_id = false;
            order.nsoft_error = "Sistemos klaida: " + error.message;
        }

        // 4. Perduodame ID (arba klaidą) į patį kvitą
        if (typeof order.export_for_printing === 'function' && !order._nsoft_patched) {
            const originalExport = order.export_for_printing.bind(order);
            order.export_for_printing = () => {
                const receipt = originalExport();
                receipt.nsoft_receipt_id = order.nsoft_receipt_id;
                receipt.nsoft_error = order.nsoft_error;
                return receipt;
            };
            order._nsoft_patched = true;
        }

        return super.validateOrder(...arguments);
    }
});
