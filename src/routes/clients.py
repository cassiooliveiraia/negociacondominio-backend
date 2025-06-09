from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from src.models.database import db, Client, Person, Unit, UnitOwner
from sqlalchemy import or_

clients_bp = Blueprint('clients', __name__)

@clients_bp.route('/', methods=['GET'])
@jwt_required()
def get_clients():
    try:
        # Parâmetros de consulta
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 10, type=int)
        search = request.args.get('search', '')
        
        # Construir query
        query = Client.query.join(Person).filter(Client.is_active == True)
        
        # Filtros
        if search:
            query = query.filter(
                or_(
                    Person.name.ilike(f'%{search}%'),
                    Client.client_code.ilike(f'%{search}%'),
                    Person.document.ilike(f'%{search}%')
                )
            )
        
        # Paginação
        total = query.count()
        clients = query.offset((page - 1) * limit).limit(limit).all()
        
        # Adicionar estatísticas para cada cliente
        clients_data = []
        for client in clients:
            client_dict = client.to_dict()
            
            # Contar unidades
            total_units = Unit.query.filter_by(client_id=client.id, is_active=True).count()
            
            # Contar cobranças ativas (simulado)
            active_charges = 0  # Será implementado quando tivermos o modelo Charge
            
            # Valor total de débito (simulado)
            total_debt = 0.0  # Será implementado quando tivermos o modelo Charge
            
            # Taxa de sucesso (simulado)
            success_rate = 85.0  # Será calculado baseado em pagamentos reais
            
            client_dict.update({
                'totalUnits': total_units,
                'activeCharges': active_charges,
                'totalDebt': total_debt,
                'successRate': success_rate
            })
            
            clients_data.append(client_dict)
        
        return jsonify({
            'data': clients_data,
            'total': total,
            'page': page,
            'limit': limit,
            'pages': (total + limit - 1) // limit
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@clients_bp.route('/<client_id>', methods=['GET'])
@jwt_required()
def get_client(client_id):
    try:
        client = Client.query.get(client_id)
        
        if not client:
            return jsonify({'error': 'Cliente não encontrado'}), 404
        
        return jsonify({'data': client.to_dict()})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@clients_bp.route('/', methods=['POST'])
@jwt_required()
def create_client():
    try:
        data = request.get_json()
        
        # Validações básicas
        required_fields = ['personId', 'clientCode', 'contractStartDate']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Campo {field} é obrigatório'}), 400
        
        # Verificar se pessoa existe
        person = Person.query.get(data['personId'])
        if not person:
            return jsonify({'error': 'Pessoa não encontrada'}), 404
        
        # Verificar se código do cliente já existe
        existing_client = Client.query.filter_by(client_code=data['clientCode']).first()
        if existing_client:
            return jsonify({'error': 'Código do cliente já existe'}), 400
        
        # Criar novo cliente
        client = Client(
            person_id=data['personId'],
            client_code=data['clientCode'],
            contract_start_date=data['contractStartDate'],
            contract_end_date=data.get('contractEndDate')
        )
        
        db.session.add(client)
        db.session.commit()
        
        return jsonify({
            'message': 'Cliente criado com sucesso',
            'data': client.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@clients_bp.route('/<client_id>/units', methods=['GET'])
@jwt_required()
def get_client_units(client_id):
    try:
        client = Client.query.get(client_id)
        
        if not client:
            return jsonify({'error': 'Cliente não encontrado'}), 404
        
        units = Unit.query.filter_by(client_id=client_id, is_active=True).all()
        
        # Adicionar informações dos proprietários
        units_data = []
        for unit in units:
            unit_dict = unit.to_dict()
            
            # Buscar proprietários/responsáveis
            owners = UnitOwner.query.filter_by(
                unit_id=unit.id, 
                is_active=True
            ).join(Person).all()
            
            unit_dict['owners'] = [owner.to_dict() for owner in owners]
            units_data.append(unit_dict)
        
        return jsonify({
            'data': units_data,
            'total': len(units_data)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@clients_bp.route('/<client_id>/units', methods=['POST'])
@jwt_required()
def create_unit(client_id):
    try:
        client = Client.query.get(client_id)
        
        if not client:
            return jsonify({'error': 'Cliente não encontrado'}), 404
        
        data = request.get_json()
        
        # Validações básicas
        required_fields = ['unitCode', 'unitType', 'number']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Campo {field} é obrigatório'}), 400
        
        # Verificar se código da unidade já existe para este cliente
        existing_unit = Unit.query.filter_by(
            client_id=client_id, 
            unit_code=data['unitCode']
        ).first()
        if existing_unit:
            return jsonify({'error': 'Código da unidade já existe para este cliente'}), 400
        
        # Criar nova unidade
        unit = Unit(
            client_id=client_id,
            unit_code=data['unitCode'],
            unit_type=data['unitType'],
            block=data.get('block'),
            floor=data.get('floor'),
            number=data['number'],
            area=data.get('area'),
            ideal_fraction=data.get('idealFraction'),
            status=data.get('status', 'ACTIVE')
        )
        
        db.session.add(unit)
        db.session.commit()
        
        return jsonify({
            'message': 'Unidade criada com sucesso',
            'data': unit.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

