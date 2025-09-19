# -*- coding: utf-8 -*-
import logging
from odoo import http
from odoo.exceptions import AccessError, UserError
from odoo.http import request
from odoo.addons.mail.controllers.thread import ThreadController
from odoo.tools import frozendict
from odoo.addons.mail.models.discuss.mail_guest import add_guest_to_context
from odoo.addons.mail.tools.discuss import Store
from datetime import datetime
from werkzeug.exceptions import NotFound

_logger = logging.getLogger(__name__)


class UserSignatureController(ThreadController):

    @http.route("/mail/message/post", methods=["POST"], type="json", auth="public")
    @add_guest_to_context
    def mail_message_post(self, thread_model, thread_id, post_data, context=None, **kwargs):
        guest = request.env["mail.guest"]._get_guest_from_context()
        guest.env["ir.attachment"].browse(post_data.get("attachment_ids", []))._check_attachments_access(
            kwargs.get("attachment_tokens")
        )
        store = Store()
        request.update_context(message_post_store=store)
        if context:
            request.update_context(**context)
        canned_response_ids = tuple(cid for cid in kwargs.get('canned_response_ids', []) if isinstance(cid, int))
        if canned_response_ids:
            # Avoid serialization errors since last used update is not
            # essential and should not block message post.
            request.env.cr.execute("""
                UPDATE mail_canned_response SET last_used=%(last_used)s
                WHERE id IN (
                    SELECT id from mail_canned_response WHERE id IN %(ids)s
                    FOR NO KEY UPDATE SKIP LOCKED
                )
            """, {
                'last_used': datetime.now(),
                'ids': canned_response_ids,
            })
        thread = request.env[thread_model]._get_thread_with_access(
            thread_id, mode=request.env[thread_model]._mail_post_access, **kwargs
        )
        if not thread:
            raise NotFound()
        if not request.env[thread_model]._get_thread_with_access(thread_id, "write"):
            thread.env.context = frozendict(
                thread.env.context, mail_create_nosubscribe=True, mail_post_autofollow=False
            )
        
        # Handle user signature if present
        if 'user_signature' in post_data and post_data['user_signature']:
            message_body = post_data.get('body', '') + f"<div>{post_data['user_signature']}</div>"
            post_data['body'] = message_body
            post_data.pop('user_signature')

        post_data = {
                key: value
                for key, value in post_data.items()
                if key in thread._get_allowed_message_post_params()
            }

        # sudo: mail.thread - users can post on accessible threads
        message = thread.sudo().message_post(**self._prepare_post_data(post_data, thread, **kwargs))
        return store.add(message, for_current_user=True).get_result()
