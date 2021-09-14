# -*- coding: utf-8 -*-
{
    'name': "Signatures",
    'summary': """
        Module for multi-company setups which allows for all mails to be branded from the currently active company's domain.!""",
    'description': """
Signatures
==========
Develop an enterprise 10, 11 compatible module for multi-company setups which allows for all mails to be branded from the currently active company's domain.

Features:

- User can setup specific Signature per company, by going to Signatures which is in the main menu and then choose Add Signature by Company.
- There the user can see all the signatures added so far, as well as add new signatures for themselves for each company available by clicking Create button.
- It won't let you create more than one signature for the same company. Each user can create signatures only for themselves, meaning the current active user.
- Test by going to Preferences (in the main odoo menu) and by choosing the Company -> the field Signature will get the value of the Signature that the selected company has for the currently active user.
- By default the signature field has the value of the currently selected company.
- Everyone has permissions to access this menu (any type of user).
- By selecting company the field signature will automatically change its value according to the table where you have previously entered the signature in 'Signatures by Company' under main menu 'Signatures'.
- Don't forget to click Save when you change the company (and the signature along with it). Signatures field is readonly and can be edited only from the main menu 'Signatures'.
- Effects all Chatter communications.
    """,
    'author': 'Simplify-ERP®',
    'images': 'static/description/icon.png',
    'application': True,
    'category': 'Signatures',
    'version': '0.1',
    'data': [
        'views/config.xml',
        'views/pref.xml',
        'security/ir.model.access.csv'
    ],
    'depends': ['base', 'mail'],
}
