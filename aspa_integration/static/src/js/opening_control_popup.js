/** @odoo-module */

import { OpeningControlPopup } from "@point_of_sale/app/store/opening_control_popup/opening_control_popup";
import { patch } from "@web/core/utils/patch";
import ASPAIntegration from "./aspa_api";

const aspaIntegration = new ASPAIntegration();

function parseLocaleNumber(str) {

    if (!str || typeof str !== 'string') {
        return NaN;
    }

    str = str.replace(/\s/g, '');

    const comma = str.includes(',');
    const dot = str.includes('.');

    let parsed;

    if (comma && dot && str.indexOf(',') > str.indexOf('.')) {
        parsed = Number(str.replace(/\./g, '').replace(',', '.'));
    } else if (comma && dot && str.indexOf('.') > str.indexOf(',')) {
        parsed = Number(str.replace(/,/g, ''));
    } else if (comma && !dot) {
        parsed = Number(str.replace(',', '.'));
    } else {
        parsed = Number(str);
    }

    return parsed;
}

patch(OpeningControlPopup.prototype, {
    async confirm() {

        const confirmed = await super.confirm();
        const rawCash = this.state.openingCash;
        const openingCash = parseLocaleNumber(rawCash);

        if (isNaN(openingCash)) {
            return confirmed;
        }

        const param = "+" + openingCash.toFixed(2);
        if (this.pos?.config?.id) {
            aspaIntegration.setPosConfigId(this.pos.config.id);
        } else {
            console.warn("[ASPA DEBUG] this.pos.config.id not available!");
        }

        try {
            const response = await aspaIntegration.sendCommand("70", param);
        } catch (error) {
            console.error("[ASPA DEBUG] Error sending ASPA command '70' during register opening:", error);
        }

        return confirmed;
    },
});

