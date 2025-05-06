/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";

class ASPAIntegration {
    constructor() {
        this.state = {
            status: "",
            aspaUrl: "",
            posConfigId: null,
        };
    }

    setPosConfigId(id) {
        this.state.posConfigId = id;
    }

    async sendCommand(cmd, parameter) {
        try {
            console.log("Sending command:", cmd, parameter);
            const response = await fetch("/aspa/command", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    cmd,
                    parameter,
                    pos_config_id: this.state.posConfigId,
                }),
            });

            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }

            const responseText = await response.text();
            let result;
            try {
                result = JSON.parse(responseText);
            } catch (e) {
                throw new Error("Failed to parse response JSON");
            }

            if (result.result && result.result.success) {
                const cmdlineResult = result.result.data.CmdlineResult;
                if (cmdlineResult.startsWith("ER")) {
                    console.log("Command returned an error:", responseText);
                    throw new Error(`Command failed with response: ${cmdlineResult}`);
                }
                console.log("Command successful:", cmdlineResult);
                return result.result.data;
            } else {
                throw new Error(result.result ? result.result.message : "Unknown error");
            }
        } catch (error) {
            console.error("Error sending command:", error);
            throw error;
        }
    }

    async sendBankas0(amount) {
        try {
            const result = await rpc("/aspa/bankassale0", {
                amount: amount,
                pos_config_id: this.state.posConfigId,
            });
            if (result.success) {
                return result.data;
            } else {
                console.error("BankasSale0 failed:", result.message);
                throw new Error(result.message || "BankasSale0 error");
            }
        } catch (error) {
            console.error("Error sending BankasSale0 request:", error);
            throw error;
        }
    }
}

export default ASPAIntegration;
