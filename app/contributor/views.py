from flask import (Blueprint, abort, flash, redirect, render_template, request, jsonify,
                   url_for)

from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError
from sqlalchemy import update

from app import db, csrf
from app.contributor.forms import BookForm, ArticleForm, OtherForm, LawForm, DraftEntryForm
from app.decorators import admin_required, contributor_required
from app.models import Document, User

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

contributor = Blueprint('contributor', __name__)

@contributor.route('/index',methods=['GET', 'POST'])
@login_required
@contributor_required
def index():
        return render_template('contributor/index.html')

@contributor.route('/my_contributions',methods=['GET', 'POST'])
@login_required
@contributor_required
def my_contributions():
    """Contribution Review page."""
    user_id = current_user.id
    contributions = Document.query.filter(Document.posted_by == user_id)
    return render_template('contributor/my_contributions.html', contributions=contributions)

@contributor.route('/view_all_drafts',methods=['GET', 'POST'])
@login_required
@contributor_required
def view_all_drafts():
    user_id = current_user.id
    contributions = Document.query.filter(Document.posted_by == user_id)
    return render_template('contributor/draft_contributions.html', contributions=contributions)

@contributor.route('/contribution/<int:id>', methods=['GET'])
@login_required
@contributor_required
def contribution(id):
    """Contribution Review page."""
    contribution = Document.query.get(id)
    return render_template('contributor/contribution.html', contribution=contribution)

# 5 different types of draft editing forms
@contributor.route('/contribution/draft/book/<int:id>', methods=['GET', 'POST'])
@login_required
@contributor_required
def view_book_draft(id):
    """Contribution Review page."""
    contribution = Document.query.get(id)
    book_entry = Document.query.filter_by(id=id).first()
    book_form = BookForm(
        doc_type = "book",
        book_title = book_entry.title,
        book_ISBN = book_entry.ISBN,
        book_volume = book_entry.volume,
        book_edition = book_entry.edition,
        book_series = book_entry.series,
        book_author_first_name = book_entry.author_first_name,
        book_author_last_name = book_entry.author_last_name,
        book_publisher_name = book_entry.name,
        book_publisher_state = book_entry.state,
        book_publisher_city = book_entry.city,
        book_publisher_country = book_entry.country,
        book_publication_day = book_entry.day,
        book_publication_month = book_entry.month,
        book_publication_year = book_entry.year,
        book_description = book_entry.description,
        book_link = book_entry.link)
    if request.method == 'POST':
        if book_form.validate_on_submit():
            if "Save Book" in request.form.values():
                book_entry.doc_type = "book"
                book_entry.title = book_form.book_title.data
                book_entry.ISBN = book_form.book_ISBN.data
                book_entry.volume = book_form.book_volume.data
                book_entry.edition = book_form.book_edition.data
                book_entry.series = book_form.book_series.data
                book_entry.author_first_name = book_form.book_author_first_name.data
                book_entry.author_last_name = book_form.book_author_last_name.data
                book_entry.posted_by = current_user.id
                book_entry.last_edited_by = current_user.id
                book_entry.name = book_form.book_publisher_name.data
                book_entry.state = book_form.book_publisher_state.data
                book_entry.city = book_form.book_publisher_city.data
                book_entry.country = book_form.book_publisher_country.data
                book_entry.day = book_form.book_publication_day.data
                book_entry.month = book_form.book_publication_month.data
                book_entry.year = book_form.book_publication_year.data
                book_entry.description = book_form.book_description.data
                book_entry.link = book_form.book_link.data
                book_entry.document_status = "draft"

                db.session.commit()
                flash(
                    'Book \"{}\" successfully saved'.format(
                        book_form.book_title.data), 'form-success')

                return view_all_drafts()

            if "Submit Book" in request.form.values():
                book_entry.doc_type = "book"
                book_entry.title = book_form.book_title.data
                book_entry.ISBN = book_form.book_ISBN.data
                book_entry.volume = book_form.book_volume.data
                book_entry.edition = book_form.book_edition.data
                book_entry.series = book_form.book_series.data
                book_entry.author_first_name = book_form.book_author_first_name.data
                book_entry.author_last_name = book_form.book_author_last_name.data
                book_entry.posted_by = current_user.id
                book_entry.last_edited_by = current_user.id
                book_entry.name = book_form.book_publisher_name.data
                book_entry.state = book_form.book_publisher_state.data
                book_entry.city = book_form.book_publisher_city.data
                book_entry.country = book_form.book_publisher_country.data
                book_entry.day = book_form.book_publication_day.data
                book_entry.month = book_form.book_publication_month.data
                book_entry.year = book_form.book_publication_year.data
                book_entry.description = book_form.book_description.data
                book_entry.link = book_form.book_link.data
                book_entry.document_status = "needs review"

                db.session.commit()
                flash(
                    'Book \"{}\" successfully created'.format(
                        book_form.book_title.data), 'form-success')

                return my_contributions()


    return render_template('contributor/edit_book_draft.html', book_form=book_form, c=contribution)


