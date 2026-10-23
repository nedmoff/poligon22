from io import BytesIO
from functools import wraps
from flask import Blueprint, jsonify, request, session, current_app, send_file
from sqlalchemy import or_
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError
from .extensions import db
from .models import User, Chat, Channel, ChannelMember, Message

bp = Blueprint('api', __name__)


def error(message, status=400):
    return jsonify(error=message), status


def authenticated(fn):
    @wraps(fn)
    def decorated(*args, **kwargs):
        user_id = session.get('user_id')
        if not isinstance(user_id, int) or db.session.get(User, user_id) is None:
            return error('Authentication required', 401)
        return fn(*args, **kwargs)
    return decorated


def payload():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def integer_id(value):
    return value if type(value) is int and value > 0 else None


def chat_access(chat_id):
    chat = db.session.get(Chat, chat_id)
    if not chat:
        return None, error('Chat not found', 404)
    if not chat.has_user(session['user_id']):
        return None, error('Forbidden', 403)
    return chat, None


def channel_json(channel):
    return {'id': channel.id, 'name': channel.name, 'creator_id': channel.creator_id}


def chat_json(chat):
    return {'id': chat.id, 'user_ids': [chat.user_low_id, chat.user_high_id]}


@bp.get('/health')
def health():
    return jsonify(status='ok', team_id=current_app.config['TEAM_ID'],
                   team_name=current_app.config['TEAM_NAME'])


@bp.post('/channels')
@authenticated
def create_channel():
    name = payload().get('name')
    if not isinstance(name, str) or not (1 <= len(name.strip()) <= 100):
        return error('Invalid channel name')
    name = name.strip()
    channel = Channel(name=name, creator_id=session['user_id'])
    db.session.add(channel)
    try:
        db.session.flush()
        db.session.add(ChannelMember(channel_id=channel.id, user_id=session['user_id']))
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return error('Channel already exists', 409)
    return jsonify(channel_json(channel)), 201


@bp.get('/channels')
@authenticated
def list_channels():
    return jsonify([channel_json(c) for c in Channel.query.order_by(Channel.id).all()])


@bp.post('/channels/<int:channel_id>/join')
@authenticated
def join_channel(channel_id):
    channel = db.session.get(Channel, channel_id)
    if not channel:
        return error('Channel not found', 404)
    exists = ChannelMember.query.filter_by(channel_id=channel_id, user_id=session['user_id']).first()
    if not exists:
        db.session.add(ChannelMember(channel_id=channel_id, user_id=session['user_id']))
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
    return jsonify(channel_json(channel))


@bp.post('/chats')
@authenticated
def create_chat():
    username = payload().get('username')
    if not isinstance(username, str) or not username.strip():
        return error('Invalid username')
    other = User.query.filter_by(username=username.strip()).first()
    if not other:
        return error('User not found', 404)
    uid = session['user_id']
    if other.id == uid:
        return error('Cannot chat with yourself')
    low, high = sorted((uid, other.id))
    chat = Chat.query.filter_by(user_low_id=low, user_high_id=high).first()
    created = chat is None
    if created:
        chat = Chat(user_low_id=low, user_high_id=high)
        db.session.add(chat)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            chat = Chat.query.filter_by(user_low_id=low, user_high_id=high).first()
            created = False
    return jsonify(chat_json(chat)), 201 if created else 200


@bp.get('/chats')
@authenticated
def list_chats():
    uid = session['user_id']
    chats = Chat.query.filter(or_(Chat.user_low_id == uid, Chat.user_high_id == uid)).order_by(Chat.id).all()
    return jsonify([chat_json(c) for c in chats])


@bp.post('/messages')
@authenticated
def send_message():
    body = payload()
    chat_id, channel_id = body.get('chat_id'), body.get('channel_id')
    text = body.get('text')
    if (integer_id(chat_id) is None) == (integer_id(channel_id) is None):
        return error('Provide exactly one destination')
    if not isinstance(text, str) or not text.strip() or len(text) > 10000:
        return error('Invalid message text')
    if integer_id(chat_id) is not None:
        _, failure = chat_access(chat_id)
        if failure:
            return failure
    else:
        if not db.session.get(Channel, channel_id):
            return error('Channel not found', 404)
        membership = ChannelMember.query.filter_by(channel_id=channel_id, user_id=session['user_id']).first()
        if not membership:
            return error('Forbidden', 403)
    message = Message(sender_id=session['user_id'], chat_id=chat_id if integer_id(chat_id) else None,
                      channel_id=channel_id if integer_id(channel_id) else None, text=text)
    db.session.add(message)
    db.session.commit()
    return jsonify(message.as_json()), 201


@bp.get('/chats/<int:chat_id>/messages')
@authenticated
def chat_messages(chat_id):
    _, failure = chat_access(chat_id)
    if failure:
        return failure
    messages = Message.query.options(joinedload(Message.sender)).filter_by(chat_id=chat_id).order_by(Message.id).all()
    return jsonify([m.as_json() for m in messages])


@bp.get('/channels/<int:channel_id>/messages')
@authenticated
def channel_messages(channel_id):
    if not db.session.get(Channel, channel_id):
        return error('Channel not found', 404)
    messages = Message.query.options(joinedload(Message.sender)).filter_by(channel_id=channel_id).order_by(Message.id).all()
    return jsonify([m.as_json() for m in messages])


@bp.get('/messages/search')
@authenticated
def search_messages():
    q = request.args.get('q', '')
    if not q or len(q) > 200:
        return error('Invalid search query')
    uid = session['user_id']
    accessible_chats = db.session.query(Chat.id).filter(
        or_(Chat.user_low_id == uid, Chat.user_high_id == uid))
    statement = Message.query.options(joinedload(Message.sender)).filter(
        Message.text.contains(q, autoescape=True),
        or_(Message.channel_id.isnot(None), Message.chat_id.in_(accessible_chats))
    ).order_by(Message.id.desc()).limit(200)
    return jsonify([m.as_json() for m in statement.all()])


@bp.post('/profile')
@authenticated
def update_profile():
    bio = payload().get('bio')
    if not isinstance(bio, str) or len(bio) > 2000:
        return error('Invalid bio')
    user = db.session.get(User, session['user_id'])
    user.bio = bio
    db.session.commit()
    return jsonify(username=user.username, bio=user.bio)


def export_messages(messages, name):
    text = '\n'.join(f'[{m.created_at.isoformat()}Z] {m.sender.username}: {m.text}' for m in messages)
    output = BytesIO(text.encode('utf-8'))
    return send_file(output, mimetype='text/plain; charset=utf-8', as_attachment=True, download_name=name)


def export_format_ok():
    return request.args.get('format', 'txt') == 'txt'


@bp.get('/chats/<int:chat_id>/export')
@authenticated
def export_chat(chat_id):
    _, failure = chat_access(chat_id)
    if failure:
        return failure
    if not export_format_ok():
        return error('Only txt supported')
    messages = Message.query.filter_by(chat_id=chat_id).order_by(Message.id).all()
    return export_messages(messages, f'chat_{chat_id}.txt')


@bp.get('/channels/<int:channel_id>/export')
@authenticated
def export_channel(channel_id):
    if not db.session.get(Channel, channel_id):
        return error('Channel not found', 404)
    if not export_format_ok():
        return error('Only txt supported')
    messages = Message.query.filter_by(channel_id=channel_id).order_by(Message.id).all()
    return export_messages(messages, f'channel_{channel_id}.txt')
