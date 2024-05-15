# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError
from email.utils import formataddr
import base64
from odoo.tools import is_html_empty, partition, collections, frozendict, lazy_property
from markupsafe import Markup


class Signatures(models.Model):
    _name = 'nebiz.signatures'

    user_id = fields.Many2one('res.users', 'User', store=True)
    company_id = fields.Many2one('res.company', 'Company', store=True)
    signature = fields.Html(string='Signature', store=True)
    user_name = fields.Char(string='Name', store=True)
    user_mail = fields.Char(string='Email', store=True)
    name = fields.Char(compute='_compute_get_name')
    x_signatures = fields.Char('Firstname')
    active_signature = fields.Boolean(string='Active Signature', store=True, default=False)

    @api.depends('user_name')
    def _compute_get_name(self):
        for rec in self:
            name = ''
            if rec.user_name:
                name = rec.user_name
            self.name = name

    @api.model
    def create(self, vals):
        res = super(Signatures, self).create(vals)
        res.user_id = self._uid
        return res

    # search edit possible only for your own records odoo and write documentation with images

    def unlink(self):
        for rec in self:
            if rec.user_id.id != self._uid:
                raise UserError('You can delete only your own signatures!')
        return super(Signatures, self).unlink()

    def set_signature_active(self):
        signatures = self.search([('company_id', '=', self.company_id.id), ('user_id', '=', self.user_id.id)])
        if signatures:
            for signature in signatures:
                signature.active_signature = False
        self.active_signature = True

    def disable_signature(self):
        signatures = self.search([('company_id', '=', self.company_id.id), ('user_id', '=', self.user_id.id)])
        if signatures:
            for signature in signatures:
                signature.active_signature = False


class Preferences(models.Model):
    _inherit = 'res.users'

    # signature = fields.Html(compute='_compute_signature')

    def _compute_signature(self):
        signature_id = self.env['nebiz.signatures'].search(
            [('company_id', '=', self.company_id.id), ('user_id', '=', self._uid), ('active_signature', '=', True)])
        if signature_id:
            for rec in self:
                rec.signature = signature_id.signature
        else:
            for user in self.filtered(lambda user: user.name and is_html_empty(user.signature)):
                user.signature = Markup('<p>--<br />%s</p>') % user['name']

    @api.onchange('company_id')
    def on_change_state(self):
        signature_id = self.env['nebiz.signatures'].search(
            [('company_id', '=', self.company_id.id), ('user_id', '=', self._uid), ('active_signature', '=', True)])
        if signature_id:
            self.signature = signature_id.signature
        else:
            self.signature = ''

    def get_name(self):
        signature_id = self.env['nebiz.signatures'].search(
            [('user_id', '=', self.id), ('company_id', '=', self.company_id.id), ('active_signature', '=', True)])
        if not signature_id.user_name:
            name = self.display_name
        else:
            name = signature_id.user_name
        return name

    def get_email(self):
        signature_id = self.env['nebiz.signatures'].search(
            [('user_id', '=', self.id), ('company_id', '=', self.company_id.id), ('active_signature', '=', True)])
        if not signature_id.user_mail:
            email = self.email
        else:
            email = signature_id.user_mail
        return email


class ChangeSenderSignature(models.Model):
    _inherit = 'mail.message'

    @api.model
    def _get_default_from(self):
        if self.env.user.get_email():
            return formataddr((self.env.user.get_name(), self.env.user.get_email()))
        raise UserError(_("Unable to send email, please configure the sender's email address."))


class MailTemplateSignature(models.Model):
    _inherit = 'mail.template'

    def generate_email(self, res_ids, fields):
        """Generates an email from the template for given the given model based on
        records given by res_ids.

        :param res_id: id of the record to use for rendering the template (model
                       is taken from template definition)
        :returns: a dict containing all relevant fields for creating a new
                  mail.mail entry, with one extra key ``attachments``, in the
                  format [(report_name, data)] where data is base64 encoded.
        """
        self.ensure_one()
        multi_mode = True
        if isinstance(res_ids, int):
            res_ids = [res_ids]
            multi_mode = False

        results = dict()
        for lang, (template, template_res_ids) in self._classify_per_lang(res_ids).items():
            for field in fields:
                generated_field_values = template._render_field(
                    field, template_res_ids,
                    post_process=(field == 'body_html')
                )
                for res_id, field_value in generated_field_values.items():
                    results.setdefault(res_id, dict())[field] = field_value
            # compute recipients
            if any(field in fields for field in ['email_to', 'partner_to', 'email_cc']):
                results = template.generate_recipients(results, template_res_ids)
            # update values for all res_ids
            for res_id in template_res_ids:
                values = results[res_id]
                if 'body_html' in fields:
                    signature = self.env.user.signature
                    if signature:
                        values['body_html'] = tools.append_content_to_html(values['body_html'], signature,
                                                                           plaintext=False)
                if values.get('body_html'):
                    values['body'] = tools.html_sanitize(values['body_html'])
                # if asked in fields to return, parse generated date into tz agnostic UTC as expected by ORM
                scheduled_date = values.pop('scheduled_date', None)
                if 'scheduled_date' in fields and scheduled_date:
                    parsed_datetime = self.env['mail.mail']._parse_scheduled_datetime(scheduled_date)
                    values['scheduled_date'] = parsed_datetime.replace(tzinfo=None) if parsed_datetime else False

                # technical settings
                values.update(
                    mail_server_id=template.mail_server_id.id or False,
                    auto_delete=template.auto_delete,
                    model=template.model,
                    res_id=res_id or False,
                    attachment_ids=[attach.id for attach in template.attachment_ids],
                )

            # Add report in attachments: generate once for all template_res_ids
            if template.report_template:
                for res_id in template_res_ids:
                    attachments = []
                    report_name = template._render_field('report_name', [res_id])[res_id]
                    report = template.report_template
                    report_service = report.report_name

                    if report.report_type in ['qweb-html', 'qweb-pdf']:
                        result, report_format = self.env['ir.actions.report']._render_qweb_pdf(report, [res_id])
                    else:
                        res = self.env['ir.actions.report']._render(report, [res_id])
                        if not res:
                            raise UserError(_('Unsupported report type %s found.', report.report_type))
                        result, report_format = res

                    # TODO in trunk, change return format to binary to match message_post expected format
                    result = base64.b64encode(result)
                    if not report_name:
                        report_name = 'report.' + report_service
                    ext = "." + report_format
                    if not report_name.endswith(ext):
                        report_name += ext
                    attachments.append((report_name, result))
                    results[res_id]['attachments'] = attachments
                    if not results[res_id]['email_from']:
                        if self.env.user.get_email():
                            results[res_id]['email_from'] = formataddr(
                                (self.env.user.get_name(), self.env.user.get_email()))

        return multi_mode and results or results[res_ids[0]]


class MailWizzardSignature(models.TransientModel):
    _inherit = 'mail.compose.message'

    def _get_default_from(self):
        if self.env.user.get_email():
            return formataddr((self.env.user.get_name(), self.env.user.get_email()))
        raise UserError(_("Unable to send email, please configure the sender's email address."))
