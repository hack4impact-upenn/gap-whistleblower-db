from flask import (Blueprint, abort, flash, redirect, render_template, request, jsonify,
                   url_for)

from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError

from app import db, csrf
from app.contributor.forms import BookForm, ArticleForm, OtherForm, LawForm
from app.decorators import admin_required
from app.models import Document

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

@contributor.route('/submit', methods=['GET', 'POST'])
@login_required
def submit():
    """Book page."""
    book_form = BookForm()
    article_form = ArticleForm()
    law_form = LawForm()
    other_form = OtherForm()

    if request.method == 'POST':
        form_name = request.form['form-name']
        if form_name == 'book_form' and book_form.validate_on_submit():
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
                link = book_form.book_link.data)

            file_urls = book_form.book_file_urls.data

            db.session.add(book)
            db.session.commit()
            flash(
                'Book \"{}\" successfully created'.format(
                    book_form.book_title.data), 'form-success')
            return render_template('contributor/submit.html', book_form=book_form,
            article_form=article_form, law_form=law_form, other_form=other_form, active="book")

        if form_name == 'article_form' and article_form.validate_on_submit():
            article = Document(
                doc_type = "article",
                title = article_form.article_title.data,
                author_first_name = article_form.article_author_first_name.data,
                author_last_name = article_form.article_author_last_name.data,
                posted_by = current_user.id,
                last_edited_by = current_user.id,
                publication = article_form.article_publication.data,
                day = article_form.article_publication_day.data,
                month = article_form.article_publication_month.data,
                year = article_form.article_publication_year.data,
                description = article_form.article_description.data,
                link = article_form.article_link.data)

            file_urls = article_form.article_file_urls.data

            db.session.add(article)
            db.session.commit()
            flash(
                'Article \"{}\" successfully created'.format(
                    article_form.article_title.data), 'form-success')
            return render_template('contributor/submit.html', book_form=book_form,
            article_form=article_form, law_form=law_form, other_form=other_form, active="article")

        if form_name == 'law_form' and law_form.validate_on_submit():

            law = Document(
                doc_type = "law",
                title = law_form.law_title.data,
                govt_body = law_form.law_government_body.data,
                section = law_form.law_section.data,
                posted_by = current_user.id,
                last_edited_by = current_user.id,
                day = law_form.law_enactment_day.data,
                month = law_form.law_enactment_month.data,
                year = law_form.law_enactment_year.data,
                description = law_form.law_description.data,
                link = law_form.law_link.data)

            file_urls = law_form.law_file_urls.data

            db.session.add(law)
            db.session.commit()
            flash(
                'Law \"{}\" successfully created'.format(
                    law_form.law_title.data), 'form-success')
            return render_template('contributor/submit.html', book_form=book_form,
            article_form=article_form, law_form=law_form, other_form=other_form, active="law")

        if form_name == 'other_form' and other_form.validate_on_submit():
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
                other_type = other_form.other_document_type.data)

            file_urls = other_form.other_file_urls.data

            db.session.add(other)
            db.session.commit()
            flash(
                'Other resource\"{}\" successfully created'.format(
                    other_form.other_title.data), 'form-success')
            return render_template('contributor/submit.html', book_form=book_form,
            article_form=article_form, law_form=law_form, other_form=other_form, active="other")


    return render_template('contributor/submit.html', book_form=book_form,
    article_form=article_form, law_form=law_form, other_form=other_form, active="book")


@contributor.route('sign-s3/')
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

