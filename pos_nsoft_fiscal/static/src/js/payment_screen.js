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
            if (this.pos?.config?.nsoft_enabled) {
                this._nsoftInterval = setInterval(() => this._nsoftInjectButtons(), 800);
            }
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

    async printNsoftXReport() {
        try {
            const result = await this.orm.call(
                "pos.session", "print_nsoft_x_report", [[this.pos.session.id]]
            );
            if (result) {
                const lines = result.receipt_lines || [];
                if (lines.length > 0 && this.pos.config.epson_printer_ip) {
                    this._printReportToEpson(lines);
                }
                this.notification.add(
                    result.params?.message || "X Ataskaita issiusta!",
                    { type: result.params?.type || "success", title: result.params?.title || "Pavyko!" }
                );
            }
        } catch (e) {
            this.notification.add("X klaida: " + (e.message || e), { type: "danger", title: "Klaida" });
        }
    },

    async printNsoftZReport() {
        try {
            const result = await this.orm.call(
                "pos.session", "print_nsoft_z_report", [[this.pos.session.id]]
            );
            if (result) {
                const lines = result.receipt_lines || [];
                if (lines.length > 0 && this.pos.config.epson_printer_ip) {
                    this._printReportToEpson(lines);
                }
                this.notification.add(
                    result.params?.message || "Z Ataskaita issiusta!",
                    { type: result.params?.type || "success", title: result.params?.title || "Pavyko!" }
                );
            }
        } catch (e) {
            this.notification.add("Z klaida: " + (e.message || e), { type: "danger", title: "Klaida" });
        }
    },

    _printReportToEpson(lines) {
        try {
            const ip = this.pos.config.epson_printer_ip;
            if (!ip) return;
            const url = `http://${ip}/cgi-bin/epos/service.cgi?devid=local_printer&timeout=10000`;
            const text = lines.join('\n').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
            const body = `<?xml version="1.0" encoding="utf-8"?><s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"><s:Body><epos-print xmlns="http://www.epson-pos.com/schemas/2011/03/epos-print"><text>${text}\n</text><feed unit="5"/><cut type="feed"/></epos-print></s:Body></s:Envelope>`;
            fetch(url, { method: 'POST', headers: { 'Content-Type': 'text/xml; charset=utf-8', 'SOAPAction': '""' }, body }).catch(e => console.error('Epson:', e));
        } catch(e) { console.error('_printReportToEpson:', e); }
    },
});
