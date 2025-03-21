/** @odoo-module */

import { ClosePosPopup } from "@point_of_sale/app/navbar/closing_popup/closing_popup";
import { patch } from "@web/core/utils/patch";
import ASPAIntegration from "./aspa_api";

const aspaIntegration = new ASPAIntegration();

patch(ClosePosPopup.prototype, {
    async confirm() {
        const confirmed = await super.confirm();
        try {
            await aspaIntegration.sendCommand("69", "");
        } catch (error) {
            console.error("Error printing Z-report:", error);
        }
        return confirmed;
    },
});
