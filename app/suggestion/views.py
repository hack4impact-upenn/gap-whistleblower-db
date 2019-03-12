from flask import (Blueprint, abort, flash, redirect, render_template, request, jsonify,
                   url_for)

from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError

from app import db, csrf
from app.suggestion.forms import SuggestionForm, BookForm, ArticleForm, OtherForm, CourtForm, LawForm
from app.decorators import admin_required
from app.models import Suggestion, Document

import json
import boto3
import boto.s3
import sys
import urllib
import tempfile
from boto.s3.key import Key
import boto.s3.connection
import ssl
from werkzeug import secure_filename

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

@suggestion.route('/book', methods=['GET', 'POST'])
@login_required
def book():
    """Book page."""
    form = BookForm()
    if form.validate_on_submit():
       
        book = Document(
            doc_type = "book",
            title = form.title.data,
            ISBN = form.ISBN.data,
            volume = form.volume.data,
            edition = form.edition.data,
            series = form.series.data,
            author_first_name = form.author_first_name.data,
            author_last_name = form.author_last_name.data,
            posted_by = current_user.id,
            last_edited_by = current_user.id,
            name = form.publisher_name.data,
            state = form.publisher_state.data,
            city = form.publisher_city.data,
            country = form.publisher_country.data,
            day = form.publication_day.data,
            month = form.publication_month.data,
            year = form.publication_year.data,
            description = form.description.data,
            link = form.link.data)

        file_urls = form.file_urls.data
                    
        db.session.add(book)
        db.session.commit()
        flash(
            'Book \"{}\" successfully created'.format(
                form.title.data), 'form-success')
        return render_template(
            'suggestion/book.html', form=form)

    return render_template('suggestion/book.html', form=form)


@suggestion.route('/article', methods=['GET', 'POST'])
@login_required
def article():
    """Article page."""
    form = ArticleForm()
    if form.validate_on_submit():
       
        article = Document(
            doc_type = "article",
            title = form.title.data,
            author_first_name = form.author_first_name.data,
            author_last_name = form.author_last_name.data,
            posted_by = current_user.id,
            last_edited_by = current_user.id,
            day = form.publication_day.data,
            month = form.publication_month.data,
            year = form.publication_year.data,
            description = form.description.data,
            link = form.link.data)

        file_urls = form.file_urls.data
                    
        db.session.add(article)
        db.session.commit()
        flash(
            'Article \"{}\" successfully created'.format(
                form.title.data), 'form-success')
        return render_template(
            'suggestion/article.html', form=form)

    return render_template('suggestion/article.html', form=form)

@suggestion.route('/other', methods=['GET', 'POST'])
@login_required
def other():
    """Other page."""
    form = OtherForm()
    if form.validate_on_submit():
        other = Document(
            doc_type = "other",
            title = form.title.data,
            author_first_name = form.author_first_name.data,
            author_last_name = form.author_last_name.data,
            posted_by = current_user.id,
            last_edited_by = current_user.id,
            day = form.publication_day.data,
            month = form.publication_month.data,
            year = form.publication_year.data,
            description = form.description.data,
            link = form.link.data,
            other_type = form.document_type.data)

        file_urls = form.file_urls.data
                    
        db.session.add(other)
        db.session.commit()
        flash(
            'Other \"{}\" successfully created'.format(
                form.title.data), 'form-success')
        return render_template(
            'suggestion/article.html', form=form)

    return render_template('suggestion/other.html', form=form)

@suggestion.route('/case', methods=['GET', 'POST'])
@login_required
def case():
    """Court case page."""
    form = CourtForm()
    if form.validate_on_submit():
        case = Document(
            doc_type = "case",
            title = form.case_name.data,
            name = form.court_name.data,
            posted_by = current_user.id,
            last_edited_by = current_user.id,
            day = form.case_day.data,
            month = form.case_month.data,
            year = form.case_year.data,
            city = form.court_city.data,
            state = form.court_state.data,
            country = form.court_country.data,
            description = form.description.data,
            link = form.link.data)

        file_urls = form.file_urls.data
                    
        db.session.add(case)
        db.session.commit()
        flash(
            'Case \"{}\" successfully created'.format(
                form.case_name.data), 'form-success')
        return render_template(
            'suggestion/court.html', form=form)

    return render_template('suggestion/court.html', form=form)

@suggestion.route('/law', methods=['GET', 'POST'])
@login_required
def law_form():
    """Law page."""
    form = LawForm()
    if form.validate_on_submit():
       
        article = Document(
            doc_type = "law",
            title = form.law_title.data,
            govt_body = form.government_body.data,
            section = form.law_section.data,
            posted_by = current_user.id,
            last_edited_by = current_user.id,
            day = form.ennactment_day.data,
            month = form.ennactment_month.data,
            year = form.ennactment_year.data,
            description = form.description.data,
            link = form.link.data)

        file_urls = form.file_urls.data
                    
        db.session.add(article)
        db.session.commit()
        flash(
            'Law \"{}\" successfully created'.format(
                form.law_title.data), 'form-success')
        return render_template(
            'suggestion/law.html', form=form)

    return render_template('suggestion/law.html', form=form)




