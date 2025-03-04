/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import ASPAIntegration from "./aspa_api";
import { onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

const aspaIntegration = new ASPAIntegration();

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
                const orderLines = order.orderlines.models || order.orderlines;
                let posReference;
                for (const line of orderLines) {
                    const originOrder = await this.orm.call("pos.order", "search_read", [
                        [["lines", "in", line.refunded_orderline_id]],
                        ["pos_reference"],
                    ]);

                    if (originOrder.length > 0) {
                        posReference = originOrder[0].pos_reference;
                    } else {
                        console.error("No order found containing the refunded line ID:", line.refunded_orderline_id);
                    }
                }
                const tillNumber = "1";
                const receiptNumber = posReference.split("Aspa Receipt:")[1]?.trim();
                if (!receiptNumber) {
                    console.error("Previous receipt number is missing for return order.");
                    throw new Error("Missing previous receipt number for return.");
                }

                const returnCommand = `G,${tillNumber},${receiptNumber}`;
                await aspaIntegration.sendCommand("48", returnCommand);
            } else {
                await aspaIntegration.sendCommand("48", "");
            }
        } catch (error) {
            throw error;
        }
    },

    // register products
    async _registerProducts() {
        const order = this.pos.get_order();
        if (order) {
            const orderLines = order.lines.models || order.lines;
            for (const line of orderLines) {
                const product = line.product_id;
                const quantity = line.qty
                const taxLetter = product.is_deposit ? "N" : "A";
                const vatAmount = line.price_unit * quantity * (line.tax_ids[0].amount / 100);
                const unitPrice = (line.price_subtotal + vatAmount) / quantity;
                const formattedPrice = unitPrice.toFixed(3);
                const parameter = `${product.display_name}\t${taxLetter}${quantity}*${formattedPrice}`;
                try {
                    await aspaIntegration.sendCommand("49", parameter);
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

        // Check if there's a card payment and call BankasSale0 before fiscal receipt
        let cardPaymentSuccess = true;
        for (const line of paymentLines) {
            const paymentType = this._getPaymentType(line.payment_method_id.name);
            if (paymentType === 'C') {
                try {
                    const bankasResponse = await aspaIntegration.sendBankas0({ amount: line.amount.toFixed(2) });
                    console.log("BankasSale0 response:", bankasResponse);
                    if (!bankasResponse || !bankasResponse.BankasSale0Result.startsWith("OK")) {
                        console.error("Bank card payment failed:", bankasResponse);
                        cardPaymentSuccess = false;
                        break;
                    }
                } catch (error) {
                    console.error("Error processing BankasSale0:", error);
                    cardPaymentSuccess = false;
                    break;
                }
            }
        }

        if (!cardPaymentSuccess) {
            throw new Error("Bank card payment unsuccessful. Transaction aborted.");
        }

        // Register payments
        if (paymentLines && paymentLines.length > 0) {
            for (const line of paymentLines) {
                if (line.amount) {
                    const paymentType = this._getPaymentType(line.payment_method_id.name);
                    let paymentText = `\t${paymentType}${line.amount}`;
                    if (line.amount == order.get_total_with_tax().toFixed(2) && paymentType === 'P') {
                        paymentText = "";
                    }
                    try {
                        await aspaIntegration.sendCommand("53", paymentText);
                    } catch (error) {
                        console.error("Error registering payment line:", error);
                        throw error;
                    }
                }
            }
        }

        // Finalize fiscal receipt
        try {
            const response = await aspaIntegration.sendCommand("56", "");
            receiptNumber = response.CmdlineResult.split(",")[1];
        } catch (error) {
            console.error("Error finalizing fiscal receipt:", error);
            throw error;
        }

        const finalized = await super._finalizeValidation();
        if (order && order.server_id) {
            await this.orm.call("pos.order", "update_pos_reference", [
                [order.server_id],
                `Aspa Receipt:${receiptNumber}`,
            ]);
        }
        return finalized;
    },

    _getPaymentType(paymentMethod) {
        switch (paymentMethod) {
            case 'Cash':
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
