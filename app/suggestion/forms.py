from flask_wtf import Form
from wtforms.fields import StringField, SubmitField, TextAreaField, SelectField
from wtforms.validators import InputRequired

from app import db
from app.models import Suggestion

class SuggestionForm(Form):
    title = StringField(validators=[InputRequired()])
    link = StringField()
    type = SelectField(choices=[('book', 'Book'), ('article', 'Article'),
    ('research', 'Research Paper'), ('law', 'Law'), ('other', 'Other')])
    description = TextAreaField()
    submit = SubmitField()
