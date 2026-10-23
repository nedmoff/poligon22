from flask import Blueprint, render_template, abort
from .models import User, Channel, ChannelMember
from .extensions import db

bp = Blueprint('main', __name__)


@bp.get('/')
def index():
    return render_template('index.html')


@bp.get('/u/<username>')
def profile(username):
    user = User.query.filter_by(username=username).first()
    if not user:
        abort(404)
    channels = (db.session.query(Channel)
                .join(ChannelMember, ChannelMember.channel_id == Channel.id)
                .filter(ChannelMember.user_id == user.id)
                .order_by(Channel.name).all())
    return render_template('profile.html', user=user, channels=channels)
