from flask import Blueprint, jsonify, current_app

bp = Blueprint('api', __name__)


@bp.get('/health')
def health():
    return jsonify({
        'status': 'ok',
        'team_id': current_app.config['TEAM_ID'],
        'team_name': current_app.config['TEAM_NAME'],
    })