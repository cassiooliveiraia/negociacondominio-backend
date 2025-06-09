from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from src.models.database import db, ChargeProgress, ChargeDocument, WhatsAppMessage, Charge
from datetime import datetime
import uuid
import os

progress_bp = Blueprint('progress', __name__)

@progress_bp.route('/charge/<charge_id>/progress', methods=['GET'])
@jwt_required()
def get_charge_progress(charge_id):
    """Busca andamentos de uma cobrança"""
    try:
        charge = Charge.query.get(charge_id)
        if not charge:
            return jsonify({'error': 'Cobrança não encontrada'}), 404
        
        # Buscar andamentos ordenados por data
        progress_entries = ChargeProgress.query.filter(
            ChargeProgress.charge_id == charge_id,
            ChargeProgress.is_active == True
        ).order_by(ChargeProgress.progress_date.desc()).all()
        
        return jsonify({
            'chargeId': charge_id,
            'progress': [entry.to_dict() for entry in progress_entries],
            'total': len(progress_entries)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@progress_bp.route('/charge/<charge_id>/progress', methods=['POST'])
@jwt_required()
def add_charge_progress(charge_id):
    """Adiciona andamento a uma cobrança"""
    try:
        charge = Charge.query.get(charge_id)
        if not charge:
            return jsonify({'error': 'Cobrança não encontrada'}), 404
        
        data = request.get_json()
        
        # Validações básicas
        required_fields = ['progressType', 'title', 'description']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Campo {field} é obrigatório'}), 400
        
        # Criar andamento
        progress = ChargeProgress(
            charge_id=charge_id,
            progress_date=datetime.strptime(data['progressDate'], '%Y-%m-%dT%H:%M:%S') if data.get('progressDate') else datetime.utcnow(),
            progress_type=data['progressType'],
            title=data['title'],
            description=data['description'],
            user_id=data.get('userId'),
            responsible_name=data.get('responsibleName'),
            whatsapp_message_id=data.get('whatsappMessageId'),
            email_id=data.get('emailId'),
            phone_number=data.get('phoneNumber'),
            priority=data.get('priority', 'MEDIUM'),
            is_milestone=data.get('isMilestone', False)
        )
        
        db.session.add(progress)
        db.session.commit()
        
        return jsonify({
            'message': 'Andamento adicionado com sucesso',
            'data': progress.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@progress_bp.route('/charge/<charge_id>/documents', methods=['GET'])
@jwt_required()
def get_charge_documents(charge_id):
    """Busca documentos de uma cobrança"""
    try:
        charge = Charge.query.get(charge_id)
        if not charge:
            return jsonify({'error': 'Cobrança não encontrada'}), 404
        
        documents = ChargeDocument.query.filter(
            ChargeDocument.charge_id == charge_id,
            ChargeDocument.is_active == True
        ).order_by(ChargeDocument.upload_date.desc()).all()
        
        return jsonify({
            'chargeId': charge_id,
            'documents': [doc.to_dict() for doc in documents],
            'total': len(documents)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@progress_bp.route('/charge/<charge_id>/documents', methods=['POST'])
@jwt_required()
def upload_charge_document(charge_id):
    """Upload de documento para uma cobrança"""
    try:
        charge = Charge.query.get(charge_id)
        if not charge:
            return jsonify({'error': 'Cobrança não encontrada'}), 404
        
        # Verificar se há arquivo no request
        if 'file' not in request.files:
            return jsonify({'error': 'Nenhum arquivo enviado'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Nenhum arquivo selecionado'}), 400
        
        # Dados do formulário
        document_type = request.form.get('documentType', 'OTHER')
        title = request.form.get('title', file.filename)
        description = request.form.get('description', '')
        progress_id = request.form.get('progressId')
        
        # Criar diretório se não existir
        upload_dir = os.path.join('uploads', 'charges', charge_id)
        os.makedirs(upload_dir, exist_ok=True)
        
        # Gerar nome único para o arquivo
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(upload_dir, unique_filename)
        
        # Salvar arquivo
        file.save(file_path)
        
        # Criar registro no banco
        document = ChargeDocument(
            charge_id=charge_id,
            progress_id=progress_id,
            document_type=document_type,
            title=title,
            description=description,
            file_name=file.filename,
            file_path=file_path,
            file_size=os.path.getsize(file_path),
            file_type=file.content_type,
            uploaded_by_id=request.form.get('uploadedById')
        )
        
        db.session.add(document)
        db.session.commit()
        
        return jsonify({
            'message': 'Documento enviado com sucesso',
            'data': document.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@progress_bp.route('/whatsapp/webhook', methods=['POST'])
def whatsapp_webhook():
    """Webhook para receber mensagens do WhatsApp"""
    try:
        data = request.get_json()
        
        # Processar mensagem do WhatsApp
        # Estrutura pode variar dependendo do provedor (Twilio, WhatsApp Business API, etc.)
        
        if 'messages' in data:
            for message_data in data['messages']:
                # Extrair dados da mensagem
                message_id = message_data.get('id')
                phone_number = message_data.get('from', '').replace('whatsapp:', '')
                content = message_data.get('body', '')
                message_type = message_data.get('type', 'text')
                
                # Verificar se mensagem já existe
                existing_message = WhatsAppMessage.query.filter_by(message_id=message_id).first()
                if existing_message:
                    continue
                
                # Criar registro da mensagem
                whatsapp_message = WhatsAppMessage(
                    message_id=message_id,
                    phone_number=phone_number,
                    contact_name=message_data.get('profile', {}).get('name', ''),
                    message_type=message_type.upper(),
                    direction='INBOUND',
                    content=content,
                    media_url=message_data.get('media_url'),
                    media_type=message_data.get('media_type'),
                    status='RECEIVED',
                    sent_at=datetime.utcnow(),
                    webhook_data=message_data
                )
                
                db.session.add(whatsapp_message)
                
                # Tentar associar a uma cobrança baseado no telefone
                # Buscar cobrança ativa para este telefone
                charge = Charge.query.join(Charge.debtor).filter(
                    Charge.debtor.has(phone=phone_number),
                    Charge.status.in_(['PENDING', 'OVERDUE', 'NEGOTIATING']),
                    Charge.is_active == True
                ).first()
                
                if charge:
                    whatsapp_message.charge_id = charge.id
                    
                    # Criar andamento automático
                    progress = ChargeProgress(
                        charge_id=charge.id,
                        progress_type='WHATSAPP_CONTACT',
                        title=f'Mensagem WhatsApp recebida de {phone_number}',
                        description=f'Conteúdo: {content[:100]}...' if len(content) > 100 else content,
                        responsible_name='Sistema WhatsApp',
                        whatsapp_message_id=message_id,
                        phone_number=phone_number,
                        priority='MEDIUM'
                    )
                    
                    db.session.add(progress)
        
        db.session.commit()
        
        return jsonify({'status': 'success', 'message': 'Webhook processado'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@progress_bp.route('/charge/<charge_id>/whatsapp', methods=['GET'])
@jwt_required()
def get_charge_whatsapp_messages(charge_id):
    """Busca mensagens WhatsApp de uma cobrança"""
    try:
        charge = Charge.query.get(charge_id)
        if not charge:
            return jsonify({'error': 'Cobrança não encontrada'}), 404
        
        messages = WhatsAppMessage.query.filter(
            WhatsAppMessage.charge_id == charge_id,
            WhatsAppMessage.is_active == True
        ).order_by(WhatsAppMessage.sent_at.desc()).all()
        
        return jsonify({
            'chargeId': charge_id,
            'messages': [msg.to_dict() for msg in messages],
            'total': len(messages)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@progress_bp.route('/charge/<charge_id>/timeline', methods=['GET'])
@jwt_required()
def get_charge_timeline(charge_id):
    """Timeline completa de uma cobrança (andamentos + mensagens + documentos)"""
    try:
        charge = Charge.query.get(charge_id)
        if not charge:
            return jsonify({'error': 'Cobrança não encontrada'}), 404
        
        # Buscar andamentos
        progress_entries = ChargeProgress.query.filter(
            ChargeProgress.charge_id == charge_id,
            ChargeProgress.is_active == True
        ).all()
        
        # Buscar mensagens WhatsApp
        whatsapp_messages = WhatsAppMessage.query.filter(
            WhatsAppMessage.charge_id == charge_id,
            WhatsAppMessage.is_active == True
        ).all()
        
        # Buscar documentos
        documents = ChargeDocument.query.filter(
            ChargeDocument.charge_id == charge_id,
            ChargeDocument.is_active == True
        ).all()
        
        # Criar timeline unificada
        timeline = []
        
        # Adicionar andamentos
        for progress in progress_entries:
            timeline.append({
                'type': 'PROGRESS',
                'date': progress.progress_date.isoformat(),
                'data': progress.to_dict()
            })
        
        # Adicionar mensagens
        for message in whatsapp_messages:
            timeline.append({
                'type': 'WHATSAPP',
                'date': message.sent_at.isoformat(),
                'data': message.to_dict()
            })
        
        # Adicionar documentos
        for document in documents:
            timeline.append({
                'type': 'DOCUMENT',
                'date': document.upload_date.isoformat(),
                'data': document.to_dict()
            })
        
        # Ordenar por data (mais recente primeiro)
        timeline.sort(key=lambda x: x['date'], reverse=True)
        
        return jsonify({
            'chargeId': charge_id,
            'timeline': timeline,
            'summary': {
                'progressEntries': len(progress_entries),
                'whatsappMessages': len(whatsapp_messages),
                'documents': len(documents),
                'totalEvents': len(timeline)
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

