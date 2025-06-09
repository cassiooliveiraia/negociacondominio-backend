import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Importar modelos e rotas
from src.models.database import db
from src.routes.auth import auth_bp
from src.routes.people import people_bp
from src.routes.clients import clients_bp
from src.routes.charges import charges_bp
from src.routes.progress import progress_bp
from src.routes.economic_indices import economic_indices_bp
from src.routes.temp_routes import financial_bp, communication_bp, reports_bp

def create_app():
    app = Flask(__name__, static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'negociacondominio-frontend/dist'))
    
    # Configurações
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'negociacondominio-secret-key-2024')
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-negociacondominio')
    
    # Configuração do banco de dados SQLite para demonstração
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///negociacondominio.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Inicializar extensões
    CORS(app, origins="*")  # Permitir CORS para todas as origens
    JWTManager(app)
    db.init_app(app)
    
    # Registrar blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(people_bp, url_prefix='/api/people')
    app.register_blueprint(clients_bp, url_prefix='/api/clients')
    app.register_blueprint(charges_bp, url_prefix='/api/charges')
    app.register_blueprint(progress_bp, url_prefix='/api/progress')
    app.register_blueprint(economic_indices_bp, url_prefix='/api/economic-indices')
    app.register_blueprint(financial_bp, url_prefix='/api/financial')
    app.register_blueprint(communication_bp, url_prefix='/api/communication')
    app.register_blueprint(reports_bp, url_prefix='/api/reports')

    
    # Rota de health check
    @app.route('/api/health')
    def health_check():
        return jsonify({
            'status': 'healthy',
            'service': 'NegocIA Condomínio API',
            'version': '1.0.0'
        })
    
    # Rota para servir arquivos estáticos (frontend)
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve(path):
        static_folder_path = app.static_folder
        if static_folder_path is None:
            return "Static folder not configured", 404

        if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
            return send_from_directory(static_folder_path, path)
        else:
            index_path = os.path.join(static_folder_path, 'index.html')
            if os.path.exists(index_path):
                return send_from_directory(static_folder_path, 'index.html')
            else:
                return jsonify({'message': 'NegocIA Condomínio API is running'}), 200
    
    # Criar tabelas do banco de dados
    with app.app_context():
        try:
            db.create_all()
            print("✅ Tabelas do banco de dados criadas com sucesso!")
        except Exception as e:
            print(f"❌ Erro ao criar tabelas: {e}")
    
    return app

if __name__ == '__main__':
    app = create_app()
        # Criar usuário admin de demonstração, se não existir
    from src.models.database import User
    from werkzeug.security import generate_password_hash

    with app.app_context():
        if not User.query.filter_by(email="admin@negociacondominio.com.br").first():
            admin = User(
                email="admin@negociacondominio.com.br",
                password=generate_password_hash("demo123"),
                nome="Admin",
                role="admin"
            )
            db.session.add(admin)
            db.session.commit()
            print("✅ Usuário admin de demonstração criado.")

    app.run(host='0.0.0.0', port=5000, debug=True)

feat: criação de usuário admin de demonstração no primeiro carregamento
