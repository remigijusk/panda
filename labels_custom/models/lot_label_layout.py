# Copyright (C) 2025 devtouch!, UAB
# https://www.devtouch.lt

from odoo import models, fields
from collections import defaultdict


class ProductLabelLayout(models.TransientModel):
    _inherit = 'lot.label.layout'

    print_format = fields.Selection(
        selection_add=[
            ('32x57', '32 x 57mm'),
        ],
        ondelete={'32x57': 'set default'},
    )

    def process(self):
        result = super().process()

        if self.print_format == '32x57':
            if self.label_quantity == 'lots':
                docids = self.move_line_ids.lot_id.ids
                result = self.env.ref('labels_custom.action_report_lot_label_32x57').report_action(docids, config=False)
                result.update({'close_on_report_download': True})

        return result
