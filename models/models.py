# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools
from odoo.exceptions import UserError, ValidationError
from email.utils import formataddr
import base64

class Signatures(models.Model):
    _name = 'nebiz.signatures'

    user_id = fields.Many2one('res.users', 'User', store=True)
    company_id = fields.Many2one('res.company', 'Company', store=True)
    signature = fields.Html(string='Signature', store=True)
    user_name=fields.Char(string='Name',store=True)
    user_mail=fields.Char(string='Email',store=True)
    name = fields.Char(compute='get_name')
    x_signatures = fields.Char('Firstname')
    active_signature=fields.Boolean(string='Active Signature',store=True,default=False)

    @api.one
    def get_name(self):
        self.name = self.user_name

    @api.model
    def create(self, vals):
        res = super(Signatures, self).create(vals)
        res.user_id = self._uid
        return res

    # search edit possible only for your own records odoo and write documentation with images

    @api.multi
    def unlink(self):
        for id in self:
            if id.user_id.id != self._uid:
                raise UserError('You can delete only your own signatures!')
        return super(Signatures,self).unlink()

    @api.multi
    def set_signature_active(self):
        signatures=self.search([('company_id','=',self.company_id.id),('user_id','=',self.user_id.id)])
        for signature in signatures:
            signature.active_signature=False
        self.active_signature=True

    @api.multi
    def disable_signature(self):
        signatures=self.search([('company_id','=',self.company_id.id),('user_id','=',self.user_id.id)])
        for signature in signatures:
            signature.active_signature=False


class Preferences(models.Model):
    _inherit = 'res.users'

    signature = fields.Html(compute='get_signature')

    @api.one
    def get_signature(self):
        rec = self.env['nebiz.signatures'].search(
            [('company_id', '=', self.company_id.id), ('user_id', '=', self._uid),('active_signature','=',True)])
        self.signature = rec.signature

    @api.onchange('company_id')
    def on_change_state(self):
        rec = self.env['nebiz.signatures'].search(
            [('company_id', '=', self.company_id.id), ('user_id', '=', self._uid),('active_signature','=',True)])
        if rec:
            self.signature = rec.signature
        else:
            self.signature = ''

    def get_name(self):
        signature = self.env['nebiz.signatures'].search([('user_id','=',self.id),('company_id','=',self.company_id.id),('active_signature','=',True)])
        if signature.user_name == False:
            name=self.display_name
        else:
            name=signature.user_name
        return name

    def get_email(self):
        signature = self.env['nebiz.signatures'].search([('user_id','=',self.id),('company_id','=',self.company_id.id),('active_signature','=',True)])
        if signature.user_name == False:
            email=self.email
        else:
            email=signature.user_mail
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

    def generate_email(self, res_ids, fields=None):
        """Generates an email from the template for given the given model based on
        records given by res_ids.

        :param template_id: id of the template to render.
        :param res_id: id of the record to use for rendering the template (model
                       is taken from template definition)
        :returns: a dict containing all relevant fields for creating a new
                  mail.mail entry, with one extra key ``attachments``, in the
                  format [(report_name, data)] where data is base64 encoded.
        """
        self.ensure_one()
        multi_mode = True
        if isinstance(res_ids, (int, long)):
            res_ids = [res_ids]
            multi_mode = False
        if fields is None:
            fields = ['subject', 'body_html', 'email_from', 'email_to', 'partner_to', 'email_cc', 'reply_to', 'scheduled_date']

        res_ids_to_templates = self.get_email_template(res_ids)

        # templates: res_id -> template; template -> res_ids
        templates_to_res_ids = {}
        for res_id, template in res_ids_to_templates.iteritems():
            templates_to_res_ids.setdefault(template, []).append(res_id)

        results = dict()
        for template, template_res_ids in templates_to_res_ids.iteritems():
            Template = self.env['mail.template']
            # generate fields value for all res_ids linked to the current template
            if template.lang:
                Template = Template.with_context(lang=template._context.get('lang'))
            for field in fields:
                Template = Template.with_context(safe=field in {'subject'})
                generated_field_values = Template.render_template(
                    getattr(template, field), template.model, template_res_ids,
                    post_process=(field == 'body_html'))
                for res_id, field_value in generated_field_values.iteritems():
                    results.setdefault(res_id, dict())[field] = field_value
            # compute recipients
            if any(field in fields for field in ['email_to', 'partner_to', 'email_cc']):
                results = template.generate_recipients(results, template_res_ids)
            # update values for all res_ids
            for res_id in template_res_ids:
                values = results[res_id]
                # body: add user signature, sanitize
                if 'body_html' in fields and template.user_signature:
                    signature = self.env.user.signature
                    if signature:
                        values['body_html'] = tools.append_content_to_html(values['body_html'], signature, plaintext=False)
                if values.get('body_html'):
                    values['body'] = tools.html_sanitize(values['body_html'])
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
                    report_name = self.render_template(template.report_name, template.model, res_id)
                    report = template.report_template
                    report_service = report.report_name

                    if report.report_type in ['qweb-html', 'qweb-pdf']:
                        result, format = Template.env['report'].get_pdf([res_id], report_service), 'pdf'
                    else:
                        result, format = odoo_report.render_report(self._cr, self._uid, [res_id], report_service, {'model': template.model}, Template._context)

                    # TODO in trunk, change return format to binary to match message_post expected format
                    result = base64.b64encode(result)
                    if not report_name:
                        report_name = 'report.' + report_service
                    ext = "." + format
                    if not report_name.endswith(ext):
                        report_name += ext
                    attachments.append((report_name, result))
                    results[res_id]['attachments'] = attachments
                    if not results[res_id]['email_from']:
                        if self.env.user.get_email():
                            results[res_id]['email_from'] = formataddr((self.env.user.get_name(), self.env.user.get_email()))

        return multi_mode and results or results[res_ids[0]]

