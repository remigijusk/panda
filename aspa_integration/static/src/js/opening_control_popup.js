/** @odoo-module */

import { OpeningControlPopup } from "@point_of_sale/app/store/opening_control_popup/opening_control_popup";
import { patch } from "@web/core/utils/patch";
import ASPAIntegration from "./aspa_api";

const aspaIntegration = new ASPAIntegration();

patch(OpeningControlPopup.prototype, {
    async confirm() {
        const confirmed = await super.confirm();
        const openingCash = Number(this.state.openingCash.replace(',', '.'));
        try {
            await aspaIntegration.sendCommand("70", "+" + openingCash.toFixed(2));
        } catch (error) {
            console.error("Error processing cash operation:", error);
        }
        return confirmed;
    },
});