@contributor.route('/contribution/draft/article/<int:id>', methods=['GET', 'POST'])
@login_required
@contributor_required
def view_article_draft(id):
    contribution = Document.query.get(id)
    article_entry = Document.query.filter_by(id=id).first()
    article_form = ArticleForm(
                    doc_type = "article",
                    article_title = article_entry.title,
                    article_author_first_name = article_entry.author_first_name,
                    article_author_last_name = article_entry.author_last_name,
                    article_publication = article_entry.name,
                    article_publication_day = article_entry.day,
                    article_publication_month = article_entry.month,
                    article_publication_year = article_entry.year,
                    article_description = article_entry.year,
                    article_link = article_entry.link,
                    document_status = "draft")

    if request.method == 'POST':
        if article_form.validate_on_submit():
            if "Save Article" in request.form.values():
                article_entry.doc_type = "article"
                article_entry.title = article_form.article_title.data
                article_entry.author_first_name = article_form.article_author_first_name.data
                article_entry.author_last_name = article_form.article_author_last_name.data
                article_entry.publication = article_form.article_publication.data
                article_entry.day = article_form.article_publication_day.data
                article_entry.month = article_form.article_publication_month.data
                article_entry.year = article_form.article_publication_year.data
                article_entry.description = article_form.article_description.data
                article_entry.link = article_form.article_link.data
                article_entry.document_status = "draft"

                db.session.commit()
                flash(
                    'Article \"{}\" successfully saved'.format(
                        article_form.article_title.data), 'form-success')

                return view_all_drafts()

            if "Submit Article" in request.form.values():
                article_entry.doc_type = "article"
                article_entry.title = article_form.article_title.data
                article_entry.author_first_name = article_form.article_author_first_name.data
                article_entry.author_last_name = article_form.article_author_last_name.data
                article_entry.publication = article_form.article_publication.data
                article_entry.day = article_form.article_publication_day.data
                article_entry.month = article_form.article_publication_month.data
                article_entry.year = article_form.article_publication_year.data
                article_entry.description = article_form.article_description.data
                article_entry.link = article_form.article_link.data
                article_entry.document_status = "needs review"

                db.session.commit()
                flash(
                    'Article \"{}\" successfully created'.format(
                        article_form.article_title.data), 'form-success')

                return my_contributions()

    return render_template('contributor/edit_article_draft.html', article_form=article_form, c=contribution)


    """Contribution Review page."""
    contribution = Document.query.get(id)
    return render_template('contributor/edit_article_draft.html', contribution=contribution)

@contributor.route('/contribution/draft/research/<int:id>', methods=['GET'])
@login_required
@contributor_required
def view_research_draft(id):
    """Contribution Review page."""
    contribution = Document.query.get(id)
    return render_template('contributor/edit_research_draft.html', contribution=contribution)

