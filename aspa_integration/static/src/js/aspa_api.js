/** @odoo-module **/

class ASPAIntegration {
    constructor() {
        this.state = {
            status: "",
        };
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

    async sendBankas0(data) {
        try {
            console.log("Sending Bankas0:", data);
            const response = await fetch("/aspa/bankas0", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(data),
            });

            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }

            const responseJson = await response.json();
            const responseData = responseJson.result.data;
            console.log('Response:', responseData);

            if (responseData.BankasSale0Result.startsWith("OK")) {
                console.log("Bankas0 successful:", responseData.BankasSale0Result);
                return responseData;
            } else {
                console.error("Bankas0 failed:", responseData.BankasSale0Result);
                return null;
            }
        } catch (error) {
            console.error("Error sending Bankas0:", error);
            return null;
        }
    }

}

export default ASPAIntegration;
