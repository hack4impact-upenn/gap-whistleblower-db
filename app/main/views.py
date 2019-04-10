import json
import time
import boto3
from flask import Blueprint, request, render_template, redirect, url_for
from random import randint
from time import sleep
from app.models import EditableHTML, Document, Saved, User, Suggestion, Tag
from flask_login import current_user, login_required
# import flask_whooshalchemyplus as whooshalchemy
# from flask_whooshee import Whooshee
from app.main.forms import SaveForm, UnsaveForm, SuggestionForm, SearchForm
from app import db
from sqlalchemy_searchable import search
from flask_paginate import Pagination

main = Blueprint('main', __name__)


@main.route('/', defaults={'page': 1}, methods=['GET', 'POST'])
@main.route('/<int:page>', methods=['GET', 'POST'])
def index(page):
    form = SearchForm()
    tags = Tag.query.all()
    choices = []
    for t in tags:
        choices.append((t.tag, t.tag))

    form.tags.choices = choices
    results = Document.query.filter_by(document_status="published").paginate(page,10,error_out=False)

    if form.validate_on_submit():
        query = form.query.data
        sql = db.session.query(Document)
        results = search(sql, query)
        return render_template('main/index.html', search_results=results, form=form)

    if not results and page != 1:
        abort(404)

    return render_template('main/index.html', form=form, search_results=results, page=page)

def get_users(results, offset=0, per_page=10):
    return results[offset: offset + per_page]

@main.route('/about')
def about():
    editable_html_obj = EditableHTML.get_editable_html('about')
    return render_template(
        'main/about.html', editable_html_obj=editable_html_obj)


@main.route('/suggestion', methods=['GET', 'POST'])
def suggestion():
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
            'main/suggestion.html', form=form)

    return render_template('main/suggestion.html', form=form)


@main.route('/resource/saved/<int:id>', methods=['GET', 'POST'])
@login_required
def resource_saved(id):
    return resource(id, from_saved=True)

@main.route('/resource/<int:id>', methods=['GET', 'POST'])
def resource(id, from_saved=False):
    resource = Document.query.get(id)
    user_id = getattr(current_user, 'id', None)
    saved_objs = Saved.query.filter_by(user_id=user_id, doc_id=id)
    saved = bool(user_id) and bool(saved_objs.all())
    form = UnsaveForm() if saved else SaveForm()
    if form.validate_on_submit():
        if saved:
            saved_objs.delete()
        else:
            saved = Saved(user_id=user_id, doc_id=id)
            db.session.add(saved)
        db.session.commit()
        return redirect(url_for('main.resource' if not from_saved else 'main.resource_saved', id=id))
    return render_template(
        'main/resource.html', resource=resource, user_id=user_id, saved=saved, form=form, from_saved=from_saved
    )


@main.route('/saved')
@login_required
def review_saved():
    user_id = current_user.id
    user = User.query.get(user_id)
    saved = user.saved
    return render_template('main/review_saved.html', saved=saved)
