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

class MultipleFileUploadField(StringField):
    pass

class BookForm(Form):
    title = StringField(validators=[InputRequired()]) #title
    ISBN = StringField() #ISBN
    volume = StringField() #volme
    edition = StringField() #edition
    series = StringField() #series
    author_first_name = StringField() #author_first_name
    author_last_name = StringField() #author_last_name
    publisher_name = StringField() #name
    publisher_city = StringField() #city
    publisher_state = StringField() #state
    publisher_country = StringField() #country
    publication_day = IntegerField(validators=[validators.optional()]) #day
    publication_month = SelectField(choices=[('',''), ('January', 'January'), ('February', 'February'),
    ('March', 'March'), ('April', 'April'), ('May', 'May'), ('June', 'June'), ('July', 'July')
    , ('August', 'August'), ('September', 'September'), ('October', 'October'), 
    ('November', 'November'), ('December', 'December')]) #month
    publication_year = IntegerField(validators=[validators.optional()]) #year
    description = TextAreaField() #description
    link = StringField() #link
    file_urls = MultipleFileUploadField()
    submit = SubmitField() 

class ArticleForm(Form):
    title = StringField(validators=[InputRequired()])
    author_first_name = StringField()
    author_last_name = StringField()
    publication_day = IntegerField(validators=[validators.optional()])
    publication_month = SelectField(choices=[('',''), ('January', 'January'), ('February', 'February'),
    ('March', 'March'), ('April', 'April'), ('May', 'May'), ('June', 'June'), ('July', 'July')
    , ('August', 'August'), ('September', 'September'), ('October', 'October'), 
    ('November', 'November'), ('December', 'December')])
    publication_year = IntegerField(validators=[validators.optional()])
    description = TextAreaField()
    link = StringField()
    file_urls = MultipleFileUploadField()
    submit = SubmitField() 

class OtherForm(Form):
    document_type = StringField(validators = [InputRequired()])
    title = StringField(validators=[InputRequired()])
    author_first_name = StringField()
    author_last_name = StringField()
    publication_day = IntegerField(validators=[validators.optional()])
    publication_month = SelectField(choices=[('',''), ('January', 'January'), ('February', 'February'),
    ('March', 'March'), ('April', 'April'), ('May', 'May'), ('June', 'June'), ('July', 'July')
    , ('August', 'August'), ('September', 'September'), ('October', 'October'), 
    ('November', 'November'), ('December', 'December')])
    publication_year = IntegerField(validators=[validators.optional()])
    description = TextAreaField()
    link = StringField()
    file_urls = MultipleFileUploadField()
    submit = SubmitField() 

class CourtForm(Form):
    case_name = StringField(validators=[InputRequired()]) #title 
    court_name = StringField() #name
    case_day = IntegerField(validators=[validators.optional()]) #day
    case_month = SelectField(choices=[('',''), ('January', 'January'), ('February', 'February'),
    ('March', 'March'), ('April', 'April'), ('May', 'May'), ('June', 'June'), ('July', 'July')
    , ('August', 'August'), ('September', 'September'), ('October', 'October'), 
    ('November', 'November'), ('December', 'December')]) #month
    case_year = IntegerField(validators=[validators.optional()]) #year
    court_city = StringField() #city
    court_state = StringField() #state
    court_country = StringField() #country
    description = TextAreaField() #description
    link = StringField() #link
    file_urls = MultipleFileUploadField()
    submit = SubmitField() 

class LawForm(Form):
    law_title = StringField(validators=[InputRequired()]) #title 
    government_body = StringField() #govt_body
    law_section = StringField() #section
    ennactment_day = IntegerField(validators=[validators.optional()]) #day
    ennactment_month = SelectField(choices=[('',''), ('January', 'January'), ('February', 'February'),
    ('March', 'March'), ('April', 'April'), ('May', 'May'), ('June', 'June'), ('July', 'July')
    , ('August', 'August'), ('September', 'September'), ('October', 'October'), 
    ('November', 'November'), ('December', 'December')]) #month
    ennactment_year = IntegerField(validators=[validators.optional()]) #year
    description = TextAreaField() #description
    link = StringField() #link
    file_urls = MultipleFileUploadField()
    submit = SubmitField() 

















