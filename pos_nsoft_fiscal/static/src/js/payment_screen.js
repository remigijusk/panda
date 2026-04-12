/** @odoo-module */
/* nSoft fiscalization - no frontend patches needed.
   All fiscalization is handled by the Python backend (_process_order).
   nsoft_receipt_id is saved to DB and loaded via _loader_params_pos_order.
   OrderReceipt.xml reads props.data.nsoft_receipt_id directly.
*/
