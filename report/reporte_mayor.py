# -*- coding: utf-8 -*-
from odoo import models, api
from odoo.release import version_info
import logging

class ReporteDiario(models.AbstractModel):
    _inherit = 'report.l10n_gt_extra.reporte_mayor'
    
    def lineas(self, datos):
        totales = {}
        lineas_resumidas = {}
        lineas=[]
        totales['debe'] = 0
        totales['haber'] = 0
        totales['saldo_inicial'] = 0
        totales['saldo_final'] = 0

        account_ids = [x for x in datos['cuentas_id']]
        movimientos = self.env['account.move.line'].search([
            ('account_id','in',account_ids),
            ('parent_state','=','posted'),
            ('date','<=',datos['fecha_hasta']),
            ('date','>=',datos['fecha_desde'])])

        if version_info[0] in [13, 14, 15]:
            include_initial_balance = 't.include_initial_balance'
            join_initial_balance = 'join account_account_type t on (t.id = a.user_type_id)'
        else:
            include_initial_balance = 'a.include_initial_balance'
            join_initial_balance = ''

        accounts_str = ','.join([str(x) for x in datos['cuentas_id']])
        if datos['agrupado_por_dia']:
            
            self.env.cr.execute('select a.id, a.code as codigo, a.name as cuenta, l.id as move_line_id, l.move_name as asiento_contable, l.name as descripcion, l.date as fecha, ' + include_initial_balance + ' as balance_inicial, sum(l.debit) as debe, sum(l.credit) as haber ' \
                'from account_move_line l join account_account a on(l.account_id = a.id)' \
                + join_initial_balance + \
                'where l.parent_state = \'posted\' and a.id in ('+accounts_str+') and l.date >= %s and l.date <= %s group by a.id, a.code, a.name, l.id, l.move_name, l.name, l.date, ' + include_initial_balance + ' ORDER BY l.date, a.code',
            (datos['fecha_desde'], datos['fecha_hasta']))

            for r in self.env.cr.dictfetchall():
                totales['debe'] += r['debe']
                totales['haber'] += r['haber']
                linea = {
                    'id': r['id'],
                    'fecha': r['fecha'],
                    'asiento_contable': r['asiento_contable'],
                    'descripcion': r['descripcion'],
                    'codigo': r['codigo'],
                    'cuenta': r['cuenta'],
                    'saldo_inicial': 0,
                    'debe': r['debe'],
                    'haber': r['haber'],
                    'saldo_final': 0,
                    'balance_inicial': r['balance_inicial']
                }
                lineas.append(linea)

            cuentas_agrupadas = {}
            llave = 'codigo'
            for l in lineas:
                if l[llave] not in cuentas_agrupadas:
                    cuentas_agrupadas[l[llave]] = {
                        'codigo': l[llave],
                        'cuenta': l['cuenta'],
                        'saldo_inicial': 0,
                        'saldo_final': 0,
                        'fechas': [],
                        'total_debe': 0,
                        'total_haber': 0
                    }

                    if not l['balance_inicial']:
                        cuentas_agrupadas[l[llave]]['saldo_inicial'] = self.retornar_saldo_inicial_inicio_anio(l['id'], datos['fecha_desde'])
                    else:
                        cuentas_agrupadas[l[llave]]['saldo_inicial'] = saldo = self.retornar_saldo_inicial_todos_anios(l['id'], datos['fecha_desde'])
                cuentas_agrupadas[l[llave]]['fechas'].append(l)

            for cuenta in cuentas_agrupadas.values():
                for fecha in cuenta['fechas']:
                    cuenta['total_debe'] += fecha['debe']
                    cuenta['total_haber'] += fecha['haber']
                cuenta['saldo_final'] += cuenta['saldo_inicial'] + cuenta['total_debe'] - cuenta['total_haber']

            lineas = sorted(cuentas_agrupadas.values(), key=lambda l: l['codigo'])
            logging.warning(lineas)
        else:

            self.env.cr.execute('select a.id, a.code as codigo, a.name as cuenta, ' + include_initial_balance + ' as balance_inicial, sum(l.debit) as debe, sum(l.credit) as haber ' \
            	'from account_move_line l join account_account a on(l.account_id = a.id)' \
            	+ join_initial_balance + \
            	'where l.parent_state = \'posted\' and a.id in ('+accounts_str+') and l.date >= %s and l.date <= %s group by a.id, a.code, a.name, ' + include_initial_balance + ' ORDER BY a.code',
            (datos['fecha_desde'], datos['fecha_hasta']))

            for r in self.env.cr.dictfetchall():
                totales['debe'] += r['debe']
                totales['haber'] += r['haber']
                linea = {
                    'id': r['id'],
                    'codigo': r['codigo'],
                    'cuenta': r['cuenta'],
                    'saldo_inicial': 0,
                    'debe': r['debe'],
                    'haber': r['haber'],
                    'saldo_final': 0,
                    'balance_inicial': r['balance_inicial']
                }
                lineas.append(linea)

            for l in lineas:
                if not l['balance_inicial']:
                    l['saldo_inicial'] += self.retornar_saldo_inicial_inicio_anio(l['id'], datos['fecha_desde'])
                    l['saldo_final'] += l['saldo_inicial'] + l['debe'] - l['haber']
                    totales['saldo_inicial'] += l['saldo_inicial']
                    totales['saldo_final'] += l['saldo_final']
                else:
                    l['saldo_inicial'] += self.retornar_saldo_inicial_todos_anios(l['id'], datos['fecha_desde'])
                    l['saldo_final'] += l['saldo_inicial'] + l['debe'] - l['haber']
                    totales['saldo_inicial'] += l['saldo_inicial']
                    totales['saldo_final'] += l['saldo_final']

        return {'lineas': lineas,'totales': totales }