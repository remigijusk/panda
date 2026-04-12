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
        btn.textContent = '📊 X Ataskaita (i.EKA)';
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
                this.notification.add("X Ataskaita išsiųsta į spausdintuvą!", {
                    type: "success",
                    title: "Pavyko!",
                });
            }
        } catch (e) {
            this.notification.add("X Ataskaitos klaida: " + (e.message || e), {
                type: "danger",
                title: "Klaida",
            });
        }
    },
});
