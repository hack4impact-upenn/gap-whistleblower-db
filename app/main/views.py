import json
import time
import boto3
from flask import Blueprint, request, render_template, redirect, url_for
from flask.json import jsonify
from random import randint
from time import sleep
from app.models import EditableHTML, Document, Saved, User, Suggestion, Tag, Idf
from flask_login import current_user, login_required
from app.main.forms import SaveForm, UnsaveForm, SuggestionForm, SearchForm
from app import db
from flask_paginate import Pagination

import atexit
from apscheduler.schedulers.background import BackgroundScheduler
import requests
import validators
import math

import os
import nltk
nltk.data.path.append(os.environ.get('NLTK_DATA'))
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

main = Blueprint('main', __name__)


@main.route('/', methods=['GET', 'POST'])
def index():
    form = SearchForm()
    tags = Tag.query.all()
    idf = Idf.query.all()
    choices = []
    for t in tags:
        choices.append((t.tag, t.tag))
    form.tags.choices = choices

    results = Document.query.filter_by(document_status="published").all()

    if form.validate_on_submit():
        query = form.query.data
        types = ['book', 'news_article', 'journal_article', 'law', 'video', 'report', 'other']
        selected_types = []
        filters = ["document_status is \'published\'"]
        if len(types) > 0:
            for t in types:
                if form.data[str(t)] == True:
                    selected_types.append(t)

        stop_words = set(stopwords.words('english'))
        word_tokens = word_tokenize(query)
        filtered_query = [w for w in word_tokens if not w in stop_words]
        docs = get_docs(filtered_query)

        results = Document.query.filter(Document.document_status=='published', Document.doc_type.in_(selected_types), Document.id.in_(docs)).all()

        idf = {}
        num_docs = len(Document.query.all())
        for w in filtered_query:
            idf_score = Idf.query.get(w)
            if idf_score is not None:
                idf[w] = math.log(num_docs/(1+len(Idf.query.get(w).docs)))

        for r in results:
            r.score = 0;
            for w in filtered_query:
                tf = r.tf.get(w)
                if tf is not None:
                    r.score += tf * idf.get(w)

        results.sort(key=lambda x: x.score, reverse=True)

        return render_template('main/index.html', search_results=results, form=form, idf=idf)

    return render_template('main/index.html', search_results=results, form=form, idf=idf)


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


@main.route('/toggleSave', methods=['POST'])
@login_required
def toggleSave():
    id = request.form['id']
    user_id = current_user.id
    saved_objs = Saved.query.filter_by(user_id=user_id, doc_id=id)
    saved = bool(user_id) and bool(saved_objs.all())
    if saved:
        saved_objs.delete()
    else:
        saved = Saved(user_id=user_id, doc_id=id)
        db.session.add(saved)
    return jsonify(success=True)


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

def check_dead_links():
    docs = Document.query.all()
    for doc in docs:
        if validators.url(doc.link) is True:
            try:
                r = requests.get(doc.link, timeout=5.0)
                if r.status_code in [400, 403, 404, 500, 501]:
                    doc.broken_link = True
                else:
                    doc.broken_link = False
            except:
                doc.broken_link = True
        db.session.commit()

def get_docs(query):
    search_docs = []
    for w in query:
        stuff = Idf.query.get(w)
        if stuff is not None:
            search_docs.extend(stuff.docs)
    return search_docs



# scheduler = BackgroundScheduler()
# scheduler.add_job(func=check_dead_links, trigger="interval", seconds=60)
# scheduler.start()
# Shut down the scheduler when exiting the app
# atexit.register(lambda: scheduler.shutdown())
