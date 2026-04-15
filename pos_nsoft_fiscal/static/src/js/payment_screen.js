/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { Chrome } from "@point_of_sale/app/pos_app";
import { useService } from "@web/core/utils/hooks";
import { onMounted, onWillUnmount } from "@odoo/owl";

patch(Chrome.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.notification = useService("notification");
        this._nsoftInterval = null;
        onMounted(() => {
            // Paleidžiame be nsoft_enabled tikrinimo - jis visada veiks POS
            this._nsoftInterval = setInterval(() => this._nsoftInjectButtons(), 800);
        });
        onWillUnmount(() => {
            if (this._nsoftInterval) {
                clearInterval(this._nsoftInterval);
                this._nsoftInterval = null;
            }
        });
    },

    _nsoftInjectButtons() {
        const menu = document.querySelector('.pos-burger-menu-items');
        if (!menu) return;
        if (menu.querySelector('.nsoft-x-btn') && menu.querySelector('.nsoft-z-btn')) return;

        if (!menu.querySelector('.nsoft-x-btn')) {
            const btn = document.createElement('span');
            btn.className = 'o-dropdown-item dropdown-item o-navigable nsoft-x-btn';
            btn.setAttribute('role', 'menuitem');
            btn.style.cursor = 'pointer';
            btn.textContent = '\u{1F4CA} X Ataskaita (i.EKA)';
            btn.addEventListener('click', (e) => { e.stopPropagation(); this.printNsoftXReport(); });
            menu.appendChild(btn);
        }

        if (!menu.querySelector('.nsoft-z-btn')) {
            const btn = document.createElement('span');
            btn.className = 'o-dropdown-item dropdown-item o-navigable nsoft-z-btn';
            btn.setAttribute('role', 'menuitem');
            btn.style.cursor = 'pointer';
            btn.textContent = '\u{1F4C4} Z Ataskaita (i.EKA)';
            btn.addEventListener('click', (e) => { e.stopPropagation(); this.printNsoftZReport(); });
            menu.appendChild(btn);
        }
    },

    async _nsoftPrintText(text) {
        if (!text) return false;
        const escapeHtml = (s) => s
            .replace(/&/g, "&amp;").replace(/</g, "&lt;")
            .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
        const html = `<div class="pos-receipt">
            <pre style="font-family:'Courier New',monospace;font-size:12px;white-space:pre;margin:0;">${escapeHtml(text)}</pre>
        </div>`;
        try {
            const printer = this.pos?.printer || this.pos?.hardwareProxy?.printer;
            if (printer && typeof printer.printReceipt === "function") {
                const res = await printer.printReceipt(html);
                if (res && res.successful === false && res.canRetry) {
                    // fall through to browser print
                } else {
                    return true;
                }
            }
        } catch (e) {
            // ignore, fallback below
        }
        // Fallback: browser print dialog
        const w = window.open("", "_blank", "width=400,height=600");
        if (w) {
            w.document.write(`<html><head><title>i.EKA</title></head><body onload="window.print();">${html}</body></html>`);
            w.document.close();
            return true;
        }
        return false;
    },

    async _nsoftHandleReport(methodName, defaultTitle) {
        try {
            const result = await this.orm.call(
                "pos.session", methodName, [[this.pos.session.id]]
            );
            if (result && result.success === false) {
                this.notification.add(result.message || "Klaida",
                    { type: "danger", title: result.title || "i.EKA klaida" });
                return;
            }
            const text = result && result.receipt_text;
            if (text) {
                await this._nsoftPrintText(text);
                this.notification.add(result.message || "Atspausdinta.",
                    { type: "success", title: result.title || defaultTitle });
            } else {
                this.notification.add(
                    (result && result.message) || "Ataskaita suformuota, bet spausdinimo tekstas negautas.",
                    { type: "warning", title: (result && result.title) || defaultTitle });
            }
        } catch (e) {
            this.notification.add((e.message || e).toString(),
                { type: "danger", title: "Klaida" });
        }
    },

    async printNsoftXReport() {
        await this._nsoftHandleReport("print_nsoft_x_report", "X Ataskaita");
    },

    async printNsoftZReport() {
        await this._nsoftHandleReport("print_nsoft_z_report", "Z Ataskaita");
    },
});
