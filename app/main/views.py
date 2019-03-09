from flask import Blueprint, request, render_template
from random import randint
from time import sleep
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


