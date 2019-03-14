from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import (
    current_user,
    login_required,
    login_user,
    logout_user,
)

account = Blueprint('saved', __name__)

@account.route('/saved')
@login_required
def saved():
    return 'hi'