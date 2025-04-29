/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import ASPAIntegration from "./aspa_api";
import { useService } from "@web/core/utils/hooks";

const aspa = new ASPAIntegration();

patch(PaymentScreen.prototype, {
    setup() {
        super.setup();
        this.orm = useService("orm");
        aspa.setPosConfigId(this.pos.config.id);
    },

    async _openFiscalReceipt() {
        const order = this.pos.get_order();
        if (!order) {
            console.error("No order found while opening fiscal receipt.");
            return;
        }

        try {
            if (order._isRefundOrder()) {
                const orderLines = order.lines;
                let posReference;
                for (const line of orderLines) {
                    const originOrders = await this.orm.call("pos.order", "search_read", [
                        [["lines", "in", [line.refunded_orderline_id.raw.id]]],
                        ["pos_reference"],
                    ]);
                    if (originOrders && originOrders.length > 0) {
                        posReference = originOrders[0].pos_reference;
                        break;
                    }
                }
                if (!posReference) {
                    console.error("Previous receipt number is missing for return order.");
                    throw new Error("Missing previous receipt number for return.");
                }
                let receiptNumber = posReference.includes("Aspa Receipt:")
                    ? posReference.split("Aspa Receipt:")[1].trim()
                    : posReference.replace(/[^0-9]/g, '');
                const returnCommand = `G,${receiptNumber};`;
                const pos_config_id = this.pos.config.id;


                await aspa.sendCommand("48", returnCommand);
            } else {
                console.log(this)
                console.log(this.pos.config.id)
                await aspa.sendCommand("48", "");
            }
        } catch (error) {
            throw error;
        }
    },


    async _registerProducts() {

        function splitProductNameByWords(name, maxLength = 41) {
            const words = name.split(" ");
            const lines = [];
            let currentLine = "";

            for (const word of words) {
                if ((currentLine + " " + word).trim().length <= maxLength) {
                    currentLine = (currentLine + " " + word).trim();
                } else {
                    if (currentLine) {
                        lines.push(currentLine);
                    }
                    currentLine = word;
                }
            }

            if (currentLine) {
                lines.push(currentLine);
            }

            return lines.join("\n");
        }

        const order = this.pos.get_order();
        if (!order) return;

        for (const line of order.lines) {
            if (line.product_id.default_code === "DISC") {
                continue;
            }

            const product = line.product_id;
            let quantity = Math.abs(line.qty);
            const taxLetter = product.is_deposit ? "N" : "A";
            const lineTotalWithTax = typeof line.get_price_with_tax === "function" ? line.get_price_with_tax() : 0;
            const unitPrice = quantity !== 0 ? (lineTotalWithTax / quantity) : 0;
            const formattedPrice = unitPrice.toFixed(4);

            let productName = product.display_name || "";
            if (line.discount && line.discount > 0) {
                productName += ` -${line.discount}%`;
            }

            productName = splitProductNameByWords(productName);

            const parameter = `${productName}\t${taxLetter}${formattedPrice}*${quantity}`;

            try {
                await aspa.sendCommand("49", parameter);
            } catch (error) {
                console.error(`Error registering product "${productName}":`, error);
            }
        }
    },

    async _finalizeValidation() {
        const order = this.pos.get_order();
        if (!order) {
            console.error("No order found.");
            return;
        }

        const paymentLines = this.currentOrder.payment_ids;
        for (const line of paymentLines) {
            const paymentType = this._getPaymentType(line.payment_method_id.name);
            const amount = parseFloat(line.amount.toFixed(2)).toFixed(2);
            if (paymentType === 'C') {
                try {
                    const bankasResponse = await aspa.sendBankas0(amount);
                    if (!bankasResponse || !bankasResponse.BankasSale0Result.startsWith("OK")) {
                        console.error("Bank card payment failed:", bankasResponse);
                        throw new Error("Bank card payment failed.");
                    }
                } catch (error) {
                    console.error("Error processing BankasSale0:", error);
                    throw new Error("Bank card payment failed.");
                }
            }
        }

        await this._openFiscalReceipt();
        await this._registerProducts();

        let fullAmount;
        try {
            const orderLines = Array.isArray(order.lines) ? order.lines : [...order.lines];
            const discountLine = orderLines.find(line => line.product_id?.default_code === "DISC");
            let parameterText = "11";

            if (discountLine) {
                const discountLineSubtotal = discountLine.price_subtotal_incl * -1;
                const orderPriceSubtotal = order.get_total_with_tax() + discountLineSubtotal;
                const discountPercentage = (discountLineSubtotal / orderPriceSubtotal) * 100;
                parameterText = `11,-${discountPercentage.toFixed()}`;
            }

            const subtotalResponse = await aspa.sendCommand("51", parameterText);
            fullAmount = parseFloat(subtotalResponse.CmdlineResult.split(",")[1]) / 100;

            if (order._isRefundOrder()) {
                fullAmount = Math.abs(fullAmount);
            }

        } catch (error) {
            console.error("Error processing order lines:", error);
            return;
        }

        if (paymentLines && paymentLines.length === 1) {
            await this._processSinglePayment(paymentLines[0], fullAmount, order);
        } else if (paymentLines && paymentLines.length > 1) {
            await this._processMixedPayments(paymentLines);
        }

        let receiptNumber;
        try {
            const response = await aspa.sendCommand("56", "");
            receiptNumber = response.CmdlineResult.split(",")[1];
        } catch (error) {
            await aspa.sendCommand("57", "");
            console.error("Error finalizing fiscal receipt:", error);
            throw error;
        }

        const finalized = await super._finalizeValidation();
        if (order && order.raw.id) {
            await this.orm.call("pos.order", "update_pos_reference", [
                [order.raw.id],
                `Aspa Receipt:${receiptNumber}`,
            ]);
        }

        return finalized;
    },

    async _processSinglePayment(line, fullAmount, order) {
        const paymentType = this._getPaymentType(line.payment_method_id.name);
        const paymentAmount = line.amount.toFixed(2);
        const paymentText = `\t${paymentType}${paymentAmount}`;

        try {
            await aspa.sendCommand("53", paymentText);
        } catch (error) {
            console.error("Error registering payment line:", error);
            await aspa.sendCommand("57", "");
            throw error;
        }
    },

    async _processMixedPayments(paymentLines) {
        paymentLines.sort((a, b) => {
            const typeA = this._getPaymentType(a.payment_method_id.name);
            const typeB = this._getPaymentType(b.payment_method_id.name);
            return typeA === 'C' ? -1 : 1;
        });

        for (const line of paymentLines) {
            const paymentType = this._getPaymentType(line.payment_method_id.name);
            const paymentAmount = line.amount.toFixed(2);
            const paymentText = `\t${paymentType}${paymentAmount}`;

            try {
                await aspa.sendCommand("53", paymentText);
            } catch (error) {
                console.error(`Error registering ${paymentType} payment line:`, error);
                await aspa.sendCommand("57", "");
                throw error;
            }
        }
    },

    _getPaymentType(paymentMethod) {
        switch (paymentMethod) {
            case 'Cash':
            case 'Grynieji':
                return 'P';
            case 'Card':
            case 'Kortelė':
            case 'Kortele':
                return 'C';
            case 'Credit':
            case 'Wolt':
                return 'N';
            case 'Check':
                return 'D';
            default:
                return 'P';
        }
    },
});
