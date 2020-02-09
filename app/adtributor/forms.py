from flask_wtf import Form
from wtforms import ValidationError, validators
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from wtforms.fields import (
    PasswordField,
    StringField,
    SubmitField,
    TextAreaField,
    SelectField,
    IntegerField,
    BooleanField,
    SelectMultipleField,
    FieldList,
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


class UpdateLinkForm(Form):
    id = IntegerField()
    link = StringField()
    submit = SubmitField()


# Document Submission Forms (copied from contributor/forms.py)
class DraftEntryForm(Form):
    draft_new_book_entry = SubmitField()


class MultipleFileUploadField(StringField):
    pass


class BookForm(Form):
    book_title = StringField(validators=[InputRequired()])
    book_author_first_name = FieldList(
        StringField(validators=[InputRequired()]),
        min_entries=1
    )
    book_author_last_name = FieldList(
        StringField(validators=[InputRequired()]), min_entries=1
    )
    book_editor_first_name = FieldList(
        StringField(), min_entries=1
    )
    book_editor_last_name = FieldList(
        StringField(), min_entries=1
    )
    book_volume = StringField()
    book_edition = StringField()
    book_series = StringField()
    book_publisher = StringField(validators=[InputRequired()])
    book_publication_month = SelectField(choices=[
        ('', ''), ('January', 'January'), ('February', 'February'),
        ('March', 'March'), ('April', 'April'), ('May', 'May'),
        ('June', 'June'), ('July', 'July'), ('August', 'August'),
        ('September', 'September'), ('October', 'October'),
        ('November', 'November'), ('December', 'December')
    ])
    book_publication_year = IntegerField(validators=[InputRequired()])  # year
    book_description = TextAreaField(validators=[InputRequired()])  # description
    book_tags = SelectMultipleField(choices=[('', '')])
    book_link = StringField()  # link
    book_file_urls = MultipleFileUploadField()
    save_book = SubmitField()
    submit_book = SubmitField()

    def __init__(self, **kwargs):
        super(BookForm, self).__init__(**kwargs)
        self.book_tags.choices = [(str(t.id), t.tag) for t in Tag.query.all()]
        self.book_tags.default = kwargs.get('book_tags')


class ArticleForm(Form):
    article_title = StringField(validators=[InputRequired()])
    article_author_first_name = FieldList(
        StringField(validators=[InputRequired()]), min_entries=1
    )
    article_author_last_name = FieldList(
        StringField(validators=[InputRequired()]), min_entries=1
    )
    article_publication = StringField(validators=[InputRequired()])
    article_publication_day = IntegerField(validators=[validators.optional()])
    article_publication_month = SelectField(choices=[
        ('', ''), ('January', 'January'), ('February', 'February'),
        ('March', 'March'), ('April', 'April'), ('May', 'May'),
        ('June', 'June'), ('July', 'July'), ('August', 'August'),
        ('September', 'September'), ('October', 'October'),
        ('November', 'November'), ('December', 'December')
    ])
    article_publication_year = IntegerField(validators=[InputRequired()])
    article_description = TextAreaField(validators=[InputRequired()])
    article_tags = SelectMultipleField(choices=[('', '')])
    article_link = StringField()
    article_file_urls = MultipleFileUploadField()
    save_article = SubmitField()
    submit_article = SubmitField()

    def __init__(self, **kwargs):
        super(ArticleForm, self).__init__(**kwargs)
        self.article_tags.choices = [
            (str(t.id), t.tag) for t in Tag.query.all()
        ]
        self.article_tags.default = kwargs.get('article_tags')


class JournalArticleForm(Form):
    journal_title = StringField(validators=[InputRequired()])
    journal_author_first_name = FieldList(
        StringField(validators=[InputRequired()]), min_entries=1
    )
    journal_author_last_name = FieldList(
        StringField(validators=[InputRequired()]), min_entries=1
    )
    journal_publication = StringField(validators=[InputRequired()])
    journal_volume = StringField()
    journal_issue = StringField()
    journal_start_page = StringField()
    journal_end_page = StringField()
    journal_publication_day = IntegerField(validators=[validators.optional()])
    journal_publication_month = SelectField(choices=[
        ('', ''), ('January', 'January'), ('February', 'February'),
        ('March', 'March'), ('April', 'April'), ('May', 'May'),
        ('June', 'June'), ('July', 'July'), ('August', 'August'),
        ('September', 'September'), ('October', 'October'),
        ('November', 'November'), ('December', 'December')
    ])
    journal_publication_year = IntegerField(validators=[InputRequired()])
    journal_description = TextAreaField(validators=[InputRequired()])
    journal_tags = SelectMultipleField(choices=[('', '')])
    journal_link = StringField()
    journal_file_urls = MultipleFileUploadField()
    save_journal = SubmitField()
    submit_journal = SubmitField()

    def __init__(self, **kwargs):
        super(JournalArticleForm, self).__init__(**kwargs)
        self.journal_tags.choices = [
            (str(t.id), t.tag) for t in Tag.query.all()
        ]
        self.journal_tags.default = kwargs.get('journal_tags')


class LawForm(Form):
    law_title = StringField(validators=[InputRequired()])
    law_citation = StringField(validators=[InputRequired()])
    law_government_body = StringField(validators=[InputRequired()])
    law_section = StringField()
    law_region = StringField()
    law_enactment_day = IntegerField(validators=[validators.optional()])
    law_enactment_month = SelectField(choices=[
        ('', ''), ('January', 'January'), ('February', 'February'),
        ('March', 'March'), ('April', 'April'), ('May', 'May'),
        ('June', 'June'), ('July', 'July'), ('August', 'August'),
        ('September', 'September'), ('October', 'October'),
        ('November', 'November'), ('December', 'December')
    ])
    law_enactment_year = IntegerField()
    law_country = StringField()
    law_description = TextAreaField(validators=[InputRequired()])
    law_tags = SelectMultipleField(choices=[('', '')])
    law_link = StringField()
    law_file_urls = MultipleFileUploadField()
    save_law = SubmitField()
    submit_law = SubmitField()

    def __init__(self, **kwargs):
        super(LawForm, self).__init__(**kwargs)
        self.law_tags.choices = [(str(t.id), t.tag) for t in Tag.query.all()]
        self.law_tags.default = kwargs.get('law_tags')


class VideoForm(Form):
    video_title = StringField(validators=[InputRequired()])
    video_series = StringField()
    director_first_name = FieldList(
        StringField(), min_entries=1
    )
    director_last_name = FieldList(
        StringField(), min_entries=1
    )
    video_source = StringField()
    video_publisher = StringField()
    video_studio = StringField()
    video_country = StringField()
    video_publication_day = IntegerField(validators=[validators.optional()])
    video_publication_month = SelectField(choices=[
        ('', ''), ('January', 'January'), ('February', 'February'),
        ('March', 'March'), ('April', 'April'), ('May', 'May'),
        ('June', 'June'), ('July', 'July'), ('August', 'August'),
        ('September', 'September'), ('October', 'October'),
        ('November', 'November'), ('December', 'December')
    ])
    video_publication_year = IntegerField(validators=[InputRequired()])
    video_description = TextAreaField(validators=[InputRequired()])
    video_tags = SelectMultipleField(choices=[('', '')])
    video_link = StringField()
    video_file_urls = MultipleFileUploadField()
    save_video = SubmitField()
    submit_video = SubmitField()

    def __init__(self, **kwargs):
        super(VideoForm, self).__init__(**kwargs)
        self.video_tags.choices = [(str(t.id), t.tag) for t in Tag.query.all()]
        self.video_tags.default = kwargs.get('video_tags')


class ReportForm(Form):
    report_title = StringField(validators=[InputRequired()])
    report_author_first_name = FieldList(
        StringField(), min_entries=1
    )
    report_author_last_name = FieldList(
        StringField(), min_entries=1
    )
    report_publisher = StringField(validators=[InputRequired()])
    report_publication_day = IntegerField(validators=[validators.optional()])
    report_publication_month = SelectField(choices=[
        ('', ''), ('January', 'January'), ('February', 'February'),
        ('March', 'March'), ('April', 'April'), ('May', 'May'),
        ('June', 'June'), ('July', 'July'), ('August', 'August'),
        ('September', 'September'), ('October', 'October'),
        ('November', 'November'), ('December', 'December')
    ])
    report_publication_year = IntegerField(validators=[InputRequired()])
    report_description = TextAreaField(validators=[InputRequired()])
    report_tags = SelectMultipleField(choices=[('', '')])
    report_link = StringField()
    report_file_urls = MultipleFileUploadField()
    save_report = SubmitField()
    submit_report = SubmitField()

    def __init__(self, **kwargs):
        super(ReportForm, self).__init__(**kwargs)
        self.report_tags.choices = [
            (str(t.id), t.tag) for t in Tag.query.all()
        ]
        self.report_tags.default = kwargs.get('report_tags')


class OtherForm(Form):
    other_document_type = StringField(validators=[InputRequired()])
    other_title = StringField(validators=[InputRequired()])
    other_author_first_name = FieldList(
        StringField(), min_entries=1
    )
    other_author_last_name = FieldList(
        StringField(), min_entries=1
    )
    other_publication_day = IntegerField(validators=[validators.optional()])
    other_publication_month = SelectField(choices=[
        ('', ''), ('January', 'January'), ('February', 'February'),
        ('March', 'March'), ('April', 'April'), ('May', 'May'),
        ('June', 'June'), ('July', 'July'), ('August', 'August'),
        ('September', 'September'), ('October', 'October'),
        ('November', 'November'), ('December', 'December')
    ])
    other_source = StringField(validators=[InputRequired()])
    other_publication_year = IntegerField(validators=[InputRequired()])
    other_description = TextAreaField(validators=[InputRequired()])
    other_tags = SelectMultipleField(choices=[('', '')])
    other_link = StringField()
    other_file_urls = MultipleFileUploadField()
    save_other = SubmitField()
    submit_other = SubmitField()

    def __init__(self, **kwargs):
        super(OtherForm, self).__init__(**kwargs)
        self.other_tags.choices = [(str(t.id), t.tag) for t in Tag.query.all()]
        self.other_tags.default = kwargs.get('other_tags')


class DownloadForm(Form):
    book = BooleanField()
    news_article = BooleanField()
    journal_article = BooleanField()
    law = BooleanField()
    video = BooleanField()
    report = BooleanField()
    other = BooleanField()
    download = SubmitField()
