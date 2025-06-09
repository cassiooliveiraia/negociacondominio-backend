from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required
from src.models.database import db, Charge, ChargeItem, ChargeFees, Unit
from src.services.charge_calculator import ChargeCalculatorService
from src.services.debt_spreadsheet_generator import DebtSpreadsheetGenerator
from sqlalchemy import or_, and_
from datetime import datetime, date
import uuid

charges_bp = Blueprint('charges', __name__)

@charges_bp.route('/check-unit-status/<unit_id>', methods=['GET'])
@jwt_required()
def check_unit_charge_status(unit_id):
    """Verifica se uma unidade pode receber novas cobranças"""
    try:
        unit = Unit.query.get(unit_id)
        if not unit:
            return jsonify({'error': 'Unidade não encontrada'}), 404
        
        # Verificar cobranças ativas/negociadas para a unidade
        active_charges = Charge.query.filter(
            and_(
                Charge.unit_id == unit_id,
                Charge.is_active == True,
                Charge.status.in_(['PENDING', 'OVERDUE', 'NEGOTIATED', 'NEGOTIATING'])
            )
        ).all()
        
        can_create_new_charge = len(active_charges) == 0
        
        return jsonify({
            'unitId': unit_id,
            'canCreateNewCharge': can_create_new_charge,
            'activeCharges': [charge.to_dict() for charge in active_charges],
            'message': 'Unidade livre para nova cobrança' if can_create_new_charge else 'Unidade possui cobranças pendentes ou negociadas'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@charges_bp.route('/', methods=['POST'])
@jwt_required()
def create_charge():
    """Cria nova cobrança com verificação de status da unidade"""
    try:
        data = request.get_json()
        
        # Validações básicas
        required_fields = ['clientId', 'debtorId', 'chargeDate', 'dueDate', 'category', 'description']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Campo {field} é obrigatório'}), 400
        
        # Verificar se unidade pode receber nova cobrança
        if data.get('unitId'):
            unit_status = check_unit_charge_status(data['unitId'])
            unit_data = unit_status.get_json()
            
            if not unit_data['canCreateNewCharge']:
                return jsonify({
                    'error': 'Não é possível criar nova cobrança para esta unidade',
                    'reason': 'Unidade possui cobranças pendentes ou negociadas',
                    'activeCharges': unit_data['activeCharges']
                }), 400
        
        # Gerar código da cobrança
        charge_code = f"COB{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:6].upper()}"
        
        # Criar nova cobrança
        charge = Charge(
            charge_code=charge_code,
            client_id=data['clientId'],
            debtor_id=data['debtorId'],
            unit_id=data.get('unitId'),
            charge_date=datetime.strptime(data['chargeDate'], '%Y-%m-%d').date(),
            due_date=datetime.strptime(data['dueDate'], '%Y-%m-%d').date(),
            category=data['category'],
            description=data['description'],
            reference_period=data.get('referencePeriod'),
            total_amount=0,  # Será calculado
            balance_amount=0  # Será calculado
        )
        
        db.session.add(charge)
        db.session.flush()  # Para obter o ID
        
        # Processar itens da cobrança se fornecidos
        if 'items' in data:
            for item_data in data['items']:
                item = ChargeItem(
                    charge_id=charge.id,
                    category=item_data['category'],
                    due_date=datetime.strptime(item_data['dueDate'], '%Y-%m-%d').date(),
                    description=item_data['description'],
                    nominal_amount=item_data['nominalAmount'],
                    monetary_correction_rate=item_data.get('monetaryCorrectionRate', 0),
                    interest_rate=item_data.get('interestRate', 0),
                    fine_rate=item_data.get('fineRate', 0),
                    subtotal=0  # Será calculado
                )
                db.session.add(item)
        
        # Calcular valores da cobrança
        calculator = ChargeCalculatorService()
        calculator.calculate_charge(charge.id)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Cobrança criada com sucesso',
            'data': charge.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@charges_bp.route('/<charge_id>/negotiate', methods=['POST'])
@jwt_required()
def negotiate_charge(charge_id):
    """Inicia negociação e altera status para NEGOTIATED"""
    try:
        charge = Charge.query.get(charge_id)
        
        if not charge:
            return jsonify({'error': 'Cobrança não encontrada'}), 404
        
        if charge.status in ['PAID', 'CANCELLED']:
            return jsonify({'error': 'Não é possível negociar cobrança paga ou cancelada'}), 400
        
        data = request.get_json()
        
        # Alterar status para NEGOTIATED
        charge.status = 'NEGOTIATED'
        
        # Criar registro de negociação (implementar modelo Negotiation)
        # ... código de negociação ...
        
        db.session.commit()
        
        return jsonify({
            'message': 'Cobrança marcada como negociada com sucesso',
            'data': charge.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@charges_bp.route('/<charge_id>/spreadsheet', methods=['GET'])
@jwt_required()
def generate_debt_spreadsheet(charge_id):
    """Gera planilha do débito"""
    try:
        charge = Charge.query.get(charge_id)
        
        if not charge:
            return jsonify({'error': 'Cobrança não encontrada'}), 404
        
        # Gerar planilha usando o serviço
        calculator = ChargeCalculatorService()
        spreadsheet_data = calculator.generate_debt_spreadsheet(charge_id)
        
        return jsonify({
            'message': 'Planilha do débito gerada com sucesso',
            'data': spreadsheet_data
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@charges_bp.route('/<charge_id>/spreadsheet/pdf', methods=['GET'])
@jwt_required()
def export_debt_spreadsheet_pdf(charge_id):
    """Exporta planilha do débito em PDF"""
    try:
        charge = Charge.query.get(charge_id)
        
        if not charge:
            return jsonify({'error': 'Cobrança não encontrada'}), 404
        
        # Gerar PDF da planilha
        generator = DebtSpreadsheetGenerator()
        pdf_path = generator.generate_pdf(charge_id)
        
        return send_file(
            pdf_path,
            as_attachment=True,
            download_name=f'planilha_debito_{charge.charge_code}.pdf',
            mimetype='application/pdf'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@charges_bp.route('/<charge_id>/spreadsheet/excel', methods=['GET'])
@jwt_required()
def export_debt_spreadsheet_excel(charge_id):
    """Exporta planilha do débito em Excel"""
    try:
        charge = Charge.query.get(charge_id)
        
        if not charge:
            return jsonify({'error': 'Cobrança não encontrada'}), 404
        
        # Gerar Excel da planilha
        generator = DebtSpreadsheetGenerator()
        excel_path = generator.generate_excel(charge_id)
        
        return send_file(
            excel_path,
            as_attachment=True,
            download_name=f'planilha_debito_{charge.charge_code}.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@charges_bp.route('/unit/<unit_id>/history', methods=['GET'])
@jwt_required()
def get_unit_charge_history(unit_id):
    """Histórico completo de cobranças de uma unidade"""
    try:
        unit = Unit.query.get(unit_id)
        if not unit:
            return jsonify({'error': 'Unidade não encontrada'}), 404
        
        # Buscar todas as cobranças da unidade
        charges = Charge.query.filter(
            Charge.unit_id == unit_id,
            Charge.is_active == True
        ).order_by(Charge.created_at.desc()).all()
        
        # Estatísticas
        total_charges = len(charges)
        paid_charges = len([c for c in charges if c.status == 'PAID'])
        negotiated_charges = len([c for c in charges if c.status == 'NEGOTIATED'])
        pending_charges = len([c for c in charges if c.status in ['PENDING', 'OVERDUE']])
        
        total_amount = sum([float(c.total_amount) for c in charges])
        paid_amount = sum([float(c.paid_amount) for c in charges])
        balance_amount = total_amount - paid_amount
        
        return jsonify({
            'unit': unit.to_dict(),
            'charges': [charge.to_dict() for charge in charges],
            'statistics': {
                'totalCharges': total_charges,
                'paidCharges': paid_charges,
                'negotiatedCharges': negotiated_charges,
                'pendingCharges': pending_charges,
                'totalAmount': total_amount,
                'paidAmount': paid_amount,
                'balanceAmount': balance_amount,
                'successRate': round((paid_charges / total_charges * 100) if total_charges > 0 else 0, 2)
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@charges_bp.route('/bulk-create', methods=['POST'])
@jwt_required()
def bulk_create_charges():
    """Criação em lote de cobranças (ex: taxa condominial mensal)"""
    try:
        data = request.get_json()
        
        required_fields = ['clientId', 'chargeDate', 'dueDate', 'category', 'description', 'units']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Campo {field} é obrigatório'}), 400
        
        client_id = data['clientId']
        charge_date = datetime.strptime(data['chargeDate'], '%Y-%m-%d').date()
        due_date = datetime.strptime(data['dueDate'], '%Y-%m-%d').date()
        
        created_charges = []
        skipped_units = []
        
        for unit_data in data['units']:
            unit_id = unit_data['unitId']
            debtor_id = unit_data['debtorId']
            amount = unit_data['amount']
            
            # Verificar se unidade pode receber nova cobrança
            active_charges = Charge.query.filter(
                and_(
                    Charge.unit_id == unit_id,
                    Charge.is_active == True,
                    Charge.status.in_(['PENDING', 'OVERDUE', 'NEGOTIATED', 'NEGOTIATING'])
                )
            ).count()
            
            if active_charges > 0:
                skipped_units.append({
                    'unitId': unit_id,
                    'reason': 'Unidade possui cobranças pendentes ou negociadas'
                })
                continue
            
            # Criar cobrança
            charge_code = f"COB{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:6].upper()}"
            
            charge = Charge(
                charge_code=charge_code,
                client_id=client_id,
                debtor_id=debtor_id,
                unit_id=unit_id,
                charge_date=charge_date,
                due_date=due_date,
                category=data['category'],
                description=data['description'],
                reference_period=data.get('referencePeriod'),
                total_amount=amount,
                balance_amount=amount
            )
            
            db.session.add(charge)
            db.session.flush()
            
            # Criar item principal
            item = ChargeItem(
                charge_id=charge.id,
                category='PRINCIPAL',
                due_date=due_date,
                description=data['description'],
                nominal_amount=amount,
                subtotal=amount
            )
            
            db.session.add(item)
            created_charges.append(charge.to_dict())
        
        db.session.commit()
        
        return jsonify({
            'message': f'{len(created_charges)} cobranças criadas com sucesso',
            'createdCharges': created_charges,
            'skippedUnits': skipped_units,
            'summary': {
                'created': len(created_charges),
                'skipped': len(skipped_units),
                'total': len(data['units'])
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ... resto das rotas existentes ...

