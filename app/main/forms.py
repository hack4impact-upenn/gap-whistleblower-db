from flask_wtf import Form
from wtforms.validators import InputRequired
from wtforms.fields import (
    PasswordField,
    StringField,
    SubmitField,
    SelectField,
    TextAreaField
)


class SaveForm(Form):
    submit = SubmitField(label='Save resource', id='save-btn')

class UnsaveForm(Form):
    submit = SubmitField(label='Unsave resource', id='save-btn')

class SuggestionForm(Form):
    title = StringField(validators=[InputRequired()])
    link = StringField()
    type = SelectField(choices=[('book', 'Book'), ('article', 'Article'),
    ('research', 'Research Paper'), ('law', 'Law'), ('other', 'Other')])
    description = TextAreaField()
    submit = SubmitField()