@contributor.route('/contribution/draft/law/<int:id>', methods=['GET', 'POST'])
@login_required
@contributor_required
def view_law_draft(id):
    """Contribution Review page."""
    contribution = Document.query.get(id)
    law_entry = Document.query.filter_by(id=id).first()

    law_form = LawForm(
        doc_type = "law",
        law_title = law_entry.title,
        law_government_body = law_entry.govt_body,
        law_section = law_entry.section,
        law_enactment_day = law_entry.day,
        law_enactment_month = law_entry.month,
        law_enactment_year = law_entry.year,
        law_city = law_entry.city,
        law_state = law_entry.state,
        law_country = law_entry.country,
        law_description = law_entry.description,
        law_link = law_entry.link,
        document_status = "draft")

    if request.method == 'POST':
        if law_form.validate_on_submit():
            if "Save Law" in request.form.values():
                law_entry.doc_type = "law"
                law_entry.title = law_form.law_title.data
                law_entry.govt_body = law_form.law_government_body.data
                law_entry.section = law_form.law_section.data
                law_entry.day = law_form.law_enactment_day.data
                law_entry.month = law_form.law_enactment_month.data
                law_entry.year = law_form.law_enactment_year.data
                law_entry.city = law_form.law_city.data
                law_entry.state = law_form.law_state.data
                law_entry.country = law_form.law_country.data
                law_entry.description = law_form.law_description.data
                law_entry.link = law_form.law_link.data
                law_entry.document_status = "draft"

                db.session.commit()
                flash(
                    'Law \"{}\" successfully saved'.format(
                        law_form.law_title.data), 'form-success')

                return view_all_drafts()

            if "Submit Law" in request.form.values():
                law_entry.doc_type = "law"
                law_entry.title = law_form.law_title.data
                law_entry.govt_body = law_form.law_government_body.data
                law_entry.section = law_form.law_section.data
                law_entry.day = law_form.law_enactment_day.data
                law_entry.month = law_form.law_enactment_month.data
                law_entry.year = law_form.law_enactment_year.data
                law_entry.city = law_form.law_city.data
                law_entry.state = law_form.law_state.data
                law_entry.country = law_form.law_country.data
                law_entry.description = law_form.law_description.data
                law_entry.link = law_form.law_link.data
                law_entry.document_status = "needs review"

                db.session.commit()
                flash(
                    'Law \"{}\" successfully created'.format(
                        law_form.law_title.data), 'form-success')

                return my_contributions()

    return render_template('contributor/edit_law_draft.html', law_form=law_form, c=contribution)


@contributor.route('/contribution/draft/other/<int:id>', methods=['GET', 'POST'])
@login_required
@contributor_required
def view_other_draft(id):
    contribution = Document.query.get(id)
    other_entry = Document.query.filter_by(id=id).first()
    other_form = OtherForm(
                    doc_type = "other",
                    other_document_type = other_entry.other_type,
                    other_title = other_entry.title,
                    other_author_first_name = other_entry.author_first_name,
                    other_author_last_name = other_entry.author_last_name,
                    other_publication_day = other_entry.day,
                    other_publication_month = other_entry.month,
                    other_publication_year = other_entry.year,
                    other_description = other_entry.year,
                    other_link = other_entry.link,
                    document_status = "draft")

    if request.method == 'POST':
        if other_form.validate_on_submit():
            if "Save Other" in request.form.values():
                other_entry.doc_type = "other"
                other_entry.other_type = other_form.other_document_type.data
                other_entry.title = other_form.other_title.data
                other_entry.author_first_name = other_form.other_author_first_name.data
                other_entry.author_last_name = other_form.other_author_last_name.data
                other_entry.day = other_form.other_publication_day.data
                other_entry.month = other_form.other_publication_month.data
                other_entry.year = other_form.other_publication_year.data
                other_entry.description = other_form.other_description.data
                other_entry.link = other_form.other_link.data
                other_entry.document_status = "draft"

                db.session.commit()
                flash(
                    'Other \"{}\" successfully saved'.format(
                        other_form.other_title.data), 'form-success')

                return view_all_drafts()

            if "Submit Other" in request.form.values():
                other_entry.doc_type = "other"
                other_entry.other_type = other_form.other_document_type.data
                other_entry.title = other_form.other_title.data
                other_entry.author_first_name = other_form.other_author_first_name.data
                other_entry.author_last_name = other_form.other_author_last_name.data
                other_entry.day = other_form.other_publication_day.data
                other_entry.month = other_form.other_publication_month.data
                other_entry.year = other_form.other_publication_year.data
                other_entry.description = other_form.other_description.data
                other_entry.link = other_form.other_link.data
                other_entry.document_status = "needs review"

                db.session.commit()
                flash(
                    'Other \"{}\" successfully created'.format(
                        other_form.other_title.data), 'form-success')

                return my_contributions()

    return render_template('contributor/edit_other_draft.html', other_form=other_form, c=contribution)


