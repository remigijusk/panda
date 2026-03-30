/** @odoo-module */
import { ClosePosPopup } from "@point_of_sale/app/navbar/closing_popup/closing_popup";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

patch(ClosePosPopup.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.notification = useService("notification");
    },
    async printXReport() {
        try {
            this.notification.add("Siunčiama X Ataskaita...", { type: "info" });
            const success = await this.orm.call(
                "pos.session",
                "print_nsoft_x_report",
                [[this.pos.pos_session.id]]
            );
            if (success) {
                this.notification.add("X Ataskaita sėkmingai išspausdinta!", { type: "success" });
            } else {
                this.notification.add("Nepavyko atspausdinti X Ataskaitos.", { type: "danger" });
            }
        } catch (error) {
            this.notification.add("Klaida spausdinant X ataskaitą.", { type: "danger" });
            console.error(error);
        }
    }
});
