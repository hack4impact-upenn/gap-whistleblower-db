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
        tag = Tag(tag=form.tag.data)
        db.session.add(tag)
        db.session.commit()
        flash(
            'Tag \"{}\" successfully created'.format(
                form.tag.data), 'form-success')
        tags = Tag.query.all()
        return render_template(
            'tag/index.html', form=form, tags=tags)

    return render_template('tag/index.html', form=form, tags=tags)

@tag.route('/delete/<int:id>', methods=['GET', 'POST'])
def delete_tag(id):
    """Tag Management page."""
    tag = Tag.query.get(id)
    if tag is None:
        abort(404)
    db.session.delete(tag)
    try:
        db.session.commit()
        flash(
            'Tag \"{}\" successfully deleted'.format(
                tag.tag), 'form-success')
    except IntegrityError:
        db.session.rollback()
        flash('Error occurred. Please try again.', 'form-error')
        return redirect(url_for('tag.index'))
    return redirect(url_for('tag.index'))
