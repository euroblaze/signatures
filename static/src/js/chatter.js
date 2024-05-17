/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { clear, insert, link, unlink } from '@mail/model/model_field_command';
import { registerPatch } from "@mail/model/model_core";
import { attr } from '@mail/model/model_field';
import { patch } from "@web/core/utils/patch";
import { Chatter } from "@mail/components/chatter/chatter";

registerPatch({
    name: 'Chatter',
    fields: {
        xIsUserSignature: attr({
            compute() {
                return this.showUserSignature()
            }
        }),
        isUserSignature: attr({
            default: false
        }),
    },
    recordMethods: {
        async showUserSignature() {
            var orm = this.env.services.orm;
            const flag = await orm.call("ir.config_parameter","get_param",['x_user_signatures.permission']).then(result =>{
                if (result == 'True') {
                    return this.update({isUserSignature: true})
                } else {
                    return this.update({isUserSignature: false})
                }
            })
        },
    }
})