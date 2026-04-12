/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { Chrome } from "@point_of_sale/app/pos_app";
import { useService } from "@web/core/utils/hooks";

patch(Chrome.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.notification = useService("notification");
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
