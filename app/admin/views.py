from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from flask_rq import get_queue
from sqlalchemy.exc import IntegrityError

from app import db
from app.admin.forms import (
    ChangeAccountTypeForm,
    ChangeUserEmailForm,
    InviteUserForm,
    NewUserForm,
    TagForm
)
from app.contributor.forms import BookForm, ArticleForm, OtherForm, LawForm, \
    DraftEntryForm, JournalArticleForm, VideoForm
from app.decorators import admin_required
from app.email import send_email
from app.models import EditableHTML, Role, User, Tag, Suggestion, Document

admin = Blueprint('admin', __name__)


@admin.route('/')
@login_required
@admin_required
def index():
    """Admin dashboard page."""
    return render_template('admin/index.html')


@admin.route('/new-user', methods=['GET', 'POST'])
@login_required
@admin_required
def new_user():
    """Create a new user."""
    form = NewUserForm()
    if form.validate_on_submit():
        user = User(
            role=form.role.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data,
            password=form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('User {} successfully created'.format(user.full_name()),
              'form-success')
    return render_template('admin/new_user.html', form=form)


@admin.route('/invite-user', methods=['GET', 'POST'])
@login_required
@admin_required
def invite_user():
    """Invites a new user to create an account and set their own password."""
    form = InviteUserForm()
    if form.validate_on_submit():
        user = User(
            role=form.role.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data)
        db.session.add(user)
        db.session.commit()
        token = user.generate_confirmation_token()
        invite_link = url_for(
            'account.join_from_invite',
            user_id=user.id,
            token=token,
            _external=True)
        get_queue().enqueue(
            send_email,
            recipient=user.email,
            subject='You Are Invited To Join',
            template='account/email/invite',
            user=user,
            invite_link=invite_link,
        )
        flash('User {} successfully invited'.format(user.full_name()),
              'form-success')
    return render_template('admin/new_user.html', form=form)


@admin.route('/users')
@login_required
@admin_required
def registered_users():
    """View all registered users."""
    users = User.query.all()
    roles = Role.query.all()
    return render_template(
        'admin/registered_users.html', users=users, roles=roles)


@admin.route('/user/<int:user_id>')
@admin.route('/user/<int:user_id>/info')
@login_required
@admin_required
def user_info(user_id):
    """View a user's profile."""
    user = User.query.filter_by(id=user_id).first()
    if user is None:
        abort(404)
    return render_template('admin/manage_user.html', user=user)


@admin.route('/user/<int:user_id>/change-email', methods=['GET', 'POST'])
@login_required
@admin_required
def change_user_email(user_id):
    """Change a user's email."""
    user = User.query.filter_by(id=user_id).first()
    if user is None:
        abort(404)
    form = ChangeUserEmailForm()
    if form.validate_on_submit():
        user.email = form.email.data
        db.session.add(user)
        db.session.commit()
        flash('Email for user {} successfully changed to {}.'.format(
            user.full_name(), user.email), 'form-success')
    return render_template('admin/manage_user.html', user=user, form=form)


@admin.route(
    '/user/<int:user_id>/change-account-type', methods=['GET', 'POST'])
@login_required
@admin_required
def change_account_type(user_id):
    """Change a user's account type."""
    if current_user.id == user_id:
        flash('You cannot change the type of your own account. Please ask '
              'another administrator to do this.', 'error')
        return redirect(url_for('admin.user_info', user_id=user_id))

    user = User.query.get(user_id)
    if user is None:
        abort(404)
    form = ChangeAccountTypeForm()
    if form.validate_on_submit():
        user.role = form.role.data
        db.session.add(user)
        db.session.commit()
        flash('Role for user {} successfully changed to {}.'.format(
            user.full_name(), user.role.name), 'form-success')
    return render_template('admin/manage_user.html', user=user, form=form)


@admin.route('/user/<int:user_id>/delete')
@login_required
@admin_required
def delete_user_request(user_id):
    """Request deletion of a user's account."""
    user = User.query.filter_by(id=user_id).first()
    if user is None:
        abort(404)
    return render_template('admin/manage_user.html', user=user)


@admin.route('/user/<int:user_id>/_delete')
@login_required
@admin_required
def delete_user(user_id):
    """Delete a user's account."""
    if current_user.id == user_id:
        flash('You cannot delete your own account. Please ask another '
              'administrator to do this.', 'error')
    else:
        user = User.query.filter_by(id=user_id).first()
        db.session.delete(user)
        db.session.commit()
        flash('Successfully deleted user %s.' % user.full_name(), 'success')
    return redirect(url_for('admin.registered_users'))


@admin.route('/_update_editor_contents', methods=['POST'])
@login_required
@admin_required
def update_editor_contents():
    """Update the contents of an editor."""

    edit_data = request.form.get('edit_data')
    editor_name = request.form.get('editor_name')

    editor_contents = EditableHTML.query.filter_by(
        editor_name=editor_name).first()
    if editor_contents is None:
        editor_contents = EditableHTML(editor_name=editor_name)
    editor_contents.value = edit_data

    db.session.add(editor_contents)
    db.session.commit()

    return 'OK', 200

@admin.route('/tag', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_tags():
    """Tag Management page."""
    form = TagForm()
    tags = Tag.query.all()

    if form.validate_on_submit():
        tag = Tag(tag=form.tag.data)
        db.session.add(tag)
        db.session.commit()
        flash(
            'Tag \"{}\" successfully created'.format(
                form.tag.data), 'form-success')
        tags = Tag.query.all()
        return render_template(
            'admin/manage_tags.html', form=form, tags=tags)

    return render_template('admin/manage_tags.html', form=form, tags=tags)

@admin.route('tag/delete/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def delete_tag(id):
    """Tag Deletion endpoint."""
    tag = Tag.query.get(id)
    if tag is None:
        abort(404)
    db.session.delete(tag)
    try:
        db.session.commit()
        flash(
            'Tag \"{}\" successfully deleted'.format(
                tag.tag), 'form-success')
    except IntegrityError:
        db.session.rollback()
        flash('Error occurred. Please try again.', 'form-error')
        return redirect(url_for('admin.manage_tags'))
    return redirect(url_for('admin.manage_tags'))

@admin.route('/suggestion', methods=['GET', 'POST'])
@login_required
@admin_required
def review_suggestions():
    """Suggestion Review page."""
    suggestions = Suggestion.query.order_by(Suggestion.id.desc()).all()
    return render_template('admin/review_suggestions.html', suggestions=suggestions)

@admin.route('/suggestion/<int:id>', methods=['GET'])
@login_required
@admin_required
def suggestion(id):
    """Suggestion Review page."""
    suggestion = Suggestion.query.get(id)
    return render_template('admin/suggestion.html', suggestion=suggestion)

@admin.route('/suggestion/delete/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def delete_suggestion(id):
    """Suggestion Deletion endpoint."""
    suggestion = Suggestion.query.get(id)
    if suggestion is None:
        abort(404)
    db.session.delete(suggestion)
    try:
        db.session.commit()
        flash(
            'Suggestion {} successfully deleted'.format(
                suggestion.title), 'form-success')
    except IntegrityError:
        db.session.rollback()
        flash('Error occurred. Please try again.', 'form-error')
        return redirect(url_for('admin.review_suggestions'))
    return redirect(url_for('admin.review_suggestions'))


@admin.route('/contribution', methods=['GET', 'POST'])
@login_required
@admin_required
def review_contributions():
    """Contribution Review page."""
    contributions = Document.query.order_by(Document.id.desc()).all()
    return render_template('admin/review_contributions.html', contributions=contributions)


@admin.route('/contribution/<int:id>', methods=['GET'])
@login_required
@admin_required
def contribution(id):
    """Contribution Review page."""
    contribution = Document.query.get(id)
    return render_template('admin/contribution.html', contribution=contribution)


def save_or_submit_doc(form, doc_type, submit=False):
    if doc_type == 'news article':
        article_form = form
        article = Document(
            doc_type="news article",
            title=article_form.article_title.data,
            author_first_name=article_form.article_author_first_name.data,
            author_last_name=article_form.article_author_last_name.data,
            posted_by=current_user.id,
            last_edited_by=current_user.id,
            name=article_form.article_publication.data,
            day=article_form.article_publication_day.data,
            month=article_form.article_publication_month.data,
            year=article_form.article_publication_year.data,
            description=article_form.article_description.data,
            link=article_form.article_link.data,
            document_status="draft" if not submit else "published")
        db.session.add(article)
        db.session.commit()
        flash(
            'Article \"{}\" successfully submitted'.format(
                article_form.article_title.data), 'form-success')
    elif doc_type == 'book':
        book_form = form
        book = Document(
            doc_type="book",
            title=book_form.book_title.data,
            ISBN=book_form.book_ISBN.data,
            volume=book_form.book_volume.data,
            edition=book_form.book_edition.data,
            series=book_form.book_series.data,
            author_first_name=book_form.book_author_first_name.data,
            author_last_name=book_form.book_author_last_name.data,
            posted_by=current_user.id,
            last_edited_by=current_user.id,
            name=book_form.book_publisher_name.data,
            state=book_form.book_publisher_state.data,
            city=book_form.book_publisher_city.data,
            country=book_form.book_publisher_country.data,
            day=book_form.book_publication_day.data,
            month=book_form.book_publication_month.data,
            year=book_form.book_publication_year.data,
            description=book_form.book_description.data,
            link=book_form.book_link.data,
            document_status="draft" if not submit else "published")

        db.session.add(book)
        db.session.commit()
        flash(
            'Book \"{}\" successfully saved'.format(
                book_form.book_title.data), 'form-success')
    elif doc_type == 'journal article':
        journal_form = form
        article = Document(
            doc_type="journal article",
            title=journal_form.article_title.data,
            author_first_name=journal_form.article_author_first_name.data,
            author_last_name=journal_form.article_author_last_name.data,
            posted_by=current_user.id,
            last_edited_by=current_user.id,
            name=journal_form.publisher_name.data,
            volume=journal_form.volume.data,
            page_start=journal_form.start_page.data,
            page_end=journal_form.end_page.data,
            day=journal_form.article_publication_day.data,
            month=journal_form.article_publication_month.data,
            year=journal_form.article_publication_year.data,
            description=journal_form.article_description.data,
            link=journal_form.article_link.data,
            document_status="draft" if not submit else "published")

        db.session.add(article)
        db.session.commit()
        flash(
            'Article \"{}\" successfully saved'.format(
                journal_form.article_title.data), 'form-success')
    elif doc_type == 'law':
        law_form = form
        law = Document(
            doc_type="law",
            day=law_form.law_enactment_day.data,
            month=law_form.law_enactment_month.data,
            year=law_form.law_enactment_year.data,
            citation=law_form.law_citation.data,
            region=law_form.law_region.data,
            posted_by=current_user.id,
            last_edited_by=current_user.id,
            title=law_form.law_title.data,
            description=law_form.law_description.data,
            city=law_form.law_city.data,
            state=law_form.law_state.data,
            country=law_form.law_country.data,
            link=law_form.law_link.data,
            govt_body=law_form.law_government_body.data,
            section=law_form.law_section.data,
            document_status="draft" if not submit else "published"
        )

        db.session.add(law)
        db.session.commit()
        flash(
            'Law \"{}\" successfully saved'.format(
                law_form.law_title.data), 'form-success')
    elif doc_type == 'video':
        video_form = form
        video = Document(
            doc_type="video",
            title=video_form.video_title.data,
            author_first_name=video_form.director_first_name.data,
            author_last_name=video_form.director_last_name.data,
            post_source=video_form.video_post_source.data,
            posted_by=current_user.id,
            last_edited_by=current_user.id,
            city=video_form.video_city.data,
            country=video_form.video_country.data,
            name=video_form.video_publisher.data,
            year=video_form.video_publication_year.data,
            description=video_form.video_description.data,
            link=video_form.video_link.data,
            document_status="draft" if not submit else "published")

        db.session.add(video)
        db.session.commit()
        flash(
            'Video \"{}\" successfully saved'.format(
                video_form.video_title.data), 'form-success')
    elif doc_type == 'other':
        other_form = form
        other = Document(
            doc_type="other",
            title=other_form.other_title.data,
            author_first_name=other_form.other_author_first_name.data,
            author_last_name=other_form.other_author_last_name.data,
            posted_by=current_user.id,
            last_edited_by=current_user.id,
            day=other_form.other_publication_day.data,
            month=other_form.other_publication_month.data,
            year=other_form.other_publication_year.data,
            description=other_form.other_description.data,
            link=other_form.other_link.data,
            other_type=other_form.other_document_type.data,
            document_status="draft" if not submit else "published")

        db.session.add(other)
        db.session.commit()
        flash(
            'Other \"{}\" successfully saved'.format(
                other_form.other_title.data), 'form-success')


@admin.route('/contribution/from_suggestion/article/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def view_article_draft(id):
    article_entry = Suggestion.query.get(id)
    article_form = ArticleForm(
        doc_type="news article",
        article_title=article_entry.title,
        article_description=article_entry.description,
        article_link=article_entry.link,
        document_status="draft")

    if request.method == 'POST':
        if article_form.validate_on_submit():
            if "Save Article" in request.form.values():
                save_or_submit_doc(article_form, doc_type='news article', submit=False)

            if "Submit Article" in request.form.values():
                save_or_submit_doc(article_form, doc_type='news article', submit=True)

            return review_suggestions()

    return render_template('contributor/edit_article_draft.html', article_form=article_form, c=article_entry)

@admin.route('/contribution/from_suggestion/journal/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def view_journal_draft(id):
    journal_entry = Suggestion.query.get(id)
    journal_form = JournalArticleForm(
        doc_type="journal article",
        article_title=journal_entry.title,
        article_description=journal_entry.description,
        article_link=journal_entry.link,
        document_status="draft")

    if request.method == 'POST':
        if journal_form.validate_on_submit():
            if "Save Article" in request.form.values():
                save_or_submit_doc(journal_form, doc_type='journal article', submit=False)

            if "Submit Article" in request.form.values():
                save_or_submit_doc(journal_form, doc_type='journal article', submit=True)

            return review_suggestions()

    return render_template('contributor/edit_journal_draft.html', journal_form=journal_form, c=journal_entry)


@admin.route('/contribution/from_suggestion/law/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def view_law_draft(id):
    """Contribution Review page."""
    law_entry = Suggestion.query.get(id)

    law_form = LawForm(
        doc_type="law",
        law_title=law_entry.title,
        law_description=law_entry.description,
        law_link=law_entry.link,
        document_status="draft")

    if request.method == 'POST':
        if law_form.validate_on_submit():
            if "Save Article" in request.form.values():
                save_or_submit_doc(law_form, doc_type='law', submit=False)

            if "Submit Article" in request.form.values():
                save_or_submit_doc(law_form, doc_type='law', submit=True)

            return review_suggestions()

    return render_template('contributor/edit_law_draft.html', law_form=law_form, c=law_entry)


@admin.route('/contribution/from_suggestion/video/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def view_video_draft(id):
    video_entry = Document.query.get(id)
    video_form = VideoForm(
        doc_type="video",
        video_title=video_entry.title,
        video_description=video_entry.description,
        video_link=video_entry.link,
        document_status="draft")

    if request.method == 'POST':
        if video_form.validate_on_submit():
            if "Save Article" in request.form.values():
                save_or_submit_doc(video_form, doc_type='video', submit=False)

            if "Submit Article" in request.form.values():
                save_or_submit_doc(video_form, doc_type='video', submit=True)

            return review_suggestions()

    return render_template('contributor/edit_video_draft.html', video_form=video_form, c=video_entry)


@admin.route('/contribution/from_suggestion/other/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def view_other_draft(id):
    other_entry = Suggestion.query.get(id)
    other_form = OtherForm(
        doc_type="other",
        other_document_type=other_entry.other_type,
        other_title=other_entry.title,
        other_description=other_entry.description,
        other_link=other_entry.link,
        document_status="draft")

    if request.method == 'POST':
        if other_form.validate_on_submit():
            if "Save Article" in request.form.values():
                save_or_submit_doc(other_form, doc_type='other', submit=False)

            if "Submit Article" in request.form.values():
                save_or_submit_doc(other_form, doc_type='other', submit=True)

            return review_suggestions()

    return render_template('contributor/edit_other_draft.html', other_form=other_form, c=other_entry)