@contributor.route('/submit', methods=['GET', 'POST'])
@login_required
@contributor_required
def submit():
    """Book page."""
    book_form = BookForm()
    article_form = ArticleForm()
    law_form = LawForm()
    other_form = OtherForm()

    if request.method == 'POST':

        form_name = request.form['form-name']

        if form_name == 'book_form' and book_form.validate_on_submit():

            if "Save Book" in request.form.values():
                book = Document(
                    doc_type = "book",
                    title = book_form.book_title.data,
                    ISBN = book_form.book_ISBN.data,
                    volume = book_form.book_volume.data,
                    edition = book_form.book_edition.data,
                    series = book_form.book_series.data,
                    author_first_name = book_form.book_author_first_name.data,
                    author_last_name = book_form.book_author_last_name.data,
                    posted_by = current_user.id,
                    last_edited_by = current_user.id,
                    name = book_form.book_publisher_name.data,
                    state = book_form.book_publisher_state.data,
                    city = book_form.book_publisher_city.data,
                    country = book_form.book_publisher_country.data,
                    day = book_form.book_publication_day.data,
                    month = book_form.book_publication_month.data,
                    year = book_form.book_publication_year.data,
                    description = book_form.book_description.data,
                    link = book_form.book_link.data,
                    document_status = "draft")

                db.session.add(book)
                db.session.commit()
                flash(
                    'Book \"{}\" successfully saved'.format(
                        book_form.book_title.data), 'form-success')

                return view_all_drafts()

            if "Submit Book" in request.form.values():
                book = Document(
                    doc_type = "book",
                    title = book_form.book_title.data,
                    ISBN = book_form.book_ISBN.data,
                    volume = book_form.book_volume.data,
                    edition = book_form.book_edition.data,
                    series = book_form.book_series.data,
                    author_first_name = book_form.book_author_first_name.data,
                    author_last_name = book_form.book_author_last_name.data,
                    posted_by = current_user.id,
                    last_edited_by = current_user.id,
                    name = book_form.book_publisher_name.data,
                    state = book_form.book_publisher_state.data,
                    city = book_form.book_publisher_city.data,
                    country = book_form.book_publisher_country.data,
                    day = book_form.book_publication_day.data,
                    month = book_form.book_publication_month.data,
                    year = book_form.book_publication_year.data,
                    description = book_form.book_description.data,
                    link = book_form.book_link.data,
                    document_status = "needs review")

                db.session.add(book)
                db.session.commit()
                flash(
                    'Book \"{}\" successfully created'.format(
                        book_form.book_title.data), 'form-success')

                return my_contributions()

        if form_name == 'article_form' and article_form.validate_on_submit():

            if "Save Article" in request.form.values():
                article = Document(
                doc_type = "article",
                title = article_form.article_title.data,
                author_first_name = article_form.article_author_first_name.data,
                author_last_name = article_form.article_author_last_name.data,
                posted_by = current_user.id,
                last_edited_by = current_user.id,
                name = article_form.article_publication.data,
                day = article_form.article_publication_day.data,
                month = article_form.article_publication_month.data,
                year = article_form.article_publication_year.data,
                description = article_form.article_description.data,
                link = article_form.article_link.data,
                document_status = "draft")

                db.session.add(article)
                db.session.commit()
                flash(
                    'Article \"{}\" successfully saved'.format(
                        article_form.article_title.data), 'form-success')

                return view_all_drafts()

            if "Submit Article" in request.form.values():
                article = Document(
                doc_type = "article",
                title = article_form.article_title.data,
                author_first_name = article_form.article_author_first_name.data,
                author_last_name = article_form.article_author_last_name.data,
                posted_by = current_user.id,
                last_edited_by = current_user.id,
                name = article_form.article_publication.data,
                day = article_form.article_publication_day.data,
                month = article_form.article_publication_month.data,
                year = article_form.article_publication_year.data,
                description = article_form.article_description.data,
                link = article_form.article_link.data,
                document_status = "needs review")

                db.session.add(article)
                db.session.commit()
                flash(
                    'Article \"{}\" successfully submitted'.format(
                        article_form.article_title.data), 'form-success')

                return my_contributions()

        if form_name == 'law_form' and law_form.validate_on_submit():

            if "Save Law" in request.form.values():
                law = Document(
                    doc_type = "law",
                    day =  law_form.law_enactment_day.data,
                    month = law_form.law_enactment_month.data,
                    year = law_form.law_enactment_year.data,
                    posted_by = current_user.id,
                    last_edited_by = current_user.id,
                    title = law_form.law_title.data,
                    description = law_form.law_description.data,
                    city = law_form.law_city.data,
                    state = law_form.law_state.data,
                    country = law_form.law_country.data,
                    link = law_form.law_link.data,
                    govt_body = law_form.law_government_body.data,
                    section = law_form.law_section.data,
                    document_status = "draft"
                )

                db.session.add(law)
                db.session.commit()
                flash(
                    'Law \"{}\" successfully saved'.format(
                        law_form.law_title.data), 'form-success')

                return view_all_drafts()

            if "Submit Law" in request.form.values():
                law = Document(
                    doc_type = "law",
                    day =  law_form.law_enactment_day.data,
                    month = law_form.law_enactment_month.data,
                    year = law_form.law_enactment_year.data,
                    posted_by = current_user.id,
                    last_edited_by = current_user.id,
                    title = law_form.law_title.data,
                    description = law_form.law_description.data,
                    city = law_form.law_city.data,
                    state = law_form.law_state.data,
                    country = law_form.law_country.data,
                    link = law_form.law_link.data,
                    govt_body = law_form.law_government_body.data,
                    section = law_form.law_section.data,
                    document_status = "needs review"
                )

                db.session.add(law)
                db.session.commit()
                flash(
                    'Law \"{}\" successfully submitted'.format(
                        law_form.law_title.data), 'form-success')

                return my_contributions()

        if form_name == 'other_form' and other_form.validate_on_submit():

            if "Save Other" in request.form.values():
                other = Document(
                    doc_type = "other",
                    title = other_form.other_title.data,
                    author_first_name = other_form.other_author_first_name.data,
                    author_last_name = other_form.other_author_last_name.data,
                    posted_by = current_user.id,
                    last_edited_by = current_user.id,
                    day = other_form.other_publication_day.data,
                    month = other_form.other_publication_month.data,
                    year = other_form.other_publication_year.data,
                    description = other_form.other_description.data,
                    link = other_form.other_link.data,
                    other_type = other_form.other_document_type.data,
                    document_status = "draft")

                db.session.add(other)
                db.session.commit()
                flash(
                    'Other \"{}\" successfully saved'.format(
                        law_form.law_title.data), 'form-success')

                return view_all_drafts()

            if "Submit Other" in request.form.values():
                other = Document(
                    doc_type = "other",
                    title = other_form.other_title.data,
                    author_first_name = other_form.other_author_first_name.data,
                    author_last_name = other_form.other_author_last_name.data,
                    posted_by = current_user.id,
                    last_edited_by = current_user.id,
                    day = other_form.other_publication_day.data,
                    month = other_form.other_publication_month.data,
                    year = other_form.other_publication_year.data,
                    description = other_form.other_description.data,
                    link = other_form.other_link.data,
                    other_type = other_form.other_document_type.data,
                    document_status = "needs review")

                db.session.add(other)
                db.session.commit()
                flash(
                    'Law \"{}\" successfully submitted'.format(
                        law_form.law_title.data), 'form-success')

                return my_contributions()

    return render_template('contributor/submit.html', book_form=book_form,
    article_form=article_form, law_form=law_form, other_form=other_form, active="book")