class MailWizzardSignature(models.TransientModel):
    _inherit = 'mail.compose.message'

    def _get_default_from(self):
        if self.env.user.get_email():
            return formataddr((self.env.user.get_name(), self.env.user.get_email()))
        raise UserError(_("Unable to send email, please configure the sender's email address."))

    @api.multi
    def get_mail_values(self, res_ids):
        """Generate the values that will be used by send_mail to create mail_messages
        or mail_mails. """
        self.ensure_one()
        results = dict.fromkeys(res_ids, False)
        rendered_values = {}
        mass_mail_mode = self.composition_mode == 'mass_mail'
        # render all template-based value at once
        if mass_mail_mode and self.model:
            rendered_values = self.render_message(res_ids)
        # compute alias-based reply-to in batch
        reply_to_value = dict.fromkeys(res_ids, None)
        if mass_mail_mode and not self.no_auto_thread:
            # reply_to_value = self.env['mail.thread'].with_context(thread_model=self.model).browse(res_ids).message_get_reply_to(default=self.email_from)
            reply_to_value = self.env['mail.thread'].with_context(thread_model=self.model).message_get_reply_to(res_ids,
                                                                                                                default=self.email_from)
        for res_id in res_ids:
            # static wizard (mail.message) values
            mail_values = {
                'subject': self.subject,
                'body': self.body or '',
                'parent_id': self.parent_id and self.parent_id.id,
                'partner_ids': [partner.id for partner in self.partner_ids],
                'attachment_ids': [attach.id for attach in self.attachment_ids],
                'author_id': self.author_id.id,
                'email_from': self._get_default_from(),
                'record_name': self.record_name,
                'no_auto_thread': self.no_auto_thread,
                'mail_server_id': self.mail_server_id.id,
            }

            # mass mailing: rendering override wizard static values
            if mass_mail_mode and self.model:
                if self.model in self.env and hasattr(self.env[self.model], 'message_get_email_values'):
                    mail_values.update(self.env[self.model].browse(res_id).message_get_email_values())
                # keep a copy unless specifically requested, reset record name (avoid browsing records)
                mail_values.update(notification=not self.auto_delete_message, model=self.model, res_id=res_id,
                                   record_name=False)
                # auto deletion of mail_mail
                if self.auto_delete or self.template_id.auto_delete:
                    mail_values['auto_delete'] = True
                # rendered values using template
                email_dict = rendered_values[res_id]
                mail_values['partner_ids'] += email_dict.pop('partner_ids', [])
                mail_values.update(email_dict)
                if not self.no_auto_thread:
                    mail_values.pop('reply_to')
                    if reply_to_value.get(res_id):
                        mail_values['reply_to'] = reply_to_value[res_id]
                if self.no_auto_thread and not mail_values.get('reply_to'):
                    mail_values['reply_to'] = mail_values['email_from']
                # mail_mail values: body -> body_html, partner_ids -> recipient_ids
                mail_values['body_html'] = mail_values.get('body', '')
                mail_values['recipient_ids'] = [(4, id) for id in mail_values.pop('partner_ids', [])]

                # process attachments: should not be encoded before being processed by message_post / mail_mail create
                mail_values['attachments'] = [(name, base64.b64decode(enc_cont)) for name, enc_cont in
                                              email_dict.pop('attachments', list())]
                attachment_ids = []
                for attach_id in mail_values.pop('attachment_ids'):
                    new_attach_id = self.env['ir.attachment'].browse(attach_id).copy(
                        {'res_model': self._name, 'res_id': self.id})
                    attachment_ids.append(new_attach_id.id)
                mail_values['attachment_ids'] = self.env['mail.thread']._message_preprocess_attachments(
                    mail_values.pop('attachments', []),
                    attachment_ids, 'mail.message', 0)
            results[res_id] = mail_values
        return results