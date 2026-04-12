/** @odoo-module */
/**
 * nSoft X Ataskaita – POS hamburger menu mygtukas
 * Prideda "X Ataskaita" mygtuką šalia "Grynųjų į/iš-nešimas"
 */

import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { useService } from "@web/core/utils/hooks";

patch(ProductScreen.prototype, {
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
                this.notification.add("X Ataskaita išsiųsta į spausdintuvą", {
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
