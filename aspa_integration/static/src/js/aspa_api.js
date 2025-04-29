/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";

class ASPAIntegration {
    constructor() {
        this.state = {
            status: "",
            aspaUrl: "",
            posConfigId: null,   // 🆕 save pos.config id here
        };
    }

    async loadAspaUrl() {
        try {
            const result = await rpc("/aspa/get_url", {
                pos_config_id: this.state.posConfigId,  // 🆕 pass it to backend
            });
            this.state.aspaUrl = result.url;
            console.log("Loaded ASPA URL:", this.state.aspaUrl);
        } catch (error) {
            console.error("Failed to load ASPA URL:", error);
        }
    }

    setPosConfigId(id) {  // 🆕 simple setter
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
                    pos_config_id: this.state.posConfigId,  // 🆕 always send pos_config_id
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
        await this.loadAspaUrl();

        if (!this.state.aspaUrl) {
            console.error("No ASPA URL configured!");
            return null;
        }

        let url = this.state.aspaUrl;

        if (window.location.protocol === "https:" && url.includes(".ngrok.app")) {
            url = url.replace("http://", "https://");
        }

        const payload = { amount: String(amount) };
        console.log("Sending Bankas0 request:", JSON.stringify(payload));
        console.log("To URL:", url);

        return new Promise((resolve, reject) => {
            $.ajax({
                type: "POST",
                url: url,
                data: JSON.stringify(payload),
                contentType: "application/json",
                accept: "application/json",
                success: function (response) {
                    try {
                        const parsedResponse = JSON.parse(JSON.stringify(response));
                        resolve(parsedResponse);
                    } catch (e) {
                        reject(new Error("Invalid JSON response from BankasSale0"));
                    }
                },
                error: function (error) {
                    reject(error);
                }
            });
        });
    }
}

export default ASPAIntegration;
