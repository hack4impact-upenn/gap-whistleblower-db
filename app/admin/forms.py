from flask_wtf import Form
from wtforms import ValidationError, validators
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from wtforms.fields import (
    PasswordField,
    StringField,
    SubmitField,
    TextAreaField,
    SelectField,
    IntegerField
)
from wtforms.fields.html5 import EmailField
from wtforms.validators import (
    Email,
    EqualTo,
    InputRequired,
    Length,
)
from app import db
from app.models import Role, User, Tag
from flask_wtf.file import FileField


class ChangeUserEmailForm(Form):
    email = EmailField(
        'New email', validators=[InputRequired(),
                                 Length(1, 64),
                                 Email()])
    submit = SubmitField('Update email')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')


class ChangeAccountTypeForm(Form):
    role = QuerySelectField(
        'New account type',
        validators=[InputRequired()],
        get_label='name',
        query_factory=lambda: db.session.query(Role).order_by('permissions'))
    submit = SubmitField('Update role')


class InviteUserForm(Form):
    role = QuerySelectField(
        'Account type',
        validators=[InputRequired()],
        get_label='name',
        query_factory=lambda: db.session.query(Role).order_by('permissions'))
    first_name = StringField(
        'First name', validators=[InputRequired(),
                                  Length(1, 64)])
    last_name = StringField(
        'Last name', validators=[InputRequired(),
                                 Length(1, 64)])
    email = EmailField(
        'Email', validators=[InputRequired(),
                             Length(1, 64),
                             Email()])
    submit = SubmitField('Invite')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')


class NewUserForm(InviteUserForm):
    password = PasswordField(
        'Password',
        validators=[
            InputRequired(),
            EqualTo('password2', 'Passwords must match.')
        ])
    password2 = PasswordField('Confirm password', validators=[InputRequired()])

    submit = SubmitField('Create')

class TagForm(Form):
    tag = StringField(validators=[InputRequired()])
    submit = SubmitField()


# Document Submission Forms (copied from contributor/forms.py)


class DraftEntryForm(Form):
    draft_new_book_entry = SubmitField()


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
    save_book = SubmitField()
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
    save_article = SubmitField()
    submit_article = SubmitField()

class JournalArticleForm(Form):
    article_title = StringField(validators=[InputRequired()])
    article_author_first_name = StringField()
    article_author_last_name = StringField()
    publisher_name = StringField()
    volume = StringField()
    start_page = IntegerField()
    end_page = IntegerField()
    article_publication_day = IntegerField(validators=[validators.optional()])
    article_publication_month = SelectField(choices=[('',''), ('January', 'January'), ('February', 'February'),
    ('March', 'March'), ('April', 'April'), ('May', 'May'), ('June', 'June'), ('July', 'July')
    , ('August', 'August'), ('September', 'September'), ('October', 'October'),
    ('November', 'November'), ('December', 'December')])
    article_publication_year = IntegerField(validators=[validators.optional()])
    article_description = TextAreaField()
    article_link = StringField()
    article_file_urls = MultipleFileUploadField()
    save_article = SubmitField()
    submit_article = SubmitField()


class LawForm(Form):
    law_title = StringField(validators=[InputRequired()]) #title
    law_citation = StringField(validators=[InputRequired()]) #citation
    law_government_body = StringField() #govt_body
    law_section = StringField() #section
    law_region = StringField() #region
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
    save_law = SubmitField()
    submit_law = SubmitField()

class VideoForm(Form):
    video_title = StringField(validators=[InputRequired()])
    director_first_name = StringField()
    director_last_name = StringField()
    video_post_source = StringField()
    video_city = StringField()
    video_country = StringField()
    video_publisher = StringField()
    video_publication_year = StringField()
    video_description = TextAreaField()
    video_link = StringField()
    video_file_urls = MultipleFileUploadField()
    save_video = SubmitField()
    submit_video = SubmitField()

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
    save_other = SubmitField()
    submit_other = SubmitField()
