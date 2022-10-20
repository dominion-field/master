from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    liquidation_location_id = fields.Many2one('stock.location', 'Liquidation location',
                                              config_parameter="i_plus_m.liquidation_location_id")

    