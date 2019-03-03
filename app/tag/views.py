from flask import (Blueprint, abort, flash, redirect, render_template, request,
                   url_for)

from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError

from app import db
from app.tag.forms import TagForm
from app.decorators import admin_required
from app.models import Tag

tag = Blueprint('tag', __name__)


@tag.route('/', methods=['GET', 'POST'])
def index():
    """Tag Management page."""
    form = TagForm()
    tags = Tag.query.all()

    if form.validate_on_submit():
        tag = Tag(name=form.name.data)
        db.session.add(tag)
        db.session.commit()
        flash(
            'Tag \"{}\" successfully created'.format(
                form.name.data), 'form-success')
        tags = Tag.query.all()
        return render_template(
            'tag/index.html', form=form, tags=tags)

    return render_template('tag/index.html', form=form, tags=tags)
