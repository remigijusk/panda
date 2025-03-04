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
    }
});