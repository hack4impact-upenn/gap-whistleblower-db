import json
import time
import boto3
from flask import Blueprint, request, render_template, redirect, url_for
from random import randint
from time import sleep
from app.models import EditableHTML, Document, Saved, User
from flask_login import current_user, login_required
# import flask_whooshalchemyplus as whooshalchemy
# from flask_whooshee import Whooshee
from app.main.forms import SaveForm, UnsaveForm
from app import db

main = Blueprint('main', __name__)


@main.route('/')
def index():
    return render_template('main/index.html', search_results=[])


@main.route('/about')
def about():
    editable_html_obj = EditableHTML.get_editable_html('about')
    return render_template(
        'main/about.html', editable_html_obj=editable_html_obj)

@main.route('/sign-s3')
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
        S3_REGION = "us-east-2"
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
            'https://s3.%s.amazonaws.com/%s/' % (S3_REGION, S3_BUCKET),
            'url':
            'https://s3.%s.amazonaws.com/%s/json/%s' % (S3_REGION, S3_BUCKET,
                file_name)
        })

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