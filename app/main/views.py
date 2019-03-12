from flask import Blueprint, request, render_template
import json
from random import randint
import time
import boto3
from app.models import EditableHTML, Document
# import flask_whooshalchemyplus as whooshalchemy
# from flask_whooshee import Whooshee

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