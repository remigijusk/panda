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
                    const originOrders = await this.orm.call("pos.order", "search_read", [
                        [["lines", "in", [line.refunded_orderline_id.raw.id]]],
                        ["pos_reference"],
                    ]);

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

                let receiptNumber = "";
                if (posReference && posReference.includes("Aspa Receipt:")) {
                    receiptNumber = posReference.split("Aspa Receipt:")[1]?.trim();
                }

                if (!receiptNumber) {
                    console.warn("ASPA Receipt reference not found, using raw POS reference.");
                    receiptNumber = posReference?.trim() || "";
                    if (receiptNumber) {
                        receiptNumber = receiptNumber.replace(/[^0-9]/g, '');
                    }
                }

                const returnCommand = `G,${receiptNumber};`;
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

                const product = line.product_id;
                let quantity = line.qty;
                if (quantity < 0) {
                    quantity = Math.abs(quantity);
                }
                const taxLetter = product.is_deposit ? "N" : "A";
                const unitPrice = line.get_price_with_tax_before_discount() / quantity;
                let formattedPrice = unitPrice.toFixed(4);
                if (order._isRefundOrder()) {
                    formattedPrice = Math.abs(formattedPrice);
                }
                const discount = line.discount > 0 ? `,-${line.discount}` : "";
                const parameter = `${product.display_name}\t${taxLetter}${formattedPrice}*${quantity}${discount}`;

                try {
                    await aspa.sendCommand("49", parameter);
                } catch (error) {
                    console.error(`Error registering product "${product.display_name}":`, error);
                }
            }
        }
    },

    // finalize validation
    async _finalizeValidation() {
        const order = this.pos.get_order();

        if (!order) {
            console.error("No order found.");
            return;
        }

        // deal with one cent rounding issues
        const orderLines = order.lines;
        let oneCentAdjustment = await this._centRoundingAdjustment(orderLines);

        // process BankasSale0 first if there's a card payment
        const paymentLines = this.currentOrder.payment_ids;
        for (const line of paymentLines) {
            const paymentType = this._getPaymentType(line.payment_method_id.name);
            const amount = (parseFloat(line.amount.toFixed(2)) + oneCentAdjustment).toFixed(2);
            if (paymentType === 'C') {
                try {
                    const bankasResponse = await aspa.sendBankas0({ amount: amount });
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

        // calculate full amount
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

        // process payments (cash or mixed)
        if (paymentLines && paymentLines.length === 1) {
            await this._processSinglePayment(paymentLines[0], fullAmount, order);
        } else if (paymentLines && paymentLines.length > 1) {
            await this._processMixedPayments(paymentLines);
        }

        // finalize fiscal receipt
        let receiptNumber;
        try {
            const response = await aspa.sendCommand("56", "");
            receiptNumber = response.CmdlineResult.split(",")[1];
        } catch (error) {
            await aspa.sendCommand("57", "");
            console.error("Error finalizing fiscal receipt:", error);
            throw error;
        }

        // save the receipt reference
        const finalized = await super._finalizeValidation();
        if (order && order.raw.id) {
            await this.orm.call("pos.order", "update_pos_reference", [
                [order.raw.id],
                `Aspa Receipt:${receiptNumber}`,
            ]);
        }

        return finalized;
    },

    // process single payments
    async _processSinglePayment(line, fullAmount, order) {
        const paymentType = this._getPaymentType(line.payment_method_id.name);
        let roundedFullAmount = (Math.round(fullAmount * 20) / 20).toFixed(2);

        if (order._isRefundOrder()) {
            roundedFullAmount = roundedFullAmount * -1;
        }

        const paymentAmount = line.amount.toFixed(2);
        let paymentText = "";

        if (paymentAmount == roundedFullAmount && paymentType === 'P' && !order._isRefundOrder()) {
            paymentText = ``;
        } else if (paymentAmount > roundedFullAmount && paymentType === 'P') {
            paymentText = `\t${paymentType}${paymentAmount}`;
        } else if (paymentType === 'P' && order._isRefundOrder()) {
            paymentText = `\t${paymentType}${roundedFullAmount}`;
        } else if (paymentType === 'C') {
            paymentText = `\t${paymentType}${fullAmount}`;
        } else {
            paymentText = `\t${paymentType}${paymentAmount}`;
        }

        try {
            await aspa.sendCommand("53", paymentText);
        } catch (error) {
            console.error("Error registering payment line:", error);
            await aspa.sendCommand("57", "");
            throw error;
        }
    },

    // process mixed payments
    async _processMixedPayments(paymentLines) {
        paymentLines.sort((a, b) => {
            const typeA = this._getPaymentType(a.payment_method_id.name);
            const typeB = this._getPaymentType(b.payment_method_id.name);
            return typeA === 'C' ? -1 : 1;
        });

        let remainingAmount = 0.00;

        for (const line of paymentLines) {
            const paymentType = this._getPaymentType(line.payment_method_id.name);

            if (paymentType === 'C') {
                const oneCentAdjustment = await this._centRoundingAdjustment(this.currentOrder.lines);
                const paymentAmount = (parseFloat(line.amount.toFixed(2)) + oneCentAdjustment).toFixed(2);
                let paymentText = `\t${paymentType}${paymentAmount}`;
                let cardPaymentResponse;
                try {
                    cardPaymentResponse = await aspa.sendCommand("53", paymentText);
                } catch (error) {
                    console.error(`Error registering ${paymentType} payment line:`, error);
                    await aspa.sendCommand("57", "");
                    throw error;
                }
                const responseValue = cardPaymentResponse.CmdlineResult.split(",")[1];
                const remainingAfterCard = parseFloat(responseValue.replace(/^D\+/, '')) / 100;
                remainingAmount = remainingAfterCard;
            }

            if (paymentType === 'P') {
                const paymentAmount = remainingAmount.toFixed(2);
                let paymentText = `\t${paymentType}${paymentAmount}`;
                try {
                    await aspa.sendCommand("53", paymentText);
                } catch (error) {
                    console.error(`Error registering ${paymentType} payment line:`, error);
                    await aspa.sendCommand("57", "");
                    throw error;
                }
            }


        }
    },

    // cent rounding adjustment
    async _centRoundingAdjustment(orderLines) {
        let oneCentAdjustment = 0.00;

        for (const line of orderLines) {
            if (line.discount > 0) {
                const odooDiscountedPrice = line.get_price_with_tax();
                const expectedPrice = line.get_price_with_tax_before_discount() * (1 - line.discount / 100);

                if (Math.round(odooDiscountedPrice * 100) > Math.floor(expectedPrice * 100)) {
                    console.log("⚠️ Odoo rounded up, but ASPA rounds down. Fixing by subtracting 0.01");
                    oneCentAdjustment -= 0.01;
                } else if (Math.round(odooDiscountedPrice * 100) < Math.floor(expectedPrice * 100)) {
                    console.log("⚠️ Odoo rounded down, but ASPA rounds up. No need to adjust.");
                }
            }
        }

        return oneCentAdjustment;
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
