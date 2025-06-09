# Rotas temporárias para módulos que serão implementados posteriormente

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required

charges_bp = Blueprint('charges', __name__)
financial_bp = Blueprint('financial', __name__)
communication_bp = Blueprint('communication', __name__)
reports_bp = Blueprint('reports', __name__)

# Rotas de Cobranças
@charges_bp.route('/', methods=['GET'])
@jwt_required()
def get_charges():
    return jsonify({
        'message': 'Módulo de cobranças em desenvolvimento',
        'data': [],
        'total': 0
    })

@charges_bp.route('/dashboard', methods=['GET'])
@jwt_required()
def get_charges_dashboard():
    return jsonify({
        'activeCharges': 127,
        'totalValue': 45230.00,
        'successRate': 78,
        'activeClients': 23,
        'monthlyGrowth': {
            'charges': 12,
            'value': 8,
            'successRate': 5,
            'clients': 2
        }
    })

# Rotas Financeiras
@financial_bp.route('/payments', methods=['GET'])
@jwt_required()
def get_payments():
    return jsonify({
        'message': 'Módulo financeiro em desenvolvimento',
        'data': [],
        'total': 0
    })

# Rotas de Comunicação
@communication_bp.route('/whatsapp', methods=['GET'])
@jwt_required()
def get_whatsapp_messages():
    return jsonify({
        'message': 'Módulo de comunicação em desenvolvimento',
        'data': [],
        'total': 0
    })

# Rotas de Relatórios
@reports_bp.route('/dashboard', methods=['GET'])
@jwt_required()
def get_dashboard_data():
    return jsonify({
        'dashboard': {
            'activeCharges': 127,
            'totalValue': 45230.00,
            'successRate': 78,
            'activeClients': 23,
            'monthlyGrowth': {
                'charges': 12,
                'value': 8,
                'successRate': 5,
                'clients': 2
            }
        },
        'activities': [
            {
                'id': '1',
                'description': 'Nova cobrança criada - Condomínio ABC',
                'timestamp': '2024-03-15T16:00:00Z',
                'type': 'CHARGE_CREATED'
            },
            {
                'id': '2',
                'description': 'Pagamento recebido - R$ 1.250,00',
                'timestamp': '2024-03-15T12:00:00Z',
                'type': 'PAYMENT_RECEIVED'
            },
            {
                'id': '3',
                'description': 'Cliente cadastrado - Residencial XYZ',
                'timestamp': '2024-03-14T10:30:00Z',
                'type': 'CLIENT_CREATED'
            }
        ],
        'tasks': [
            {
                'id': '1',
                'description': 'Enviar notificação de vencimento',
                'dueDate': '2024-03-16',
                'priority': 'HIGH',
                'status': 'PENDING'
            },
            {
                'id': '2',
                'description': 'Reunião com cliente - Condomínio DEF',
                'dueDate': '2024-03-17',
                'priority': 'MEDIUM',
                'status': 'PENDING'
            },
            {
                'id': '3',
                'description': 'Relatório mensal de cobranças',
                'dueDate': '2024-03-20',
                'priority': 'LOW',
                'status': 'PENDING'
            }
        ]
    })

