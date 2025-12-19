# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class UserSignatures(models.Model):
    _name = 'user.signatures'
    _description = 'User Signatures'
    _rec_name = 'x_name'
    _sql_constraints = [
        ('unique_employee_company_signature',
         'UNIQUE (x_employee_id, x_company_id)',
         'An employee can only have one signature per company!')
    ]

    x_employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        default=lambda self: self.env.user.employee_id,
        help="Employee who owns this signature"
    )
    x_company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        help="Company for which this signature is used"
    )
    x_signature = fields.Html(
        string='Signature',
        help="HTML signature content"
    )
    x_name = fields.Char(
        string='Name',
        required=True,
        default=lambda self: f"Signature [{self.env.company.name}]",
        help="Display name for this signature"
    )
    x_selected = fields.Boolean(
        string="Selected",
        default=False,
        help="Whether this signature is currently selected for use"
    )

    @api.model
    def get_user_signatures(self):
        user_signatures = []
        employee = self.env.user.employee_id
        if not employee:
            return user_signatures
        valid_user_signatures = self.env['user.signatures'].search(
            [('x_employee_id', '=', employee.id), ('x_company_id', 'in', self.env.context.get('allowed_company_ids'))])

        if valid_user_signatures:
            for sig in valid_user_signatures:
                user_signatures.append({
                    'x_name': sig.x_name,
                    'x_signature': sig.x_signature,
                    'x_employee_id': sig.x_employee_id,
                    'x_company_id': sig.x_company_id,
                    'x_selected': sig.x_selected,
                    'x_sig_id': sig.id
                })
        return user_signatures

    @api.model
    def get_selected_sig(self):
        employee = self.env.user.employee_id
        if not employee:
            return False
        selected_sig = self.env['user.signatures'].search(
            [('x_employee_id', '=', employee.id), ('x_company_id', 'in', self.env.context.get('allowed_company_ids')), ('x_selected', '=', True)])
        if len(selected_sig) > 1:
            selected_sig = self.env['user.signatures'].search(
                [('x_employee_id', '=', employee.id), ('x_company_id', '=', self.env.user.company_id.id),
                 ('x_selected', '=', True)], limit=1)
        if selected_sig:
            return {
                    'x_name': selected_sig.x_name,
                    'x_signature': selected_sig.x_signature,
                    'x_employee_id': selected_sig.x_employee_id,
                    'x_company_id': selected_sig.x_company_id,
                    'x_selected': selected_sig.x_selected,
                    'x_sig_id': selected_sig.id
                }
        else:
            return False

    def mail_signature_select(self, user_signature):
        sig_id = user_signature['x_sig_id']
        employee = self.env.user.employee_id
        if not employee:
            return False
        reset_user_signatures = self.env['user.signatures'].search(
            [('x_employee_id', '=', employee.id), ('x_company_id', 'in', self.env.context.get('allowed_company_ids')), ('id', '!=', int(sig_id))])
        selected_user_signature = self.env['user.signatures'].browse(int(sig_id))
        if selected_user_signature.x_selected:
            selected_user_signature.x_selected = False
            return selected_user_signature
        selected_user_signature.x_selected = True
        for sig in reset_user_signatures:
            sig.x_selected = False

        return selected_user_signature

class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def _get_user_signature_domain(self):
        employee = self.env.user.employee_id
        return [
            ('x_company_id', 'in', self.env.context.get('allowed_company_ids', [])),
            ('x_employee_id', '=', employee.id if employee else False)
        ]

    x_use_user_signatures = fields.Boolean(
        string="Use User Signatures",
        compute="_compute_use_user_signture",
        help="Enable custom signature management per company"
    )
    x_user_signature_id = fields.Many2one(
        'user.signatures',
        string='User Signature',
        domain=_get_user_signature_domain,
        help="Select signature for current company"
    )

    @api.onchange('x_user_signature_id')
    def _onchange_signature(self):
        """Update user signature when signature is selected"""
        for user in self:
            if user.x_user_signature_id:
                user.signature = user.x_user_signature_id.x_signature

    def _compute_use_user_signture(self):
        config_enabled = self.env['ir.config_parameter'].sudo().get_param('x_user_signatures.permission', False)
        for user in self:
            user['x_use_user_signatures'] = config_enabled and bool(user.employee_ids)