from flask_wtf import Form
from wtforms.fields import StringField, SubmitField, TextAreaField
from wtforms.validators import InputRequired

from app import db
from app.models import Suggestion

class SuggestionForm(Form):
    title = StringField(validators=[InputRequired()])
    link = StringField(validators=[InputRequired()])
    description = TextAreaField()
    submit = SubmitField()
