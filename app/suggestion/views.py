from flask import (Blueprint, abort, flash, redirect, render_template, request,
                   url_for)

from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError

from app import db
from app.suggestion.forms import SuggestionForm
from app.decorators import admin_required
from app.models import Suggestion

suggestion = Blueprint('suggestion', __name__)


@suggestion.route('/', methods=['GET', 'POST'])
def index():
    """Suggestion page."""
    form = SuggestionForm()

    if form.validate_on_submit():
        suggestion = Suggestion(
            title=form.title.data, link=form.link.data,
            description=form.description.data)
        db.session.add(suggestion)
        db.session.commit()
        flash(
            'Suggestion \"{}\" successfully created'.format(
                form.title.data), 'form-success')
        return render_template(
            'suggestion/index.html', form=form)

    return render_template('suggestion/index.html', form=form)
