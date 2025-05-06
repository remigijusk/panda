/** @odoo-module */

import { ClosePosPopup } from "@point_of_sale/app/navbar/closing_popup/closing_popup";
import { patch } from "@web/core/utils/patch";
import ASPAIntegration from "./aspa_api";

const aspa = new ASPAIntegration();

patch(ClosePosPopup.prototype, {
    setup() {
        super.setup();
        aspa.setPosConfigId(this.pos.config.id);
    },

    async confirm() {
        const confirmed = await super.confirm();
        try {
            await aspa.sendCommand("69", "");
        } catch (error) {
            console.error("Error printing Z-report:", error);
        }
        return confirmed;
    },
});
