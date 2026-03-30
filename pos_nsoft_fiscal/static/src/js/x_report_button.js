/** @odoo-module */

import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

export class XReportButton extends Component {
    static template = "pos_nsoft_fiscal.XReportButton";

    setup() {
        this.pos = usePos();
        this.orm = useService("orm");
        this.notification = useService("notification");
    }

    async onClick() {
        try {
            await this.orm.call(
                "pos.session",
                "print_nsoft_x_report",
                [[this.pos.pos_session.id]]
            );
            this.notification.add("X Ataskaita sėkmingai išsiųsta į spausdintuvą!", { type: "success" });
        } catch (error) {
            this.notification.add("Klaida spausdinant X ataskaitą.", { type: "danger" });
            console.error(error);
        }
    }
}

ProductScreen.addControlButton({
    component: XReportButton,
    condition: function () {
        return true;
    },
});
