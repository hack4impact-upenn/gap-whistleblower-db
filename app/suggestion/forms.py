from flask_wtf import Form
from wtforms.fields import StringField, SubmitField, TextAreaField, SelectField, IntegerField
from wtforms.validators import InputRequired
from wtforms import validators
from flask_wtf.file import FileField
from app import db
from app.models import Suggestion, Document

class SuggestionForm(Form):
    title = StringField(validators=[InputRequired()])
    link = StringField()
    type = SelectField(choices=[('book', 'Book'), ('article', 'Article'),
    ('research', 'Research Paper'), ('law', 'Law'), ('other', 'Other')])
    description = TextAreaField()
    submit = SubmitField()
