/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { onMounted } from "@odoo/owl";

/**
 * Patch ReceiptScreen so that when an order is fiscalized via nSoft, the
 * physical printout is sent to the local nSoft Print Agent (which forwards
 * raw ESC/POS to the Epson printer on TCP port 9100). This bypasses Odoo's
 * standard ePos integration which renders the receipt as a small bitmap
 * and produces an undersized/misaligned printout for non-Intelligent
 * Epson models (TM-T20III etc.).
 */
patch(ReceiptScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this._nsoftPrintedViaAgent = false;
        if (this._nsoftAgentConfigured()) {
            onMounted(async () => {
                if (!this._nsoftPrintedViaAgent) {
                    const ok = await this._nsoftPrintReceiptViaAgent();
                    if (ok) {
                        this._nsoftPrintedViaAgent = true;
                    }
                }
            });
        }
    },

    _nsoftAgentConfigured() {
        const config = this.pos?.config;
        return !!(config?.nsoft_print_agent_url && config?.nsoft_printer_host);
    },

    _nsoftCurrentOrder() {
        return this.currentOrder || this.pos?.get_order?.();
    },

    async _nsoftPrintReceiptViaAgent() {
        const config = this.pos?.config;
        const order = this._nsoftCurrentOrder();
        const text = order?.nsoft_receipt_text;
        if (!text || !this._nsoftAgentConfigured()) {
            return false;
        }
        try {
            const resp = await fetch(config.nsoft_print_agent_url, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    host: (config.nsoft_printer_host || "").trim(),
                    port: parseInt(config.nsoft_printer_port || 9100, 10),
                    text: text,
                }),
            });
            const data = await resp.json().catch(() => ({}));
            if (resp.ok && data.success) {
                console.log("[nSoft] Receipt printed via agent:", data);
                return true;
            }
            console.warn("[nSoft] Agent print failed:", resp.status, data);
        } catch (e) {
            console.warn("[nSoft] Agent error:", e);
        }
        return false;
    },

    /**
     * Override manual "Print Receipt" button so it also goes through the
     * agent. Falls back to Odoo's standard printer if agent fails.
     */
    async printReceipt() {
        if (this._nsoftAgentConfigured()) {
            const ok = await this._nsoftPrintReceiptViaAgent();
            if (ok) {
                return;
            }
        }
        if (super.printReceipt) {
            return super.printReceipt(...arguments);
        }
    },
});
