# -*- coding: utf-8 -*-
from odoo.addons.mail.controllers.discuss import DiscussController
import logging
from odoo import http
from odoo.exceptions import AccessError, UserError
from odoo.http import request

_logger = logging.getLogger(__name__)


class UserSignatureController(DiscussController):

    @http.route('/mail/message/post', methods=['POST'], type='json', auth='public')
    def mail_message_post(self, thread_model, thread_id, post_data, **kwargs):
        guest = request.env['mail.guest']._get_guest_from_request(request)
        check_access_attachment = guest.env['ir.attachment'].browse(post_data.get('attachment_ids', []))
        if hasattr(check_access_attachment, '_check_attachments_access'):
            guest.env['ir.attachment'].browse(post_data.get('attachment_ids', []))._check_attachments_access(
                post_data.get('attachment_tokens'))
        if thread_model == 'mail.channel':
            channel_member_sudo = request.env['mail.channel.member']._get_as_sudo_from_request_or_raise(
                request=request, channel_id=int(thread_id))
            thread = channel_member_sudo.channel_id
        else:
            thread = request.env[thread_model].browse(int(thread_id)).exists()
        if 'user_signature' in post_data.keys():
            if post_data['user_signature'] != "":
                message_body = post_data['body'] + f"<div>{post_data['user_signature']}</div>"
                post_data['body'] = message_body
                post_data.pop('user_signature')
        return thread.message_post(**{key: value for key, value in post_data.items() if
                                      key in self._get_allowed_message_post_params()}).message_format()[0]
