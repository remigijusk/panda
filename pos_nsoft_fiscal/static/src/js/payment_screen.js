/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { Chrome } from "@point_of_sale/app/pos_app";
import { useService } from "@web/core/utils/hooks";
import { onMounted, onWillUnmount } from "@odoo/owl";

/**
 * Adds nSoft control buttons to the POS burger menu:
 *   - X / Z fiscal reports
 *   - Cash IN / Cash OUT (calls standard try_cash_in_out so Odoo statement
 *     line is created AND nSoft cash endpoint is hit; receipt text returned
 *     by nSoft is printed via pos.printer)
 *
 * Sale-receipt printing is handled by the standard Odoo POS pipeline:
 * OrderReceipt.xml renders nsoft_receipt_text into a <pre> block and
 * Odoo's pos.printer prints it.
 */
patch(Chrome.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.notification = useService("notification");
        this._nsoftInterval = null;
        onMounted(() => {
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
        const menu = document.querySelector(".pos-burger-menu-items");
        if (!menu) return;

        const addBtn = (cls, label, handler) => {
            if (menu.querySelector("." + cls)) return;
            const btn = document.createElement("span");
            btn.className = "o-dropdown-item dropdown-item o-navigable " + cls;
            btn.setAttribute("role", "menuitem");
            btn.style.cursor = "pointer";
            btn.textContent = label;
            btn.addEventListener("click", (e) => {
                e.stopPropagation();
                handler.call(this);
            });
            menu.appendChild(btn);
        };

        addBtn("nsoft-x-btn", "\u{1F4CA} X Ataskaita (i.EKA)",
               this.printNsoftXReport);
        addBtn("nsoft-z-btn", "\u{1F4C4} Z Ataskaita (i.EKA)",
               this.printNsoftZReport);
        addBtn("nsoft-cash-in-btn", "\u{1F4B5} Pinigu idejimas (i.EKA)",
               this.nsoftCashIn);
        addBtn("nsoft-cash-out-btn", "\u{1F4B8} Pinigu isemimas (i.EKA)",
               this.nsoftCashOut);
    },

    /**
     * Print nVF text via Odoo's standard pos.printer (ePos or IoT Box).
     * The text comes from nVF API and is the only legally-printable content.
     */
    async _nsoftPrintText(text) {
        if (!text) return false;
        const escapeHtml = (s) =>
            s
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;");
        const html =
            '<div class="pos-receipt"><pre style="font-family:\'Courier New\',monospace;font-size:12px;white-space:pre;margin:0;padding:0;line-height:1.2;">' +
            escapeHtml(text) +
            "</pre></div>";
        try {
            const printer = this.pos?.printer || this.pos?.hardwareProxy?.printer;
            if (printer && typeof printer.printReceipt === "function") {
                const res = await printer.printReceipt(html);
                if (res && res.successful === false) {
                    this.notification.add(res.message?.body || "Spausdintuvas nepasiekiamas.", {
                        type: "danger",
                        title: "Spausdinimo klaida",
                    });
                    return false;
                }
                return true;
            }
        } catch (e) {
            this.notification.add((e?.message || e).toString(), {
                type: "danger",
                title: "Spausdinimo klaida",
            });
            return false;
        }
        return false;
    },

    async _nsoftHandleReport(methodName, defaultTitle) {
        try {
            const result = await this.orm.call("pos.session", methodName,
                [[this.pos.session.id]]);
            console.log("[nSoft] " + methodName + " response:", result);
            if (result && result.success === false) {
                this.notification.add(result.message || "Klaida", {
                    type: "danger",
                    title: result.title || "i.EKA klaida",
                });
                return;
            }
            const text = result && result.receipt_text;
            if (text) {
                await this._nsoftPrintText(text);
                this.notification.add(result.message || "Atspausdinta.", {
                    type: "success",
                    title: result.title || defaultTitle,
                });
            } else {
                this.notification.add(
                    (result && result.message) || "Suformuota, bet teksto negauta.",
                    { type: "warning", title: (result && result.title) || defaultTitle }
                );
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

    /**
     * Prompt for amount, call standard try_cash_in_out (overridden in
     * pos.session to also hit nSoft + return receipt text), then print.
     */
    async _nsoftCashOp(direction, defaultTitle) {
        const raw = window.prompt(
            (direction === "in" ? "Pinigu idejimas" : "Pinigu isemimas") +
            "\n\nIveskite suma (EUR):", "0");
        if (raw === null) return;
        const amount = parseFloat((raw || "0").replace(",", "."));
        if (!isFinite(amount) || amount <= 0) {
            this.notification.add("Suma turi buti teigiama.",
                { type: "warning", title: defaultTitle });
            return;
        }
        const reason = direction === "in" ? "Pinigu idejimas" : "Pinigu isemimas";
        try {
            const result = await this.orm.call("pos.session", "try_cash_in_out",
                [[this.pos.session.id], direction, amount, reason, {}]);
            console.log("[nSoft] cash-" + direction + " response:", result);
            const text = result && result.nsoft_receipt_text;
            if (text) {
                await this._nsoftPrintText(text);
            }
            this.notification.add(amount.toFixed(2) + " EUR uzregistruota.",
                { type: "success", title: defaultTitle });
        } catch (e) {
            this.notification.add((e.message || e).toString(),
                { type: "danger", title: defaultTitle });
        }
    },

    async nsoftCashIn() {
        await this._nsoftCashOp("in", "Pinigu idejimas");
    },

    async nsoftCashOut() {
        await this._nsoftCashOp("out", "Pinigu isemimas");
    },
});
