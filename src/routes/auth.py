from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import check_password_hash, generate_password_hash
from src.models.database import db
from src.models.user import User
from datetime import datetime, timedelta

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'success': False, 'error': 'Email e senha são obrigatórios'}), 400
        
        # Para demonstração, vamos usar credenciais fixas
        # Em produção, isso seria verificado no banco de dados
        if email == 'admin@negociacondominio.com.br' and password == 'demo123':
            # Criar ou buscar usuário de demonstração
            user = User.query.filter_by(email=email).first()
            if not user:
                user = User(
                    email=email,
                    password_hash=generate_password_hash(password),
                    first_name='Usuário',
                    last_name='Teste',
                    role='ADMIN'
                )
                db.session.add(user)
                db.session.commit()
            
            # Atualizar último login
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            # Criar token JWT
            access_token = create_access_token(
                identity=user.id,
                expires_delta=timedelta(hours=24)
            )
            
            return jsonify({
                'success': True,
                'user': user.to_dict(),
                'token': access_token
            })
        else:
            return jsonify({'success': False, 'error': 'Credenciais inválidas'}), 401
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'Usuário não encontrado'}), 404
        
        return jsonify({'user': user.to_dict()})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required()
def refresh_token():
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'Usuário não encontrado'}), 404
        
        new_token = create_access_token(
            identity=user.id,
            expires_delta=timedelta(hours=24)
        )
        
        return jsonify({'token': new_token})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    # Em uma implementação real, você poderia adicionar o token a uma blacklist
    return jsonify({'message': 'Logout realizado com sucesso'})

