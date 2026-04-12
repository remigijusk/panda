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
        this._nsoftObserver = null;
        onMounted(() => this._nsoftStartObserver());
        onWillUnmount(() => this._nsoftStopObserver());
    },

    _nsoftStartObserver() {
        if (!this.pos.config.nsoft_enabled) return;
        this._nsoftObserver = new MutationObserver(() => this._nsoftInjectButton());
        this._nsoftObserver.observe(document.body, { childList: true, subtree: true });
    },

    _nsoftStopObserver() {
        this._nsoftObserver?.disconnect();
    },

    _nsoftInjectButton() {
        const menu = document.querySelector('.pos-burger-menu-items');
        if (!menu || menu.querySelector('.nsoft-x-btn')) return;
        const btn = document.createElement('span');
        btn.className = 'o-dropdown-item dropdown-item o-navigable nsoft-x-btn';
        btn.setAttribute('role', 'menuitem');
        btn.style.cursor = 'pointer';
        btn.textContent = '\u{1F4CA} X Ataskaita (i.EKA)';
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.printNsoftXReport();
        });
        menu.appendChild(btn);
    },

    async printNsoftXReport() {
        try {
            const sessionId = this.pos.session.id;
            const result = await this.orm.call(
                "pos.session",
                "print_nsoft_x_report",
                [[sessionId]]
            );
            if (result) {
                // Print via Epson if receipt lines returned
                const lines = result.receipt_lines || [];
                if (lines.length > 0 && this.pos.config.epson_printer_ip) {
                    this._printXReportToEpson(lines);
                }
                this.notification.add(
                    result.params?.message || "X Ataskaita išsiųsta!",
                    { type: result.params?.type || "success", title: result.params?.title || "Pavyko!" }
                );
            }
        } catch (e) {
            this.notification.add("X Ataskaitos klaida: " + (e.message || e), {
                type: "danger",
                title: "Klaida",
            });
        }
    },

    _printXReportToEpson(lines) {
        try {
            const ip = this.pos.config.epson_printer_ip;
            if (!ip) return;
            const url = `http://${ip}/cgi-bin/epos/service.cgi?devid=local_printer&timeout=10000`;
            const textContent = lines.join('\n');
            const body = `<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
<s:Body>
<epos-print xmlns="http://www.epson-pos.com/schemas/2011/03/epos-print">
<text>${textContent.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}\n</text>
<feed unit="5"/>
<cut type="feed"/>
</epos-print>
</s:Body>
</s:Envelope>`;
            fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'text/xml; charset=utf-8', 'SOAPAction': '""' },
                body: body,
            }).catch(e => console.error('Epson X report print error:', e));
        } catch(e) {
            console.error('_printXReportToEpson error:', e);
        }
    },
});
