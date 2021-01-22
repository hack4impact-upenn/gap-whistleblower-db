from flask_wtf import Form
from wtforms.validators import InputRequired
from wtforms.fields import (
    StringField,
    SubmitField,
    SelectField,
    TextAreaField,
    BooleanField,
)
from app.models import Tag
from app.utils import CustomSelectField


class SuggestionForm(Form):
    title = StringField(validators=[InputRequired()])
    link = StringField()
    type = SelectField(
        choices=[
            ('', ''),
            ('book', 'Book'),
            ('news_article', 'Article'),
            ('journal_article', 'Journal'),
            ('law', 'Law'),
            ('video', 'Video'),
            ('report', 'Report'),
            ('other', 'Other')
        ], validators=[InputRequired()])
    description = TextAreaField()
    submit = SubmitField()


class SearchForm(Form):
    def __init__(self, **kwargs):
        super(SearchForm, self).__init__(**kwargs)
        self.tags.choices = [(str(t.id), t.tag) for t in Tag.query.all()]
    query = StringField()
    book = BooleanField(default='true')
    news_article = BooleanField(default='true')
    journal_article = BooleanField(default='true')
    law = BooleanField(default='true')
    video = BooleanField(default='true')
    report = BooleanField(default='true')
    other = BooleanField(default='true')
    tags = CustomSelectField(
        choices=[('', '')],
        multiple=True,
        allow_custom=False
    )
    sort_by = CustomSelectField(
        default='Most Relevant',
        choices=[
            ('most_relevant', 'Most Relevant'),
            ('title', 'Title'),
            ('newest', 'Newest'),
            ('oldest', 'Oldest'),
        ], validators=[InputRequired()])
    start_date = StringField()
    end_date = StringField()
