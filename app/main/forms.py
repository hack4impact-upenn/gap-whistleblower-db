from flask_wtf import Form
from wtforms.fields import (
    PasswordField,
    StringField,
    SubmitField,
)


class SaveForm(Form):
    submit = SubmitField(label='Save resource', id='save-btn')

class UnsaveForm(Form):
    submit = SubmitField(label='Unsave resource', id='save-btn')