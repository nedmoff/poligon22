from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from .extensions import db


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    bio = db.Column(db.Text, nullable=False, default='')
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Channel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)


class ChannelMember(db.Model):
    __table_args__ = (db.UniqueConstraint('channel_id', 'user_id'),)
    id = db.Column(db.Integer, primary_key=True)
    channel_id = db.Column(db.Integer, db.ForeignKey('channel.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)


class Chat(db.Model):
    __table_args__ = (
        db.UniqueConstraint('user_low_id', 'user_high_id'),
        db.CheckConstraint('user_low_id < user_high_id'),
    )
    id = db.Column(db.Integer, primary_key=True)
    user_low_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    user_high_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    def has_user(self, user_id):
        return user_id in (self.user_low_id, self.user_high_id)


class Message(db.Model):
    __table_args__ = (
        db.CheckConstraint(
            '(chat_id IS NOT NULL AND channel_id IS NULL) OR '
            '(chat_id IS NULL AND channel_id IS NOT NULL)',
            name='one_message_destination'
        ),
        db.Index('ix_message_chat_id_id', 'chat_id', 'id'),
        db.Index('ix_message_channel_id_id', 'channel_id', 'id'),
    )
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    chat_id = db.Column(db.Integer, db.ForeignKey('chat.id'), index=True)
    channel_id = db.Column(db.Integer, db.ForeignKey('channel.id'), index=True)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    sender = db.relationship('User')

    def as_json(self):
        return {
            'id': self.id, 'sender_id': self.sender_id,
            'username': self.sender.username,
            'chat_id': self.chat_id, 'channel_id': self.channel_id,
            'text': self.text, 'created_at': self.created_at.isoformat() + 'Z'
        }


class LoginAttempt(db.Model):
    key = db.Column(db.String(255), primary_key=True)
    failures = db.Column(db.Integer, nullable=False, default=0)
    first_failure = db.Column(db.DateTime, nullable=False, default=utcnow)
    locked_until = db.Column(db.DateTime)
