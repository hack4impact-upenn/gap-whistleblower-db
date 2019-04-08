from flask_wtf import Form
from wtforms.validators import InputRequired
from wtforms.fields import (
    PasswordField,
    StringField,
    SubmitField,
    SelectField,
    TextAreaField,
    BooleanField,
    SelectMultipleField
)
from wtforms.fields.html5 import DateField
from app import db

class SaveForm(Form):
    submit = SubmitField(label='Save resource', id='save-btn')

class UnsaveForm(Form):
    submit = SubmitField(label='Unsave resource', id='save-btn')

class SuggestionForm(Form):
    title = StringField(validators=[InputRequired()])
    link = StringField()
    type = SelectField(choices=[('book', 'Book'), ('news article', 'News Article'),
    ('journal article', 'Journal Article'), ('law', 'Law'),  ('video', 'Video'), ('other', 'Other')])
    description = TextAreaField()
    submit = SubmitField()

class SearchForm(Form):
    query = StringField(validators=[InputRequired()])
    book = BooleanField(default='true')
    news_article = BooleanField(default='true')
    journal_article = BooleanField(default='true')
    law = BooleanField(default='true')
    video = BooleanField(default='true')
    other = BooleanField(default='true')
    tags = SelectMultipleField()
    start_date = StringField()
    end_date = StringField()
