# -*- coding: utf-8 -*-
from odoo.addons.mail.controllers.discuss import DiscussController
from collections import defaultdict
from datetime import datetime, timedelta
from psycopg2 import IntegrityError
from psycopg2.errorcodes import UNIQUE_VIOLATION

from odoo import http
from odoo.exceptions import AccessError, UserError
from odoo.http import request
from odoo.tools import consteq, file_open
from odoo.tools.misc import get_lang
from odoo.tools.translate import _
from werkzeug.exceptions import NotFound


class UserSignatureController(DiscussController):

    @http.route('/mail/message/post', methods=['POST'], type='json', auth='public')
    def mail_message_post(self, thread_model, thread_id, post_data, **kwargs):
        guest = request.env['mail.guest']._get_guest_from_request(request)
        guest.env['ir.attachment'].browse(post_data.get('attachment_ids', []))._check_attachments_access(post_data.get('attachment_tokens'))
        if thread_model == 'mail.channel':
            channel_member_sudo = request.env['mail.channel.member']._get_as_sudo_from_request_or_raise(request=request, channel_id=int(thread_id))
            thread = channel_member_sudo.channel_id
        else:
            thread = request.env[thread_model].browse(int(thread_id)).exists()
        if 'user_signature' in post_data.keys() and post_data['user_signature']:
            message_body = post_data['body'] + f"<div>{post_data['user_signature']}</div>"
            post_data['body'] = message_body
            post_data.pop('user_signature')
        return thread.message_post(**{key: value for key, value in post_data.items() if key in self._get_allowed_message_post_params()}).message_format()[0]