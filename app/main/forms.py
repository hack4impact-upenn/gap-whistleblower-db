from flask_wtf import Form
from wtforms.validators import InputRequired
from wtforms.fields import (
    PasswordField,
    StringField,
    SubmitField,
    SelectField,
    TextAreaField,
    BooleanField,
    SelectMultipleField,
)
from wtforms.fields.html5 import DateField
from app import db
from app.models import Tag
from app.utils import CustomSelectField

class SaveForm(Form):
    submit = SubmitField(label='Save resource', id='save-btn')

class UnsaveForm(Form):
    submit = SubmitField(label='Unsave resource', id='save-btn')

class SuggestionForm(Form):
    title = StringField(validators=[InputRequired()])
    link = StringField()
    type = SelectField(choices=[('book', 'Book'), ('news_article', 'Article'),
    ('journal_article', 'Journal'), ('law', 'Law'),  ('video', 'Video'), ('report', 'Report'), ('other', 'Other')])
    description = TextAreaField()
    submit = SubmitField()

class SearchForm(Form):
    def __init__(self, **kwargs):
        super(SearchForm, self).__init__(**kwargs)
        self.tags.choices = [(str(t.id), t.tag) for t in Tag.query.all()]
    query = StringField(validators=[InputRequired()])
    book = BooleanField(default='true')
    news_article = BooleanField(default='true')
    journal_article = BooleanField(default='true')
    law = BooleanField(default='true')
    video = BooleanField(default='true')
    report = BooleanField(default='true')
    other = BooleanField(default='true')
    tags = CustomSelectField(choices=[('', '')], multiple=True, allow_custom=False)
    start_date = StringField()
    end_date = StringField()
