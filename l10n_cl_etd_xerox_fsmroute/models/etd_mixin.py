# Copyright (C) 2019 Open Source Integrators
# Copyright (C) 2019 Serpent Consulting Services Pvt. Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import models


class EtdMixin(models.AbstractModel):

    _inherit = "etd.mixin"

    def _xerox_group_key(self):
        """
        Given a Model record.

        returns a tuple, to use as grouping key.
        """
        key = super()._xerox_group_key()
        # WIP
        if key and hasattr(self, "fsm_order_id"):
            route = self.fsm_order_id.fsm_route_id
            key += route.id
        return key
