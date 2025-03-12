/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import ASPAIntegration from "./aspa_api";
import { onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

const aspa = new ASPAIntegration();

patch(PaymentScreen.prototype, {
    setup() {
        super.setup();
        this.orm = useService("orm");
    },

    // open fiscal receipt
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
                    console.log("line raw id:", line.refunded_orderline_id.raw.id);
                    const originOrders = await this.orm.call("pos.order", "search_read", [
                        [["lines", "in", [line.refunded_orderline_id.raw.id]]],
                        ["pos_reference"],
                    ]);
                    console.log("originOrders:", originOrders);

                    if (originOrders && originOrders.length > 0) {
                        posReference = originOrders[0].pos_reference;
                        break;
                    } else {
                        console.error("No order found containing the refunded line ID:", line.refunded_orderline_id);
                    }
                }

                if (!posReference) {
                    console.error("Previous receipt number is missing for return order.");
                    throw new Error("Missing previous receipt number for return.");
                }

                const tillNumber = "1";
                const receiptNumber = posReference.split("Aspa Receipt:")[1]?.trim();
                if (!receiptNumber) {
                    console.error("Previous receipt number is missing for return order.");
                    throw new Error("Missing previous receipt number for return.");
                }

                const returnCommand = `G,${tillNumber}-${receiptNumber};`;
                await aspa.sendCommand("48", returnCommand);
            } else {
                await aspa.sendCommand("48", "");
            }
        } catch (error) {
            throw error;
        }
    },

    // register products
    async _registerProducts() {
        const order = this.pos.get_order();
        if (order) {
            const orderLines = order.lines;
            for (const line of orderLines) {
                if (line.product_id.default_code === "DISC") {
                    continue;
                }

                console.log(line);
                const product = line.product_id;
                const quantity = line.qty * -1;
                const taxLetter = product.is_deposit ? "N" : "A";
                let price = line.getUnitDisplayPriceBeforeDiscount();
                const discount = line.discount > 0 ? `,-${line.discount}` : "";
                const parameter = `${product.display_name}\t${taxLetter}${price.toFixed(2)}*${quantity}${discount}`;

                try {
                    await aspa.sendCommand("49", parameter);
                } catch (error) {
                    console.error(`Error registering product "${product.display_name}":`, error);
                }
            }
        }
    },

    // finalize validation and register payment lines before closing the receipt
    async _finalizeValidation() {
        await this._openFiscalReceipt();
        await this._registerProducts();
        const paymentLines = this.currentOrder.payment_ids;
        let receiptNumber;
        const order = this.pos.get_order();

        if (!order) {
            console.error("No order found.");
            return;
        }

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
            console.log("subtotalResponse:", subtotalResponse);
            fullAmount = parseFloat(subtotalResponse.CmdlineResult.split(",")[1]) / 100;
            console.log("fullAmount:", fullAmount);

        } catch (error) {
            console.error("Error processing order lines:", error);
        }


        // register single payment line
        if (paymentLines && paymentLines.length == 1) {
            console.log('THERE IS ONE PAYMENT LINE');
            const line = paymentLines[0];
            const paymentType = this._getPaymentType(line.payment_method_id.name);
            let paymentText = `\t${paymentType}${(Math.floor(fullAmount * 100) / 100).toFixed(2)}`;
            const roundedFullAmount = (Math.round(fullAmount * 20) / 20).toFixed(2);
            const paymentAmount = line.amount;

            if (paymentType === 'C') {
                try {
                    const bankasResponse = await aspa.sendBankas0({ amount: fullAmount });
                    if (!bankasResponse || !bankasResponse.BankasSale0Result.startsWith("OK")) {
                        console.error("Bank card payment failed:", bankasResponse);
                        throw new Error("Bank card payment failed.");
                    }
                } catch (error) {
                    console.error("Error processing BankasSale0:", error);
                    throw new Error("Bank card payment failed.");
                }
            }

            if (paymentAmount == roundedFullAmount && paymentType === 'P') {
                paymentText = "";
            }

            try {
                await aspa.sendCommand("53", paymentText);
            } catch (error) {
                console.error("Error registering payment line:", error);
                throw error;
            }
        }

        // register multiple payment lines
        if (paymentLines && paymentLines.length > 1) {
            await this._processMixedPayments(paymentLines, fullAmount);
        }

        // finalize fiscal receipt
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

    // process mixed payments
    async _processMixedPayments(paymentLines, fullAmount) {
        let remainingAmount = Math.floor(fullAmount * 100) / 100;
        for (const line of paymentLines) {
            const paymentType = this._getPaymentType(line.payment_method_id.name);
            if (paymentType === 'P') {
                let cashPaymentText = `\t${paymentType}${line.amount.toFixed(2)}`;
                remainingAmount -= line.amount;
                try {
                    await aspa.sendCommand("53", cashPaymentText);
                } catch (error) {
                    console.error("Error registering cash payment line:", error);
                    throw error;
                }

            } else if (paymentType === 'C') {
                let cardPaymentText = `\t${paymentType}${remainingAmount.toFixed(2)}`;
                try {
                    await aspa.sendBankas0({ amount: remainingAmount });
                    await aspa.sendCommand("53", cardPaymentText);
                } catch (error) {
                    console.error("Error registering card payment line:", error);
                    throw error;
                }
                remainingAmount = 0;
            }
        }
    },

    _getPaymentType(paymentMethod) {
        switch (paymentMethod) {
            case 'Cash':
                return 'P';
            case 'Grynieji':
                return 'P';
            case 'Card':
                return 'C';
            case 'Kortelė':
                return 'C';
            case 'Kortele':
                return 'C';
            case 'Credit':
                return 'N';
            case 'Check':
                return 'D';
            case 'Wolt':
                return 'N';
            default:
                return 'P';
        }
    },
});
