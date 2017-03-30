# -*- coding: utf-8 -*-
# Copyright 2014-2015 Akretion - Alexis de Lattre
# Copyright 2017 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Import Paypal Bank Statements',
    'version': '8.0.1.0.0',
    'license': 'AGPL-3',
    'author': 'Akretion, '
              'Tecnativa',
    'website': 'http://www.akretion.com',
    'summary': 'Import Paypal CSV files as Bank Statements in Odoo',
    'depends': [
        'account_bank_statement_import'
    ],
    'external_dependencies': {
        'python': [
            'unicodecsv',
        ],
    },
    'data': [
        # To be included in v9
        # 'wizards/account_bank_statement_import_view.xml',
    ],
    'installable': True,
}
