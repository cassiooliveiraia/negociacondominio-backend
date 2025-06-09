from decimal import Decimal
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from src.models.database import db, Charge, ChargeItem, ChargeFees, CalculationParameter
import uuid

class ChargeCalculatorService:
    """
    Serviço para cálculo de débitos conforme estrutura corrigida:
    1. Débito Principal (correção + juros + multa por item)
    2. Despesas de Cobrança (correção + juros por item)
    3. Subtotal Base = Principal + Despesas
    4. Honorários Extrajudiciais = % ou fixo sobre Principal
    5. Honorários Execução = % ou fixo sobre Principal  
    6. Subtotal com Honorários = Base + Honorários
    7. Multa Art. 523 = % sobre Subtotal com Honorários
    8. TOTAL = Subtotal + Multa 523
    """
    
    def __init__(self):
        self.calculation_date = date.today()
    
    def calculate_charge(self, charge_id):
        """Calcula todos os valores de uma cobrança"""
        try:
            charge = Charge.query.get(charge_id)
            if not charge:
                raise ValueError("Cobrança não encontrada")
            
            # Buscar parâmetros de cálculo do cliente
            params = self._get_calculation_parameters(charge.client_id)
            
            # 1. Calcular itens individuais
            principal_total = self._calculate_charge_items(charge_id, 'PRINCIPAL', params)
            expenses_total = self._calculate_charge_items(charge_id, 'COLLECTION_EXPENSES', params)
            
            # 2. Subtotal base
            subtotal_base = principal_total + expenses_total
            
            # 3. Calcular honorários sobre o principal apenas
            extrajudicial_fees = self._calculate_fees(charge_id, 'EXTRAJUDICIAL', principal_total, params)
            execution_fees = self._calculate_fees(charge_id, 'EXECUTION', principal_total, params)
            
            # 4. Subtotal com honorários
            subtotal_with_fees = subtotal_base + extrajudicial_fees + execution_fees
            
            # 5. Multa Art. 523 sobre tudo
            art_523_fine = self._calculate_art_523_fine(subtotal_with_fees, params)
            
            # 6. Total final
            total_amount = subtotal_with_fees + art_523_fine
            
            # Atualizar cobrança
            charge.principal_amount = principal_total
            charge.expenses_amount = expenses_total
            charge.extrajudicial_fees = extrajudicial_fees
            charge.execution_fees = execution_fees
            charge.art_523_fine = art_523_fine
            charge.total_amount = total_amount
            charge.balance_amount = total_amount - charge.paid_amount
            
            db.session.commit()
            
            return {
                'principal_amount': float(principal_total),
                'expenses_amount': float(expenses_total),
                'subtotal_base': float(subtotal_base),
                'extrajudicial_fees': float(extrajudicial_fees),
                'execution_fees': float(execution_fees),
                'subtotal_with_fees': float(subtotal_with_fees),
                'art_523_fine': float(art_523_fine),
                'total_amount': float(total_amount),
                'balance_amount': float(charge.balance_amount)
            }
            
        except Exception as e:
            db.session.rollback()
            raise e
    
    def _get_calculation_parameters(self, client_id):
        """Busca parâmetros de cálculo vigentes para o cliente"""
        params = CalculationParameter.query.filter(
            CalculationParameter.client_id == client_id,
            CalculationParameter.is_active == True,
            CalculationParameter.start_date <= self.calculation_date
        ).filter(
            (CalculationParameter.end_date.is_(None)) | 
            (CalculationParameter.end_date >= self.calculation_date)
        ).first()
        
        if not params:
            # Parâmetros padrão se não encontrar
            return {
                'fine_rate': Decimal('2.0'),
                'interest_rate': Decimal('1.0'),
                'extrajudicial_fees_rate': Decimal('10.0'),
                'execution_fees_rate': Decimal('10.0'),
                'art_523_fine_rate': Decimal('10.0'),
                'correction_index': 'INPC'
            }
        
        return {
            'fine_rate': params.fine_rate,
            'interest_rate': params.interest_rate,
            'extrajudicial_fees_rate': params.extrajudicial_fees_rate,
            'execution_fees_rate': params.execution_fees_rate,
            'art_523_fine_rate': params.art_523_fine_rate,
            'correction_index': params.correction_index
        }
    
    def _calculate_charge_items(self, charge_id, category, params):
        """Calcula itens de uma categoria específica"""
        items = ChargeItem.query.filter(
            ChargeItem.charge_id == charge_id,
            ChargeItem.category == category,
            ChargeItem.is_active == True
        ).all()
        
        total = Decimal('0')
        
        for item in items:
            # Calcular correção monetária
            correction = self._calculate_monetary_correction(
                item.nominal_amount, 
                item.due_date, 
                params['correction_index']
            )
            
            # Calcular juros
            interest = self._calculate_interest(
                item.nominal_amount + correction,
                item.due_date,
                params['interest_rate']
            )
            
            # Calcular multa (apenas para principal)
            fine = Decimal('0')
            if category == 'PRINCIPAL' and item.due_date < self.calculation_date:
                fine = item.nominal_amount * (params['fine_rate'] / 100)
            
            # Subtotal do item
            subtotal = item.nominal_amount + correction + interest + fine
            
            # Atualizar item
            item.monetary_correction = correction
            item.interest_amount = interest
            item.fine_amount = fine
            item.subtotal = subtotal
            
            total += subtotal
        
        return total
    
    def _calculate_monetary_correction(self, amount, due_date, index_type):
        """Calcula correção monetária"""
        # Implementação simplificada - em produção, integrar com APIs de índices
        months_diff = self._get_months_difference(due_date, self.calculation_date)
        
        if months_diff <= 0:
            return Decimal('0')
        
        # Taxas aproximadas mensais
        rates = {
            'INPC': Decimal('0.005'),  # 0.5% ao mês
            'IGPM': Decimal('0.006'),  # 0.6% ao mês
            'IPCA': Decimal('0.004'),  # 0.4% ao mês
            'CDI': Decimal('0.008')    # 0.8% ao mês
        }
        
        monthly_rate = rates.get(index_type, Decimal('0.005'))
        correction_factor = (1 + monthly_rate) ** months_diff - 1
        
        return amount * correction_factor
    
    def _calculate_interest(self, amount, due_date, monthly_rate):
        """Calcula juros de mora"""
        months_diff = self._get_months_difference(due_date, self.calculation_date)
        
        if months_diff <= 0:
            return Decimal('0')
        
        rate = monthly_rate / 100  # Converter percentual
        return amount * rate * months_diff
    
    def _calculate_fees(self, charge_id, fee_type, base_amount, params):
        """Calcula honorários"""
        # Verificar se já existe configuração específica
        existing_fee = ChargeFees.query.filter(
            ChargeFees.charge_id == charge_id,
            ChargeFees.fee_type == fee_type,
            ChargeFees.is_active == True
        ).first()
        
        if existing_fee:
            if existing_fee.calculation_type == 'PERCENTAGE':
                return base_amount * (existing_fee.percentage_rate / 100)
            else:
                return existing_fee.fixed_amount
        
        # Usar parâmetros padrão do cliente
        if fee_type == 'EXTRAJUDICIAL':
            rate = params['extrajudicial_fees_rate']
        else:  # EXECUTION
            rate = params['execution_fees_rate']
        
        return base_amount * (rate / 100)
    
    def _calculate_art_523_fine(self, base_amount, params):
        """Calcula multa do Art. 523 CPC"""
        rate = params['art_523_fine_rate']
        return base_amount * (rate / 100)
    
    def _get_months_difference(self, start_date, end_date):
        """Calcula diferença em meses entre duas datas"""
        if start_date >= end_date:
            return 0
        
        delta = relativedelta(end_date, start_date)
        return delta.years * 12 + delta.months + (1 if delta.days > 0 else 0)
    
    def generate_debt_spreadsheet(self, charge_id):
        """Gera planilha detalhada do débito"""
        charge = Charge.query.get(charge_id)
        if not charge:
            raise ValueError("Cobrança não encontrada")
        
        # Recalcular para garantir valores atualizados
        calculation_result = self.calculate_charge(charge_id)
        
        # Buscar itens detalhados
        principal_items = ChargeItem.query.filter(
            ChargeItem.charge_id == charge_id,
            ChargeItem.category == 'PRINCIPAL',
            ChargeItem.is_active == True
        ).all()
        
        expense_items = ChargeItem.query.filter(
            ChargeItem.charge_id == charge_id,
            ChargeItem.category == 'COLLECTION_EXPENSES',
            ChargeItem.is_active == True
        ).all()
        
        # Buscar honorários
        fees = ChargeFees.query.filter(
            ChargeFees.charge_id == charge_id,
            ChargeFees.is_active == True
        ).all()
        
        return {
            'charge': charge.to_dict(),
            'calculation_date': self.calculation_date.isoformat(),
            'principal_items': [item.to_dict() for item in principal_items],
            'expense_items': [item.to_dict() for item in expense_items],
            'fees': [fee.to_dict() for fee in fees],
            'totals': calculation_result,
            'breakdown': {
                'client_amount': float(calculation_result['principal_amount'] + calculation_result['expenses_amount']),
                'lawyer_amount': float(calculation_result['extrajudicial_fees'] + calculation_result['execution_fees']),
                'court_amount': float(calculation_result['art_523_fine']),
                'total_amount': float(calculation_result['total_amount'])
            },
            'percentages': {
                'client_percentage': round((calculation_result['principal_amount'] + calculation_result['expenses_amount']) / calculation_result['total_amount'] * 100, 2),
                'lawyer_percentage': round((calculation_result['extrajudicial_fees'] + calculation_result['execution_fees']) / calculation_result['total_amount'] * 100, 2),
                'court_percentage': round(calculation_result['art_523_fine'] / calculation_result['total_amount'] * 100, 2)
            }
        }

