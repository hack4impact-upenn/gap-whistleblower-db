from flask_wtf import Form
from wtforms.fields import StringField, SubmitField, TextAreaField
from wtforms.validators import InputRequired

from app import db
from app.models import Tag

class TagForm(Form):
    name = StringField(validators=[InputRequired()])
    submit = SubmitField()
