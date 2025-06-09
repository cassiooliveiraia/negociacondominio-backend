from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from src.models.database import db, EconomicIndex, EconomicIndexValue

economic_indices_bp = Blueprint("economic_indices", __name__)

@economic_indices_bp.route("/", methods=["POST"])
@jwt_required()
def create_economic_index():
    data = request.get_json()
    name = data.get("name")
    description = data.get("description")

    if not name:
        return jsonify({"message": "Nome do índice é obrigatório"}), 400

    new_index = EconomicIndex(name=name, description=description)
    db.session.add(new_index)
    db.session.commit()
    return jsonify({"message": "Índice econômico criado com sucesso!", "id": new_index.id}), 201

@economic_indices_bp.route("/", methods=["GET"])
@jwt_required()
def get_all_economic_indices():
    indices = EconomicIndex.query.all()
    output = []
    for index in indices:
        output.append({
            "id": index.id,
            "name": index.name,
            "description": index.description
        })
    return jsonify({"data": output}), 200

@economic_indices_bp.route("/<int:index_id>", methods=["GET"])
@jwt_required()
def get_economic_index(index_id):
    index = EconomicIndex.query.get_or_404(index_id)
    return jsonify({
        "id": index.id,
        "name": index.name,
        "description": index.description
    }), 200

@economic_indices_bp.route("/<int:index_id>", methods=["PUT"])
@jwt_required()
def update_economic_index(index_id):
    index = EconomicIndex.query.get_or_404(index_id)
    data = request.get_json()

    index.name = data.get("name", index.name)
    index.description = data.get("description", index.description)

    db.session.commit()
    return jsonify({"message": "Índice econômico atualizado com sucesso!"}), 200

@economic_indices_bp.route("/<int:index_id>", methods=["DELETE"])
@jwt_required()
def delete_economic_index(index_id):
    index = EconomicIndex.query.get_or_404(index_id)
    db.session.delete(index)
    db.session.commit()
    return jsonify({"message": "Índice econômico deletado com sucesso!"}), 200

# Rotas para valores dos índices
@economic_indices_bp.route("/<int:index_id>/values", methods=["POST"])
@jwt_required()
def add_economic_index_value(index_id):
    index = EconomicIndex.query.get_or_404(index_id)
    data = request.get_json()
    reference_date = data.get("reference_date")
    value = data.get("value")

    if not reference_date or not value:
        return jsonify({"message": "Data de referência e valor são obrigatórios"}), 400

    new_value = EconomicIndexValue(index_id=index.id, reference_date=reference_date, value=value)
    db.session.add(new_value)
    db.session.commit()
    return jsonify({"message": "Valor do índice adicionado com sucesso!", "id": new_value.id}), 201

@economic_indices_bp.route("/<int:index_id>/values", methods=["GET"])
@jwt_required()
def get_economic_index_values(index_id):
    index = EconomicIndex.query.get_or_404(index_id)
    values = EconomicIndexValue.query.filter_by(index_id=index.id).order_by(EconomicIndexValue.reference_date).all()
    output = []
    for val in values:
        output.append({
            "id": val.id,
            "reference_date": str(val.reference_date),
            "value": str(val.value)
        })
    return jsonify({"data": output}), 200

@economic_indices_bp.route("/values/<int:value_id>", methods=["PUT"])
@jwt_required()
def update_economic_index_value(value_id):
    value_entry = EconomicIndexValue.query.get_or_404(value_id)
    data = request.get_json()

    value_entry.reference_date = data.get("reference_date", value_entry.reference_date)
    value_entry.value = data.get("value", value_entry.value)

    db.session.commit()
    return jsonify({"message": "Valor do índice atualizado com sucesso!"}), 200

@economic_indices_bp.route("/values/<int:value_id>", methods=["DELETE"])
@jwt_required()
def delete_economic_index_value(value_id):
    value_entry = EconomicIndexValue.query.get_or_404(value_id)
    db.session.delete(value_entry)
    db.session.commit()
    return jsonify({"message": "Valor do índice deletado com sucesso!"}), 200


