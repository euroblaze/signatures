/** @odoo-module **/

import { attr, many2many, many2one, one2many, one2one } from '@mail/model/model_field';
import { clear, replace, unlink } from '@mail/model/model_field_command';
import { registerPatch } from "@mail/model/model_core";
import { useService } from "@web/core/utils/hooks";
import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { sprintf } from '@web/core/utils/strings';
import { getMessagingComponent } from "@mail/utils/messaging_component";

registerPatch({
    name:'Composer',
    fields: {
        selectUserSignatures: attr(),
    },
})

if (!getMessagingComponent("Dropdown") && !getMessagingComponent("DropdownItem")) {
    registerMessagingComponent(Dropdown)
    registerMessagingComponent(DropdownItem)
}
