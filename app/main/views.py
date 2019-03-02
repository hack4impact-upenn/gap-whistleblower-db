from flask import Blueprint, request, render_template

from app.models import EditableHTML, Document

main = Blueprint('main', __name__)

@main.route('/')
def index():
    return render_template('main/index.html')

@main.route('/test')
def test():
    #query = request.args.get('q', '')
    #Document.generate_fake(100)
    #results = Document.query.whoosh_search("").all()
    results = Document.query.first()
    print(results)
    if results is not None:
        x = "pls"
        y = repr(results)
        print(y)
        return y
    return "u failed"

@main.route('/about')
def about():
    editable_html_obj = EditableHTML.get_editable_html('about')
    return render_template(
        'main/about.html', editable_html_obj=editable_html_obj)
