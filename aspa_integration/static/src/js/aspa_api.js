/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";

class ASPAIntegration {
    constructor() {
        this.state = {
            status: "",
            aspaUrl: "",
        };
    }

    async loadAspaUrl() {
        try {
            const result = await rpc("/aspa/get_url", {});
            this.state.aspaUrl = result.url;
            console.log("Loaded ASPA URL:", this.state.aspaUrl);
        } catch (error) {
            console.error("Failed to load ASPA URL:", error);
        }
    }

    async sendCommand(cmd, parameter) {
        try {
            console.log("Sending command:", cmd, parameter);
            const response = await fetch("/aspa/command", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ cmd, parameter }),
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
                    console.error("Command returned an error:", cmd);
                    throw new Error(`Command failed with response: ${cmdlineResult}`);
                }
                console.log("Command successful:", cmdlineResult);
                return result.result.data;
            } else {
                console.error("Command failed:", result.result ? result.result.message : "Unknown error");
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

        if (window.location.protocol === "https:") {
            if (url.includes(".ngrok.app")) {
                url = url.replace("http://", "https://");
            }
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
                    console.log("Received response:", response);
                    try {
                        const parsedResponse = JSON.parse(JSON.stringify(response));
                        resolve(parsedResponse);
                    } catch (e) {
                        reject(new Error("Invalid JSON response from BankasSale0"));
                    }
                },
                error: function (error) {
                    console.error("BankasSale0 failed:", error);
                    reject(error);
                }
            });
        });
    }
}

export default ASPAIntegration;