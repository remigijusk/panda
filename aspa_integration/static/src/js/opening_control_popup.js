/** @odoo-module */

import { OpeningControlPopup } from "@point_of_sale/app/store/opening_control_popup/opening_control_popup";
import { patch } from "@web/core/utils/patch";
import ASPAIntegration from "./aspa_api";

const aspaIntegration = new ASPAIntegration();

function parseLocaleNumber(str) {
    if (!str || typeof str !== 'string') return NaN;

    str = str.replace(/\s/g, '');

    const comma = str.includes(',');
    const dot = str.includes('.');

    if (comma && dot && str.indexOf(',') > str.indexOf('.')) {
        return Number(str.replace(/\./g, '').replace(',', '.'));
    }

    if (comma && dot && str.indexOf('.') > str.indexOf(',')) {
        return Number(str.replace(/,/g, ''));
    }

    if (comma && !dot) {
        return Number(str.replace(',', '.'));
    }

    return Number(str);
}


patch(OpeningControlPopup.prototype, {
    async confirm() {
        const confirmed = await super.confirm();
        const rawCash = this.state.openingCash;
        const openingCash = parseLocaleNumber(rawCash);

        if (isNaN(openingCash)) {
            console.warn("Invalid cash input format:", rawCash);
            return confirmed;
        }

        try {
            await aspaIntegration.sendCommand("70", "+" + openingCash.toFixed(2));
        } catch (error) {
            console.error("Error processing cash operation:", error);
        }

        return confirmed;
    },
});