@contributor.route('sign-s3/')
@login_required
@contributor_required
def sign_s3():
    # Load necessary information into the application
        S3_BUCKET = "h4i-test2"
        TARGET_FOLDER = 'json/'
        # Load required data from the request
        pre_file_name = request.args.get('file-name')
        file_name = ''.join(pre_file_name.split('.')[:-1]) +\
            str(time.time()).replace('.',  '-') + '.' +  \
            ''.join(pre_file_name.split('.')[-1:])
        file_type = request.args.get('file-type')

        # Initialise the S3 client
        s3 = boto3.client('s3', 'us-east-2')

        # Generate and return the presigned URL
        presigned_post = s3.generate_presigned_post(
        Bucket=S3_BUCKET,
        Key=TARGET_FOLDER + file_name,
        Fields={
            "acl": "public-read",
            "Content-Type": file_type
        },
        Conditions=[{
            "acl": "public-read"
        }, {
            "Content-Type": file_type
        }],
        ExpiresIn=60000)

        # Return the data to the client
        return json.dumps({
            'data':
            presigned_post,
            'url_upload':
            'https://%s.%s.amazonaws.com' % (S3_BUCKET, S3_REGION),
            'url':
            'https://%s.amazonaws.com/%s/json/%s' % (S3_REGION, S3_BUCKET,
                                                     file_name)
        })
