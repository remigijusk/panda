/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { CashMovePopup } from "@point_of_sale/app/navbar/cash_move_popup/cash_move_popup";
import ASPAIntegration from "./aspa_api";

const aspa = new ASPAIntegration();

patch(CashMovePopup.prototype, {
    setup() {
        super.setup();
        aspa.setPosConfigId(this.pos.config.id);
    },

    async confirm() {
        const amount = parseFloat(this.state.amount);
        const type = this.state.type;
        const parameter = type === "in" ? `+${amount.toFixed(2)}` : `-${amount.toFixed(2)}`;

        try {
            await aspa.sendCommand("70", parameter);
            await aspa.sendCommand("106", "");
        } catch (error) {
            console.error("Error processing cash operation:", error);
        }

        return await super.confirm();
    },
});
