/** @odoo-module **/

//import {registerInstancePatchModel,registerFieldPatchModel} from'@mail/model/model_core';
import { useService } from "@web/core/utils/hooks";
import { clear, insert, insertAndReplace, link, unlink } from '@mail/model/model_field_command';
import { attr, many2many, many2one, one2one } from '@mail/model/model_field';
import { registerPatch } from "@mail/model/model_core";
import '@mail/models/composer_view';


registerPatch({
    name: 'ComposerView',
    recordMethods: {

        async getUserSignatures(){
            const orm = this.env.services.orm;
            const thread = this.composer.thread
            const self = this
            return await orm.call(
                'user.signatures',
                'get_user_signatures',
            ).then(function(result) {
                self.composer.update({selectUserSignatures:result})
            })
        },

        _getMessageData() {
            var res = this._super();
            if (this.chatter.selectedUserSignature) {
                res['user_signature'] = this.chatter.selectedUserSignature['x_signature']
            }
            return res
        },

        async onClickSelectSignature(sig){
            if (sig['x_selected']){
                this.chatter.update({selectedUserSignature: false})
            }else{
                this.chatter.update({selectedUserSignature: sig})
            }
            const mess = await this.messaging.rpc({ route: `/mail/message/signature/select`, params:{user_signature: sig} });
        }
    }
})
