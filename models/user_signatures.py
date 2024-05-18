# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError
from email.utils import formataddr
import base64
from odoo.tools import is_html_empty, partition, collections, frozendict, lazy_property
from markupsafe import Markup


class UserSignatures(models.Model):
    _name = 'user.signatures'
    _rec_name = 'x_name'

    x_user_id = fields.Many2one('res.users', 'User', store=True, required=True, default=lambda self: self.env.user)
    x_company_id = fields.Many2one('res.company', 'Company', store=True, default=lambda self: self.env.company)
    x_signature = fields.Html(string='Signature', store=True)
    x_name = fields.Char(string='Name', required=True,
                         default=lambda self: f"Signature [{self.env.user.name}/{self.env.company.name}]")
    x_selected = fields.Boolean(string="Selected", default=False, store=True)

    @api.model
    def get_user_signatures(self):
        user_signatures = []
        valid_user_signatures = self.env['user.signatures'].search(
            [('x_user_id', '=', self._uid), ('x_company_id', '=', self.env.company.id)])

        if valid_user_signatures:
            for sig in valid_user_signatures:
                user_signatures.append({
                    'x_name': sig.x_name,
                    'x_signature': sig.x_signature,
                    'x_user_id': sig.x_user_id,
                    'x_company_id': sig.x_company_id,
                    'x_selected': sig.x_selected,
                    'x_sig_id': sig.id
                })
        return user_signatures

    @api.model
    def get_selected_sig(self):
        selected_sig = self.env['user.signatures'].search(
            [('x_user_id', '=', self._uid), ('x_company_id', '=', self.env.company.id), ('x_selected', '=', True)])
        if selected_sig:
            return {
                    'x_name': selected_sig.x_name,
                    'x_signature': selected_sig.x_signature,
                    'x_user_id': selected_sig.x_user_id,
                    'x_company_id': selected_sig.x_company_id,
                    'x_selected': selected_sig.x_selected,
                    'x_sig_id': selected_sig.id
                }
        else:
            return False

class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def _get_user_signature_domain(self):
        return [('x_company_id', '=', self.env.company.id), ('x_user_id', '=', self._uid)]

    x_use_user_signatures = fields.Boolean(string="Use User Signatures", default=False, store=True)
    x_user_signature_id = fields.Many2one('user.signatures', string='User Signature',
                                          domain=_get_user_signature_domain)

    @api.onchange('x_user_signature_id')
    def _onchange_signature(self):
        for user in self:
            if user.x_user_signature_id:
                user.signature = user.x_user_signature_id.x_signature
