from flask_wtf import Form
from wtforms.fields import StringField, SubmitField, TextAreaField, SelectField, IntegerField
from wtforms.validators import InputRequired
from wtforms import validators
from flask_wtf.file import FileField
from app import db

class MultipleFileUploadField(StringField):
    pass

class BookForm(Form):
    book_title = StringField(validators=[InputRequired()]) #title
    book_ISBN = StringField() #ISBN
    book_volume = StringField() #volme
    book_edition = StringField() #edition
    book_series = StringField() #series
    book_author_first_name = StringField() #author_first_name
    book_author_last_name = StringField() #author_last_name
    book_publisher_name = StringField() #name
    book_publisher_city = StringField() #city
    book_publisher_state = StringField() #state
    book_publisher_country = StringField() #country
    book_publication_day = IntegerField(validators=[validators.optional()]) #day
    book_publication_month = SelectField(choices=[('',''), ('January', 'January'), ('February', 'February'),
    ('March', 'March'), ('April', 'April'), ('May', 'May'), ('June', 'June'), ('July', 'July')
    , ('August', 'August'), ('September', 'September'), ('October', 'October'),
    ('November', 'November'), ('December', 'December')]) #month
    book_publication_year = IntegerField(validators=[validators.optional()]) #year
    book_description = TextAreaField() #description
    book_link = StringField() #link
    book_file_urls = MultipleFileUploadField()
    submit_book = SubmitField()

class ArticleForm(Form):
    article_title = StringField(validators=[InputRequired()])
    article_author_first_name = StringField()
    article_author_last_name = StringField()
    article_publication = StringField()
    article_publication_day = IntegerField(validators=[validators.optional()])
    article_publication_month = SelectField(choices=[('',''), ('January', 'January'), ('February', 'February'),
    ('March', 'March'), ('April', 'April'), ('May', 'May'), ('June', 'June'), ('July', 'July')
    , ('August', 'August'), ('September', 'September'), ('October', 'October'),
    ('November', 'November'), ('December', 'December')])
    article_publication_year = IntegerField(validators=[validators.optional()])
    article_description = TextAreaField()
    article_link = StringField()
    article_file_urls = MultipleFileUploadField()
    submit_article = SubmitField()


class LawForm(Form):
    law_title = StringField(validators=[InputRequired()]) #title
    law_government_body = StringField() #govt_body
    law_section = StringField() #section
    law_enactment_day = IntegerField(validators=[validators.optional()]) #day
    law_enactment_month = SelectField(choices=[('',''), ('January', 'January'), ('February', 'February'),
    ('March', 'March'), ('April', 'April'), ('May', 'May'), ('June', 'June'), ('July', 'July')
    , ('August', 'August'), ('September', 'September'), ('October', 'October'),
    ('November', 'November'), ('December', 'December')]) #month
    law_enactment_year = IntegerField(validators=[validators.optional()]) #year
    law_city = StringField() #city
    law_state = StringField() #state
    law_country = StringField()
    law_description = TextAreaField() #description
    law_link = StringField() #link
    law_file_urls = MultipleFileUploadField()
    submit_law = SubmitField()

class OtherForm(Form):
    other_document_type = StringField(validators = [InputRequired()])
    other_title = StringField(validators=[InputRequired()])
    other_author_first_name = StringField()
    other_author_last_name = StringField()
    other_publication_day = IntegerField(validators=[validators.optional()])
    other_publication_month = SelectField(choices=[('',''), ('January', 'January'), ('February', 'February'),
    ('March', 'March'), ('April', 'April'), ('May', 'May'), ('June', 'June'), ('July', 'July')
    , ('August', 'August'), ('September', 'September'), ('October', 'October'),
    ('November', 'November'), ('December', 'December')])
    other_publication_year = IntegerField(validators=[validators.optional()])
    other_description = TextAreaField()
    other_link = StringField()
    other_file_urls = MultipleFileUploadField()
    submit_other = SubmitField()


