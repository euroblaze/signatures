from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    x_user_signatures = fields.Boolean(
        config_parameter='x_user_signatures.permission',
        string='User Signatures',
    )