# -*- coding: utf-8 -*-
# Copyright 2014-2015 Akretion - Alexis de Lattre
# Copyright 2017 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime
from openerp import _, api, fields, models
from openerp.exceptions import Warning as UserError
import re
from cStringIO import StringIO


class AccountBankStatementImport(models.TransientModel):
    _inherit = 'account.bank.statement.import'

    @api.model
    def _prepare_paypal_encoding(self):
        """This method is designed to be inherited"""
        return 'utf-8'

    @api.model
    def _prepare_paypal_date_format(self):
        """This method is designed to be inherited"""
        return '%d/%m/%Y'

    @api.model
    def _valid_paypal_line(self, line):
        """This method is designed to be inherited"""
        return line[4].startswith('Pago') or line[4].startswith('Reembolso')

    @api.model
    def _paypal_convert_amount(self, amount_str):
        '''This method is designed to be inherited'''
        valstr = re.sub(r'[^\d,.-]', '', amount_str)
        valstrdot = valstr.replace('.', '')
        valstrdot = valstrdot.replace(',', '.')
        return float(valstrdot)

    @api.model
    def _check_paypal(self, data_file):
        """This method is designed to be inherited"""
        return data_file.startswith('"Fecha",')

    @api.model
    def _parse_file(self, data_file):
        """ Import a file in Paypal CSV format"""
        paypal = self._check_paypal(data_file)
        if not paypal:
            return super(AccountBankStatementImport, self)._parse_file(
                data_file
            )
        f = StringIO()
        f.write(data_file)
        f.seek(0)
        transactions = []
        i = 0
        start_balance = end_balance = start_date_str = end_date_str = False
        company_currency_name = self.env.user.company_id.currency_id.name
        commission_total = 0.0
        raw_lines = []
        import unicodecsv
        for line in unicodecsv.reader(
                f, encoding=self._prepare_paypal_encoding()):
            i += 1
            if i == 1 or not line or not self._valid_paypal_line(line):
                continue
            date_dt = datetime.strptime(
                line[0], self._prepare_paypal_date_format()
            )
            rline = {
                'date': fields.Date.to_string(date_dt),
                'currency': line[6],
                'partner_email': line[10],
                'owner_name': line[3],
                'amount': line[7],
                'commission': line[8],
                'balance': line[29],
                'transac_ref': line[25],
                'ref': line[12],
                'line_nr': i,
            }
            name_list = [line[3]]
            if line[16]:
                name_list.append(line[16])
            if line[17]:
                name_list.append(line[17])
            rline['name'] = ' - '.join(name_list)
            for field in ['commission', 'amount', 'balance']:
                try:
                    rline[field] = self._paypal_convert_amount(rline[field])
                except:
                    raise UserError(
                        _("Value '%s' for the field '%s' on line %d, "
                            "cannot be converted to float")
                        % (rline[field], field, i))
            raw_lines.append(rline)
        # Second pass to sort out the lines in other currencies
        final_lines = []
        other_currency_line = {}
        for wline in raw_lines:
            if company_currency_name != wline['currency']:
                if not wline['transac_ref'] and not other_currency_line:
                    currencies = self.env['res.currency'].search(
                        [('name', '=', wline['currency'])])
                    if not currencies:
                        raise UserError(
                            _('Currency %s on line %d cannot be found in Odoo')
                            % (wline['currency'], wline['line_nr']))
                    other_currency_line = {
                        'amount_currency': wline['amount'],
                        'currency_id': currencies[0].id,
                        'currency': wline['currency'],
                        'name': wline['name'],
                        'owner_name': wline['owner_name'],
                        }
                if wline['transac_ref'] and other_currency_line:
                    assert (
                        wline['currency'] == other_currency_line['currency']),\
                        'WRONG currency'
                    assert (
                        wline['amount'] ==
                        other_currency_line['amount_currency'] * -1),\
                        'WRONG amount %s vs %s' % (wline.get('amount'),
                                                   other_currency_line.get(
                                                       'amount_currency'))
                    other_currency_line['transac_ref'] = wline['transac_ref']
            else:
                if (other_currency_line and
                        wline['transac_ref'] ==
                        other_currency_line.get('transac_ref', '')):
                    wline.update(other_currency_line)
                    # reset other_currency_line
                    other_currency_line = {}
                final_lines.append(wline)
        j = 0
        for fline in final_lines:
            j += 1
            commission_total += fline['commission']
            if j == 1:
                start_date_str = fline['date']
                start_balance = fline['balance'] - fline['amount']
            end_date_str = fline['date']
            end_balance = fline['balance']
            partner = self.env['res.partner']
            if fline['partner_email']:
                partner = self.env['res.partner'].search(
                    [('email', '=', fline['partner_email'])], limit=1,
                )
                partner = partner.commercial_partner_id
            vals_line = {
                'date': fline['date'],
                'name': fline['ref'],
                'ref': fline['name'],
                'unique_import_id': fline['ref'],
                'amount': fline['amount'],
                'partner_id': partner.id,
                'bank_account_id': False,
                'currency_id': fline.get('currency_id'),
                'amount_currency': fline.get('amount_currency'),
            }
            transactions.append(vals_line)
        if commission_total:
            commission_line = {
                'date': end_date_str,
                'name': _('Paypal commissions'),
                'ref': _('PAYPAL-COSTS'),
                'amount': commission_total,
                'unique_import_id': False,
            }
            transactions.append(commission_line)
        vals_bank_statement = {
            'name': _('PayPal Import %s > %s')
            % (start_date_str, end_date_str),
            'balance_start': start_balance,
            'balance_end_real': end_balance,
            'transactions': transactions,
        }
        return None, None, [vals_bank_statement]
