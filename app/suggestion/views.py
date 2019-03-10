from flask import (Blueprint, abort, flash, redirect, render_template, request, jsonify,
                   url_for)

from sqlalchemy.exc import IntegrityError

from app import db, csrf
from app.suggestion.forms import SuggestionForm
from app.models import Suggestion

suggestion = Blueprint('suggestion', __name__)


@suggestion.route('/', methods=['GET', 'POST'])
def index():
    """Suggestion page."""
    form = SuggestionForm()

    if form.validate_on_submit():
        suggestion = Suggestion(
            title=form.title.data, link=form.link.data,
            doc_type = form.type.data, description=form.description.data)
        db.session.add(suggestion)
        db.session.commit()
        flash(
            'Suggestion \"{}\" successfully created'.format(
                form.title.data), 'form-success')
        return render_template(
            'suggestion/index.html', form=form)

    return render_template('suggestion/index.html', form=form)
