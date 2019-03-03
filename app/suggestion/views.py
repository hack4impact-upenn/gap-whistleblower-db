from flask import (Blueprint, abort, flash, redirect, render_template, request,
                   url_for)

from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError

from app import db
from app.suggestion.forms import SuggestionForm
from app.decorators import admin_required

suggestion = Blueprint('suggestion', __name__)


@suggestion.route('/')
def index():
    """Suggestion page."""
    form = SuggestionForm()
    return render_template(
        'suggestion/index.html',
        form=form)
