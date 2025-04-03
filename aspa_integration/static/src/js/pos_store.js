import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import ASPAIntegration from "./aspa_api";

const aspaIntegration = new ASPAIntegration();

patch(PosStore.prototype, {
    async printXreport() {
        console.log("Printing X-report");
        try {
            await aspaIntegration.sendCommand("69", "2");
        } catch (error) {
            console.error("Error printing X-report:", error);
        }
    },

    async printZreport() {
        console.log("Printing Z-report");
        try {
            await aspaIntegration.sendCommand("69", "");
        } catch (error) {
            console.error("Error printing Z-report:", error);
        }
    },

    async onClickWeigh() {
    const order = this.selectedOrder;
    const line = order?.get_selected_orderline();

    if (!line) {
        this.notification.add("No order line selected", { type: "warning" });
        return;
    }

    try {
        const response = await aspaIntegration.sendCommand("1000", "");
        const result = response?.CmdlineResult?.trim();

        if (!result) {
            this.notification.add("Empty response from scale", { type: "danger" });
            return;
        }

        const match = result.match(/^OK,([SU])\s+(\d+)g$/);

        if (!match) {
            this.notification.add("Invalid weight format received", { type: "danger" });
            return;
        }

        const stability = match[1];
        const grams = parseInt(match[2], 10);

        if (isNaN(grams)) {
            this.notification.add("Weight parse error", { type: "danger" });
            return;
        }

        if (stability === "U") {
            this.notification.add("Unstable weight detected. Please wait...", { type: "warning" });
            return;
        }

        const kg = grams / 1000;
        line.set_quantity(kg);

    } catch (error) {
        console.error("Error during ASPA weigh:", error);
        this.notification.add("Weighing failed", { type: "danger" });
    }
}



});