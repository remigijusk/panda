# Copyright (C) 2025 devtouch!, UAB
# https://www.devtouch.lt

from odoo import models, fields
from collections import defaultdict


class ProductLabelLayout(models.TransientModel):
    _inherit = 'lot.label.layout'

    print_format = fields.Selection(
        selection_add=[
            ('32x57', 'Custom 32 x 57mm'),
        ],
        ondelete={'32x57': 'set default'},
    )

    def process(self):
        result = super().process()

        if self.print_format == '32x57':
            if self.label_quantity == 'lots':
                docids = self.move_line_ids.lot_id.ids
            else:
                uom_categ_unit = self.env.ref('uom.product_uom_categ_unit')
                quantity_by_lot = defaultdict(int)
                for move_line in self.move_line_ids:
                    if not move_line.lot_id:
                        continue
                    if move_line.product_uom_id.category_id == uom_categ_unit:
                        quantity_by_lot[move_line.lot_id.id] += int(move_line.quantity)
                    else:
                        quantity_by_lot[move_line.lot_id.id] += 1
                docids = []
                for lot_id, qty in quantity_by_lot.items():
                    docids.extend([lot_id] * qty)
            result = self.env.ref('labels_custom.action_report_lot_label_32x57').report_action(docids, config=False)
            result.update({'close_on_report_download': True})

        return result
