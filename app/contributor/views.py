from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from flask_rq import get_queue
from sqlalchemy.exc import IntegrityError

from app import db

from app.decorators import contributor_required
from app.email import send_email

contributor = Blueprint('contributor', __name__)


@contributor.route('/')
@login_required
@contributor_required
def index():
    """Contributor dashboard page."""
    return render_template('contributor/index.html')
