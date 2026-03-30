/** @odoo-module */
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";

export class XReportButton extends Component {
    static template = "pos_nsoft_fiscal.XReportButton";

    setup() {
        this.pos = usePos();
        this.orm = useService("orm");
        this.notification = useService("notification");
    }

    async onClick() {
        try {
            this.notification.add("Siunčiama X Ataskaitos komanda...", { type: "info" });
            const success = await this.orm.call(
                "pos.session",
                "print_nsoft_x_report",
                [[this.pos.pos_session.id]]
            );
            if (success) {
                this.notification.add("X Ataskaita sėkmingai atspausdinta!", { type: "success" });
            } else {
                this.notification.add("Nepavyko atspausdinti X Ataskaitos.", { type: "danger" });
            }
        } catch (error) {
            this.notification.add("Klaida spausdinant X ataskaitą.", { type: "danger" });
            console.error(error);
        }
    }
}

registry.category("pos_control_buttons").add("XReportButton", XReportButton);
