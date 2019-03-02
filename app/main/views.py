from flask import Blueprint, request, render_template
from random import randint
from time import sleep
from app.models import EditableHTML, Document

main = Blueprint('main', __name__)

@main.route('/')
def index():
    query = request.args.get('q', '')
    query = ""
    #results = Document.query.whoosh_search(query).all()
    #print(results, "ok")
    Document.generate_fake(10)
    # This just returns an empty list...
    results = Document.query.search('article').all()
    return render_template('main/index.html', search_results=results)

@main.route('/about')
def about():
    editable_html_obj = EditableHTML.get_editable_html('about')
    return render_template(
        'main/about.html', editable_html_obj=editable_html_obj)
