import json
import time
import boto3
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    jsonify,
    url_for
)
from app.models import (
    EditableHTML,
    Document,
    Saved,
    User,
    Suggestion,
    Idf,
    Tagged
)
from flask_login import current_user, login_required
from app.decorators import contributor_required, admin_required
from app.main.forms import SuggestionForm, SearchForm
from app import db

import atexit
from apscheduler.schedulers.background import BackgroundScheduler
import requests
import validators
import math
import logging

from nltk.stem.snowball import SnowballStemmer

from sqlalchemy import or_, and_

import os
import nltk
nltk.data.path.append(os.environ.get('NLTK_DATA'))

main = Blueprint('main', __name__)
logger = logging.getLogger('werkzeug')


BROKEN = 0
NOT_BROKEN = 1
IGNORE = 2


def role():
    if current_user.is_authenticated and current_user.role_id == 3:
        return 'admin'
    else:
        return 'not_admin'


@main.route('/', methods=['GET', 'POST'])
def index():
    idf = Idf.query.all()

    form = SearchForm()

    stemmer = SnowballStemmer("english", ignore_stopwords=True)

    results = Document.query.filter_by(
        document_status="published"
    ).order_by(Document.last_edited_date.desc()).all()

    if form.validate_on_submit():
        conditions = []
        conditions.append(Document.document_status == 'published')
        types = [
            'book',
            'news_article',
            'journal_article',
            'law',
            'video',
            'report',
            'other'
        ]
        selected_types = []
        for t in types:
            if form.data[str(t)]:
                selected_types.append(t)

        if len(selected_types) > 0:
            conditions.append(Document.doc_type.in_(selected_types))

        if form.tags.data != '':
            or_conditions = []
            the_tags = form.tags.data.split(',')
            for tag in the_tags:
                or_conditions.append(Document.tags.any(Tagged.tag_name == tag))
            or_condition = or_(*or_conditions)
            conditions.append(or_condition)

        query = form.query.data.lower()
        if len(query) > 0:
            stop_words = set(stopwords.words('english'))
            word_tokens = word_tokenize(query)
            filtered_query = [
                stemmer.stem(w) for w in word_tokens if w not in stop_words
            ]
            docs = get_docs(filtered_query)
            conditions.append(Document.id.in_(docs))

        month_dict = {
            'January': 1,
            'February': 2,
            'March': 3,
            'April': 4,
            'May': 5,
            'June': 6,
            'July': 7,
            'August': 8,
            'September': 9,
            'October': 10,
            'November': 11,
            'December': 12
        }

        if len(form.start_date.data) > 0:
            start_date = form.start_date.data.split(' ')
            start_month = month_dict.get(start_date[0])
            start_day = start_date[1][:-1]
            start_year = start_date[2]
            start = (start_year, start_month, start_day)
            conditions.append(Document.is_after(start))

        if len(form.end_date.data) > 0:
            end_date = form.end_date.data.split(' ')
            end_month = month_dict.get(end_date[0])
            end_day = end_date[1][:-1]
            end_year = end_date[2]
            end = (end_year, end_month, end_day)
            conditions.append(Document.is_before(end))

        results = Document.query.filter(
                and_(*conditions)
            ).order_by(
                Document.last_edited_date.desc()
            ).all()

        if len(query) > 0:
            idf = {}
            num_docs = len(Document.query.all())
            for w in filtered_query:
                idf_score = Idf.query.get(w)
                if idf_score:
                    idf[w] = math.log(num_docs/(1+len(Idf.query.get(w).docs)))

            for r in results:
                r.score = 0
                for w in filtered_query:
                    tf = r.tf.get(w)
                    if tf:
                        r.score += tf * idf.get(w)

            results.sort(key=lambda x: x.score, reverse=True)

        return render_template(
            'main/index.html',
            search_results=results,
            form=form,
            idf=idf
        )

    return render_template(
        'main/index.html',
        search_results=results,
        form=form,
        idf=idf
    )


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
            title=form.title.data,
            link=form.link.data,
            doc_type=form.type.data,
            description=form.description.data)
        db.session.add(suggestion)
        db.session.commit()
        flash('Suggestion \"{}\" successfully created'.format(
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
        return jsonify(status='Save')
    else:
        saved = Saved(user_id=user_id, doc_id=id)
        db.session.add(saved)
        return jsonify(status='Unsave')


@main.route('/resource/<int:id>', methods=['GET', 'POST'])
def resource(id, from_saved=False):
    resource = Document.query.get(id)
    user_id = getattr(current_user, 'id', None)
    saved_objs = Saved.query.filter_by(user_id=user_id, doc_id=id)
    saved = bool(user_id) and bool(saved_objs.all())
    return render_template(
        'main/resource.html',
        resource=resource,
        user_id=user_id,
        saved=saved,
        from_saved=from_saved,
        user_type=role()
    )


@main.route('/saved')
@login_required
def review_saved():
    user_id = current_user.id
    user = User.query.get(user_id)
    saved = user.saved.order_by(Document.last_edited_date)
    return render_template('main/review_saved.html', saved=saved)


def check_dead_links():
    header = {'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.88 Safari/537.36'}
    docs = Document.query.filter(Document.document_status == "published").filter(Document.broken_link < 2).all()
    for doc in docs:
        if validators.url(doc.link):
            try:
                r = requests.get(doc.link, headers=header, timeout=5.0)
                if r.status_code >= 400:
                    doc.broken_link = BROKEN
                else:
                    doc.broken_link = NOT_BROKEN
            except Exception:
                doc.broken_link = BROKEN
        elif not doc.link:
            doc.broken_link = NOT_BROKEN
        else:
            doc.broken_link = BROKEN
        db.session.commit()


def get_docs(query):
    search_docs = []
    for w in query:
        additional_docs = Idf.query.get(w)
        if additional_docs:
            search_docs.extend(additional_docs.docs)
    return search_docs


@main.route('/sign-s3/')
@admin_required
@contributor_required
@login_required
def sign_s3():
    # Load necessary information into the application
        S3_BUCKET = os.environ.get('S3_BUCKET')
        S3_REGION = os.environ.get('S3_REGION')
        AWS_ACCESS_KEY = os.environ.get('AWS_ACCESS_KEY')
        AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
        TARGET_FOLDER = 'json/'
        # Load required dat a from the request
        pre_file_name = request.args.get('file-name')
        file_name = ''.join(pre_file_name.split('.')[:-1]) +\
            str(time.time()).replace('.',  '-') + '.' +  \
            ''.join(pre_file_name.split('.')[-1:])
        file_type = request.args.get('file-type')

        # Initialise the S3 client
        s3 = boto3.client(
            's3',
            region_name=S3_REGION,
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY)

        # Generate and return the presigned URL
        presigned_post = s3.generate_presigned_post(
            Bucket=S3_BUCKET,
            Key=TARGET_FOLDER + file_name,
            Fields={
                "acl": "public-read",
                "Content-Type": file_type
            },
            Conditions=[
                {"acl": "public-read"},
                {"Content-Type": file_type}
            ],
            ExpiresIn=60000
        )
        # Return the data to the client
        return json.dumps({
            'data':
            presigned_post,
            'url_upload':
            'https://%s.s3-%s.amazonaws.com' % (S3_BUCKET, S3_REGION),
            'url':
            'https://%s.s3.%s.amazonaws.com/json/%s' % (
                S3_BUCKET,
                S3_REGION,
                file_name
            )
        })

# scheduler = BackgroundScheduler()
# scheduler.add_job(func=check_dead_links, trigger="interval", seconds=3600)
# scheduler.start()
# atexit.register(lambda: scheduler.shutdown())
