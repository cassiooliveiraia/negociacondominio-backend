from flask import Blueprint, jsonify

# Apenas inicializa o blueprint sem usar os modelos por enquanto
people_bp = Blueprint('people', __name__)

@people_bp.route('/', methods=['GET'])
def get_people():
    return jsonify({'message': 'Rota /api/people funcionando corretamente.'})
