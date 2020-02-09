from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    jsonify,
    url_for
)

from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem.snowball import SnowballStemmer
from flask_login import login_required, current_user
from flask_rq import get_queue

from sqlalchemy.exc import IntegrityError
from sqlalchemy import func

from app import db, csrf
from app.adtributor.forms import (
    ChangeAccountTypeForm,
    ChangeUserEmailForm,
    InviteUserForm,
    NewUserForm,
    TagForm,
    BookForm,
    ArticleForm,
    OtherForm,
    LawForm,
    ReportForm,
    JournalArticleForm,
    VideoForm,
    DownloadForm,
    UpdateLinkForm,
)
from app.decorators import contributor_required, admin_required
from app.models import (
    EditableHTML,
    Role,
    User,
    Tag,
    Suggestion,
    Document,
    Tagged,
    Idf,
    Saved
)

from collections import Counter
from app.email import send_email
import csv
import io
import datetime

import os
import nltk
import threading
import logging

logger = logging.getLogger('werkzeug')

nltk.data.path.append(os.environ.get('NLTK_DATA'))

admin = Blueprint('admin', __name__)
contributor = Blueprint('contributor', __name__)

BROKEN = 0
NOT_BROKEN = 1
IGNORE = 2


def role():
    if current_user.role_id == 2:
        return 'contributor'
    else:
        return 'admin'


def dest_from_role():
    if role() == 'contributor':
        return 'needs review'
    else:
        return 'published'


@admin.route('/index', methods=['GET', 'POST'])
@admin_required
@contributor.route('/index', methods=['GET', 'POST'])
@contributor_required
@login_required
def index():
    return render_template(role() + '/index.html')


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
    '/user/<int:user_id>/change-account-type',
    methods=['GET', 'POST']
)
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
    """Manage tags available for documents."""
    form = TagForm()
    tags = Tag.query.all()

    if form.validate_on_submit():
        tag = Tag.query.filter(
            func.lower(Tag.tag) == func.lower(form.tag.data)
        ).first()
        if tag:
            flash(
                'Tag \"{}\" already exists'.format(
                    form.tag.data), 'form-error'
            )
        else:
            tag = Tag(tag=form.tag.data)
            db.session.add(tag)
            db.session.commit()
            flash(
                'Tag \"{}\" successfully created'.format(
                    form.tag.data), 'form-success'
            )
        tags = Tag.query.all()
        return render_template(
            'admin/manage_tags.html', form=form, tags=tags)

    return render_template('admin/manage_tags.html', form=form, tags=tags)


@admin.route('/tag/delete/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def delete_tag(id):
    """Endpoint for deleting document tags."""
    tag = Tag.query.get(id)
    if tag is None:
        abort(404)
    Tagged.query.filter_by(tag_id=tag.id).delete()
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
    """Review suggestions for ."""
    suggestions = Suggestion.query.order_by(Suggestion.id.desc()).all()
    return render_template(
        'admin/review_suggestions.html',
        suggestions=suggestions
    )


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


@admin.route('/view_all_drafts', methods=['GET', 'POST'])
@admin_required
@contributor.route('/view_all_drafts', methods=['GET', 'POST'])
@contributor_required
@login_required
def view_all_drafts():
    contributions = Document.query.filter(
        Document.posted_by == str(current_user.id)
    ).order_by(Document.last_edited_date.desc()).all()
    return render_template(
        'adtributor/draft_contributions.html',
        contributions=contributions,
        user_type=role()
    )


@admin.route('/publish_contribution/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def publish_contribution(id):
    """Contribution Review page."""
    contribution = Document.query.filter_by(id=id).first()
    if contribution.document_status == "published":
        contribution.document_status = "draft"
    else:
        contribution.document_status = "published"
    db.session.commit()
    return redirect(url_for('admin.review_contributions'))


@contributor.route('/publish_draft/<int:id>', methods=['GET', 'POST'])
@contributor_required
@admin.route('/publish_draft/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def publish_draft(id):
    """Contribution Review page."""
    contribution = Document.query.filter_by(id=id).first()
    if contribution.document_status == "published":
        contribution.document_status = "draft"
    else:
        contribution.document_status = "published"
    db.session.commit()
    return redirect(url_for('admin.view_all_drafts'))


@admin.route('/toggle_publish', methods=['GET', 'POST'])
@login_required
@admin_required
def toggle_publish():
    id = request.form['id']
    contribution = Document.query.filter_by(id=id).first()
    contribution.last_edited_by = \
        current_user.first_name + ' ' + current_user.last_name
    contribution.last_edited_date = datetime.datetime.utcnow()
    if contribution.document_status == "published":
        contribution.document_status = "under review"
        db.session.commit()
        return jsonify(status='Publish')
    else:
        contribution.document_status = "published"
        db.session.commit()
        return jsonify(status='Unpublish')


@admin.route('/review_contributions', methods=['GET', 'POST'])
@login_required
@admin_required
def review_contributions():
    contributions = Document.query.filter(
        Document.document_status != 'draft',
        Document.document_status != 'published'
    ).order_by(Document.id.desc()).all()
    return render_template(
        'admin/review_contributions.html',
        contributions=contributions
    )


@admin.route('/contribution/<int:id>', methods=['GET'])
@login_required
@admin_required
def other_contribution(id):
    """Contribution Review page."""
    contribution = Document.query.get(id)
    user_id = getattr(current_user, 'id', None)
    saved_objs = Saved.query.filter_by(user_id=user_id, doc_id=id)
    saved = bool(user_id) and bool(saved_objs.all())
    return render_template(
        'main/resource.html',
        resource=contribution,
        user_id=user_id,
        saved=saved,
        loc="contribution",
        user_type=role()
    )


@admin.route('/draft/<int:id>', methods=['GET'])
@admin_required
@contributor.route('/draft/<int:id>', methods=['GET'])
@contributor_required
@login_required
def contribution(id):
    contribution = Document.query.get(id)
    return render_template(
        'main/resource.html',
        resource=contribution,
        loc="draft",
        user_type=role()
    )


@admin.route('/draft/book/<int:id>', methods=['GET', 'POST'])
@admin_required
@contributor.route('/draft/book/<int:id>', methods=['GET', 'POST'])
@contributor_required
@login_required
def view_book_draft(id):
    contribution = Document.query.get(id)
    book_entry = Document.query.filter_by(id=id).first()
    book_form = BookForm(
        book_title=book_entry.title,
        book_volume=book_entry.volume,
        book_edition=book_entry.edition,
        book_editor_first_name=book_entry.editor_first_name.split(','),
        book_editor_last_name=book_entry.editor_last_name.split(','),
        book_series=book_entry.series,
        book_author_first_name=book_entry.author_first_name.split(','),
        book_author_last_name=book_entry.author_last_name.split(','),
        book_publisher=book_entry.publisher,
        book_publication_month=book_entry.month,
        book_publication_year=book_entry.year,
        book_description=book_entry.description,
        book_tags=[str(t.tag_id) for t in book_entry.tags],
        book_link=book_entry.link,
        book_file_urls=book_entry.file,
    )

    if request.method == 'POST':
        if book_form.validate_on_submit():
            if "Save Book" in request.form.values():
                save_or_submit_doc(
                    book_form, doc_type='book',
                    submit='draft',
                    entry=book_entry
                )

            if "Submit Book" in request.form.values():
                save_or_submit_doc(
                    book_form,
                    doc_type='book',
                    submit=dest_from_role(),
                    entry=book_entry
                )

            return redirect(url_for(role() + '.view_all_drafts'))

    return render_template(
        'adtributor/edit_book_draft.html',
        book_form=book_form,
        c=contribution
    )


@admin.route('/draft/news_article/<int:id>', methods=['GET', 'POST'])
@admin_required
@contributor.route('/draft/news_article/<int:id>', methods=['GET', 'POST'])
@contributor_required
@login_required
def view_news_article_draft(id):
    article_entry = Document.query.filter_by(id=id).first()
    article_form = ArticleForm(
        article_title=article_entry.title,
        article_author_first_name=article_entry.author_first_name.split(','),
        article_author_last_name=article_entry.author_last_name.split(','),
        article_publication=article_entry.publisher,
        article_publication_day=article_entry.day,
        article_publication_month=article_entry.month,
        article_publication_year=article_entry.year,
        article_description=article_entry.description,
        article_tags=[str(t.tag_id) for t in article_entry.tags],
        article_link=article_entry.link,
        article_file_urls=article_entry.file,
    )

    if request.method == 'POST':
        if article_form.validate_on_submit():
            if "Save Article" in request.form.values():
                save_or_submit_doc(
                    article_form,
                    doc_type='news_article',
                    submit='draft',
                    entry=article_entry
                )

            if "Submit Article" in request.form.values():
                save_or_submit_doc(
                    article_form,
                    doc_type='news_article',
                    submit=dest_from_role(),
                    entry=article_entry
                )

            return redirect(url_for(role() + '.view_all_drafts'))

    return render_template(
        'adtributor/edit_news_article_draft.html',
        article_form=article_form,
        c=contribution
    )


@admin.route('/draft/journal_article/<int:id>', methods=['GET', 'POST'])
@admin_required
@contributor.route('/draft/journal_article/<int:id>', methods=['GET', 'POST'])
@contributor_required
@login_required
def view_journal_article_draft(id):
    journal_entry = Document.query.filter_by(id=id).first()
    journal_form = JournalArticleForm(
        doc_type="journal_article",
        journal_title=journal_entry.title,
        journal_author_first_name=journal_entry.author_first_name.split(','),
        journal_author_last_name=journal_entry.author_last_name.split(','),
        journal_publication=journal_entry.publisher,
        journal_volume=journal_entry.volume,
        journal_issue=journal_entry.issue,
        journal_start_page=journal_entry.page_start,
        journal_end_page=journal_entry.page_end,
        journal_publication_day=journal_entry.day,
        journal_publication_month=journal_entry.month,
        journal_publication_year=journal_entry.year,
        journal_description=journal_entry.description,
        journal_tags=[str(t.tag_id) for t in journal_entry.tags],
        journal_link=journal_entry.link,
        journal_file_urls=journal_entry.file,
        document_status="draft"
    )

    if request.method == 'POST':
        if journal_form.validate_on_submit():

            if "Save Journal" in request.form.values():
                save_or_submit_doc(
                    journal_form,
                    doc_type='journal_article',
                    submit='draft',
                    entry=journal_entry
                )

            if "Submit Journal" in request.form.values():
                save_or_submit_doc(
                    journal_form,
                    doc_type='journal_article',
                    submit=dest_from_role(),
                    entry=journal_entry
                )

            return redirect(url_for(role() + '.view_all_drafts'))

    return render_template(
        'adtributor/edit_journal_article_draft.html',
        journal_form=journal_form,
        c=contribution
    )


@admin.route('/draft/law/<int:id>', methods=['GET', 'POST'])
@admin_required
@contributor.route('/draft/law/<int:id>', methods=['GET', 'POST'])
@contributor_required
@login_required
def view_law_draft(id):
    law_entry = Document.query.filter_by(id=id).first()
    law_form = LawForm(
        law_title=law_entry.title,
        law_government_body=law_entry.govt_body,
        law_section=law_entry.section,
        law_citation=law_entry.citation,
        law_region=law_entry.region,
        law_enactment_day=law_entry.day,
        law_enactment_month=law_entry.month,
        law_enactment_year=law_entry.year,
        law_country=law_entry.country,
        law_description=law_entry.description,
        law_tags=[str(t.tag_id) for t in law_entry.tags],
        law_link=law_entry.link,
        law_file_urls=law_entry.file,
    )

    if request.method == 'POST':
        if law_form.validate_on_submit():
            if "Save Law" in request.form.values():
                save_or_submit_doc(
                    law_form,
                    doc_type='law',
                    submit='draft',
                    entry=law_entry
                )

            if "Submit Law" in request.form.values():
                save_or_submit_doc(
                    law_form,
                    doc_type='law',
                    submit=dest_from_role(),
                    entry=law_entry
                )

            return redirect(url_for(role() + '.view_all_drafts'))

    return render_template(
        'adtributor/edit_law_draft.html',
        law_form=law_form,
        c=contribution
    )


@admin.route('/draft/video/<int:id>', methods=['GET', 'POST'])
@admin_required
@contributor.route('draft/video/<int:id>', methods=['GET', 'POST'])
@contributor_required
@login_required
def view_video_draft(id):
    video_entry = Document.query.filter_by(id=id).first()
    video_form = VideoForm(
        video_title=video_entry.title,
        video_series=video_entry.series,
        director_first_name=video_entry.author_first_name.split(','),
        director_last_name=video_entry.author_last_name.split(','),
        video_source=video_entry.source,
        video_publisher=video_entry.publisher,
        video_country=video_entry.country,
        video_studio=video_entry.studio,
        video_publication_day=video_entry.day,
        video_publication_month=video_entry.month,
        video_publication_year=video_entry.year,
        video_description=video_entry.description,
        video_tags=[str(t.tag_id) for t in video_entry.tags],
        video_link=video_entry.link,
        video_file_urls=video_entry.file,
    )

    if request.method == 'POST':
        if video_form.validate_on_submit():
            if "Save Video" in request.form.values():
                save_or_submit_doc(
                    video_form,
                    doc_type='video',
                    submit='draft',
                    entry=video_entry
                )

            if "Submit Video" in request.form.values():
                save_or_submit_doc(
                    video_form,
                    doc_type='video',
                    submit=dest_from_role(),
                    entry=video_entry
                )

            return redirect(url_for(role() + '.view_all_drafts'))

    return render_template(
        'adtributor/edit_video_draft.html',
        video_form=video_form,
        c=contribution
    )


@admin.route('/draft/report/<int:id>', methods=['GET', 'POST'])
@admin_required
@contributor.route('/draft/report/<int:id>', methods=['GET', 'POST'])
@contributor_required
@login_required
def view_report_draft(id):
    report_entry = Document.query.filter_by(id=id).first()
    report_form = ReportForm(
        doc_type="report",
        report_title=report_entry.title,
        report_author_first_name=report_entry.author_first_name.split(','),
        report_author_last_name=report_entry.author_last_name.split(','),
        report_publisher=report_entry.publisher,
        report_publication_day=report_entry.day,
        report_publication_month=report_entry.month,
        report_publication_year=report_entry.year,
        report_description=report_entry.description,
        report_tags=[str(t.tag_id) for t in report_entry.tags],
        report_link=report_entry.link,
        report_file_urls=report_entry.file,
    )

    if request.method == 'POST':
        if report_form.validate_on_submit():
            if "Save Book" in request.form.values():
                save_or_submit_doc(
                    report_form,
                    doc_type='report',
                    submit='draft',
                    entry=report_entry
                )

            if "Submit Book" in request.form.values():
                save_or_submit_doc(
                    report_form,
                    doc_type='report',
                    submit=dest_from_role(),
                    entry=report_entry
                )

            return redirect(url_for(role() + '.view_all_drafts'))

    return render_template(
        'adtributor/edit_report_draft.html',
        report_form=report_form,
        c=contribution
    )


@admin.route('/draft/other/<int:id>', methods=['GET', 'POST'])
@admin_required
@contributor.route('/draft/other/<int:id>', methods=['GET', 'POST'])
@contributor_required
@login_required
def view_other_draft(id):
    other_entry = Document.query.filter_by(id=id).first()
    other_form = OtherForm(
        doc_type="other",
        other_document_type=other_entry.other_type,
        other_title=other_entry.title,
        other_author_first_name=other_entry.author_first_name.split(','),
        other_author_last_name=other_entry.author_last_name.split(','),
        other_publication_day=other_entry.day,
        other_publication_month=other_entry.month,
        other_publication_year=other_entry.year,
        other_source=other_entry.source,
        other_description=other_entry.description,
        other_tags=[str(t.tag_id) for t in other_entry.tags],
        other_link=other_entry.link,
        other_file_urls=other_entry.file,
        document_status="draft"
    )

    if request.method == 'POST':
        if other_form.validate_on_submit():
            if "Save Other" in request.form.values():
                save_or_submit_doc(
                    other_form,
                    doc_type='other',
                    submit='draft',
                    entry=other_entry
                )

            if "Submit Law" in request.form.values():
                save_or_submit_doc(
                    other_form,
                    doc_type='other',
                    submit=dest_from_role(),
                    entry=other_entry
                )

            return redirect(url_for(role() + '.view_all_drafts'))

    return render_template(
        'adtributor/edit_other_draft.html',
        other_form=other_form,
        c=contribution
    )


@admin.route('/submit', methods=['GET', 'POST'])
@admin_required
@contributor.route('/submit', methods=['GET', 'POST'])
@contributor_required
@login_required
def submit():
    book_form = BookForm()
    article_form = ArticleForm()
    law_form = LawForm()
    other_form = OtherForm()
    journal_form = JournalArticleForm()
    video_form = VideoForm()
    report_form = ReportForm()

    if request.method == 'POST':

        form_name = request.form['form-name']

        if form_name == 'book_form':

            if book_form.validate_on_submit():

                if "Save Book" in request.form.values():
                    save_or_submit_doc(
                        book_form, doc_type='book', submit='draft'
                    )

                if "Submit Book" in request.form.values():
                    save_or_submit_doc(
                        book_form, doc_type='book', submit=dest_from_role()
                    )

                return redirect(url_for(role() + '.view_all_drafts'))

            return render_template(
                'adtributor/submit.html',
                book_form=book_form, report_form=report_form,
                article_form=article_form, law_form=law_form,
                other_form=other_form, journal_form=journal_form,
                video_form=video_form, active="book", user_type=role()
            )

        if form_name == 'article_form':

            if article_form.validate_on_submit():

                if "Save Article" in request.form.values():
                    save_or_submit_doc(
                        article_form, doc_type='news_article',
                        submit='draft'
                    )

                if "Submit Article" in request.form.values():
                    save_or_submit_doc(
                        article_form, doc_type='news_article',
                        submit=dest_from_role()
                    )

                return redirect(url_for(role() + '.view_all_drafts'))

            return render_template(
                'adtributor/submit.html', book_form=book_form,
                report_form=report_form, article_form=article_form,
                law_form=law_form, other_form=other_form,
                journal_form=journal_form, video_form=video_form,
                active="article", user_type=role()
            )

        if form_name == 'journal_form':

            if journal_form.validate_on_submit():

                if "Save Journal" in request.form.values():
                    save_or_submit_doc(
                        journal_form, doc_type='journal_article',
                        submit='draft'
                    )

                if "Submit Journal" in request.form.values():
                    save_or_submit_doc(
                        journal_form, doc_type='journal_article',
                        submit=dest_from_role()
                    )

                return redirect(url_for(role() + '.view_all_drafts'))

            return render_template(
                'adtributor/submit.html', book_form=book_form,
                report_form=report_form, article_form=article_form,
                law_form=law_form, other_form=other_form,
                journal_form=journal_form, video_form=video_form,
                active="journal", user_type=role()
            )

        if form_name == 'law_form':

            if law_form.validate_on_submit():

                if "Save Law" in request.form.values():
                    save_or_submit_doc(
                        law_form,
                        doc_type='law',
                        submit='draft'
                    )

                if "Submit Law" in request.form.values():
                    save_or_submit_doc(
                        law_form, doc_type='law', submit=dest_from_role()
                    )

                return redirect(url_for(role() + '.view_all_drafts'))

            return render_template(
                'adtributor/submit.html', book_form=book_form,
                report_form=report_form, article_form=article_form,
                law_form=law_form, other_form=other_form,
                journal_form=journal_form, video_form=video_form,
                active="law", user_type=role()
            )

        if form_name == 'video_form':

            if video_form.validate_on_submit():

                if "Save Video" in request.form.values():
                    save_or_submit_doc(
                        video_form, doc_type='video', submit='draft'
                    )

                if "Submit Video" in request.form.values():
                    save_or_submit_doc(
                        video_form, doc_type='video', submit=dest_from_role()
                    )

                return redirect(url_for(role() + '.view_all_drafts'))

            return render_template(
                'adtributor/submit.html', book_form=book_form,
                report_form=report_form, article_form=article_form,
                law_form=law_form, other_form=other_form,
                journal_form=journal_form, video_form=video_form,
                active="video", user_type=role()
            )

        if form_name == 'report_form':

            if report_form.validate_on_submit():

                if "Save Report" in request.form.values():
                    save_or_submit_doc(
                        report_form, doc_type='report', submit='draft'
                    )

                if "Submit Report" in request.form.values():
                    save_or_submit_doc(
                        report_form, doc_type='report', submit=dest_from_role()
                    )

                return redirect(url_for(role() + '.view_all_drafts'))

            return render_template(
                'adtributor/submit.html', book_form=book_form,
                report_form=report_form, article_form=article_form,
                law_form=law_form, other_form=other_form,
                journal_form=journal_form, video_form=video_form,
                active="report", user_type=role()
            )

        if form_name == 'other_form':

            if other_form.validate_on_submit():

                if "Save Other" in request.form.values():
                    save_or_submit_doc(
                        other_form, doc_type='other', submit='draft'
                    )

                if "Submit Other" in request.form.values():
                    save_or_submit_doc(
                        other_form, doc_type='other', submit=dest_from_role()
                    )

                return redirect(url_for(role() + '.view_all_drafts'))

            return render_template(
                'adtributor/submit.html', book_form=book_form,
                report_form=report_form, article_form=article_form,
                law_form=law_form, other_form=other_form,
                journal_form=journal_form, video_form=video_form,
                active="other", user_type=role()
            )

    return render_template(
        'adtributor/submit.html', book_form=book_form,
        report_form=report_form, article_form=article_form,
        law_form=law_form, other_form=other_form,
        journal_form=journal_form, video_form=video_form,
        active="book", user_type=role()
    )


@admin.route('/contribution/book/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def contribution_book(id):
    contribution = Document.query.get(id)
    book_entry = Document.query.filter_by(id=id).first()
    book_form = BookForm(
        doc_type="book",
        book_title=book_entry.title,
        book_volume=book_entry.volume,
        book_edition=book_entry.edition,
        book_editor_first_name=book_entry.editor_first_name.split(','),
        book_editor_last_name=book_entry.editor_last_name.split(','),
        book_series=book_entry.series,
        book_author_first_name=book_entry.author_first_name.split(','),
        book_author_last_name=book_entry.author_last_name.split(','),
        book_publisher=book_entry.publisher,
        book_publication_month=book_entry.month,
        book_publication_year=book_entry.year,
        book_description=book_entry.description,
        book_tags=[str(t.tag_id) for t in book_entry.tags],
        book_link=book_entry.link,
        book_file_urls=book_entry.file,
    )

    if request.method == 'POST':
        if book_form.validate_on_submit():
            if "Save Book" in request.form.values():
                save_or_submit_doc(
                    book_form, doc_type='book', submit='under review',
                    entry=book_entry
                )

            if "Submit Book" in request.form.values():
                save_or_submit_doc(
                    book_form, doc_type='book', submit='published',
                    entry=book_entry
                )

            return redirect(url_for('admin.review_contributions'))

    return render_template(
        'adtributor/edit_book_draft.html', book_form=book_form, c=contribution
    )


@admin.route('/contribution/news_article/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def contribution_news_article(id):
    article_entry = Document.query.filter_by(id=id).first()
    article_form = ArticleForm(
        doc_type="news_article",
        article_title=article_entry.title,
        article_author_first_name=article_entry.author_first_name.split(','),
        article_author_last_name=article_entry.author_last_name.split(','),
        article_publication=article_entry.publisher,
        article_publication_day=article_entry.day,
        article_publication_month=article_entry.month,
        article_publication_year=article_entry.year,
        article_description=article_entry.description,
        article_tags=[str(t.tag_id) for t in article_entry.tags],
        article_link=article_entry.link,
        article_file_urls=article_entry.file,
        document_status="draft"
    )

    if request.method == 'POST':
        if article_form.validate_on_submit():
            if "Save Article" in request.form.values():
                save_or_submit_doc(
                    article_form, doc_type='news_article',
                    submit='under review', entry=article_entry
                )

            if "Submit Article" in request.form.values():
                save_or_submit_doc(
                    article_form, doc_type='news_article', submit='published',
                    entry=article_entry
                )

            return redirect(url_for('admin.review_contributions'))

    return render_template(
        'adtributor/edit_news_article_draft.html', article_form=article_form,
        c=contribution
    )


@admin.route('/contribution/journal_article/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def contribution_journal_article(id):
    journal_entry = Document.query.filter_by(id=id).first()
    journal_form = JournalArticleForm(
        journal_title=journal_entry.title,
        journal_author_first_name=journal_entry.author_first_name.split(','),
        journal_author_last_name=journal_entry.author_last_name.split(','),
        journal_volume=journal_entry.volume,
        journal_start_page=journal_entry.page_start,
        journal_end_page=journal_entry.page_end,
        journal_publication=journal_entry.publisher,
        journal_publication_day=journal_entry.day,
        journal_publication_month=journal_entry.month,
        journal_publication_year=journal_entry.year,
        journal_description=journal_entry.description,
        journal_tags=[str(t.tag_id) for t in journal_entry.tags],
        journal_link=journal_entry.link,
        journal_file_urls=journal_entry.file,
    )

    if request.method == 'POST':
        if journal_form.validate_on_submit():
            if "Save Journal" in request.form.values():
                save_or_submit_doc(
                    journal_form, doc_type='journal_article',
                    submit="under review", entry=journal_entry
                )

            if "Submit Journal" in request.form.values():
                save_or_submit_doc(
                    journal_form, doc_type='journal_article',
                    submit="published", entry=journal_entry
                )

            return redirect(url_for('admin.review_contributions'))

    return render_template(
        'adtributor/edit_journal_article_draft.html',
        journal_form=journal_form, c=contribution
    )


@admin.route('/contribution/law/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def contribution_law(id):
    law_entry = Document.query.filter_by(id=id).first()
    law_form = LawForm(
        law_title=law_entry.title,
        law_government_body=law_entry.govt_body,
        law_section=law_entry.section,
        law_citation=law_entry.citation,
        law_region=law_entry.region,
        law_enactment_day=law_entry.day,
        law_enactment_month=law_entry.month,
        law_enactment_year=law_entry.year,
        law_country=law_entry.country,
        law_description=law_entry.description,
        law_tags=[str(t.tag_id) for t in law_entry.tags],
        law_link=law_entry.link,
        law_file_urls=law_entry.file,
    )

    if request.method == 'POST':
        if law_form.validate_on_submit():
            if "Save Law" in request.form.values():
                save_or_submit_doc(
                    law_form, doc_type='law', submit="under review",
                    entry=law_entry
                )

            if "Submit Law" in request.form.values():
                save_or_submit_doc(
                    law_form, doc_type='law', submit="published",
                    entry=law_entry
                )

            return redirect(url_for('admin.review_contributions'))

    return render_template(
        'adtributor/edit_law_draft.html', law_form=law_form, c=contribution
    )


@admin.route('/contribution/video/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def contribution_video(id):
    video_entry = Document.query.filter_by(id=id).first()
    video_form = VideoForm(
        video_title=video_entry.title,
        director_first_name=video_entry.author_first_name.split(','),
        director_last_name=video_entry.author_last_name.split(','),
        video_source=video_entry.source,
        video_publisher=video_entry.publisher,
        video_studio=video_entry.studio,
        video_country=video_entry.series,
        video_series=video_entry.series,
        video_publication_day=video_entry.day,
        video_publication_month=video_entry.month,
        video_publication_year=video_entry.year,
        video_description=video_entry.description,
        video_tags=[str(t.tag_id) for t in video_entry.tags],
        video_link=video_entry.link,
        video_file_urls=video_entry.file,
    )

    if request.method == 'POST':
        if video_form.validate_on_submit():
            if "Save Video" in request.form.values():
                save_or_submit_doc(
                    video_form, doc_type='video', submit="under review",
                    entry=video_entry
                )

            if "Submit Video" in request.form.values():
                save_or_submit_doc(
                    video_form, doc_type='video', submit="published",
                    entry=video_entry
                )

            return redirect(url_for('admin.review_contributions'))

    return render_template(
        'adtributor/edit_video_draft.html', video_form=video_form,
        c=contribution
    )


@admin.route('/contribution/report/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def contribution_report(id):
    report_entry = Document.query.filter_by(id=id).first()
    report_form = ReportForm(
        doc_type="report",
        report_title=report_entry.title,
        report_author_first_name=report_entry.author_first_name.split(','),
        report_author_last_name=report_entry.author_last_name.split(','),
        report_publisher=report_entry.publisher,
        report_publication_day=report_entry.day,
        report_publication_month=report_entry.month,
        report_publication_year=report_entry.year,
        report_description=report_entry.description,
        report_tags=[str(t.tag_id) for t in report_entry.tags],
        report_link=report_entry.link,
        report_file_urls=report_entry.file,
        document_status='draft'
    )

    if request.method == 'POST':
        if report_form.validate_on_submit():
            if "Save Report" in request.form.values():
                save_or_submit_doc(
                    report_form, doc_type='report', submit="under review",
                    entry=report_entry
                )

            if "Submit Report" in request.form.values():
                save_or_submit_doc(
                    report_form, doc_type='report', submit="published",
                    entry=report_entry
                )

            return redirect(url_for('admin.review_contributions'))

    return render_template(
        'adtributor/edit_report_draft.html', report_form=report_form,
        c=contribution
    )


@admin.route('/contribution/other/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def contribution_other(id):
    contribution = Document.query.get(id)
    other_entry = Document.query.filter_by(id=id).first()
    other_form = OtherForm(
        doc_type="other",
        other_document_type=other_entry.other_type,
        other_title=other_entry.title,
        other_author_first_name=other_entry.author_first_name.split(','),
        other_author_last_name=other_entry.author_last_name.split(','),
        other_publication_day=other_entry.day,
        other_publication_month=other_entry.month,
        other_publication_year=other_entry.year,
        other_source=other_entry.source,
        other_description=other_entry.description,
        other_tags=[str(t.tag_id) for t in other_entry.tags],
        other_link=other_entry.link,
        other_file_urls=other_entry.file,
        document_status="draft"
    )

    if request.method == 'POST':
        if other_form.validate_on_submit():
            if "Save Other" in request.form.values():
                save_or_submit_doc(
                    other_form, doc_type='other', submit="under review",
                    entry=other_entry
                )

            if "Submit Other" in request.form.values():
                save_or_submit_doc(
                    other_form, doc_type='other', submit="published",
                    entry=other_entry
                )

            return redirect(url_for('admin.review_contributions'))

    return render_template(
        'adtributor/edit_other_draft.html', other_form=other_form,
        c=contribution
    )


@admin.route('/from_suggestion/book/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def suggestion_book_draft(id):
    book_entry = Suggestion.query.get(id)
    book_form = BookForm(
        doc_type="book",
        book_title=book_entry.title,
        book_description=book_entry.description,
        book_link=book_entry.link,
        document_status="draft")

    if request.method == 'POST':
        if book_form.validate_on_submit():
            if "Save Book" in request.form.values():
                save_or_submit_doc(book_form, doc_type='book', submit='draft')

            if "Submit Book" in request.form.values():
                save_or_submit_doc(
                    book_form, doc_type='book', submit='published'
                )

            return redirect(url_for('admin.review_suggestions'))

    return render_template(
        'adtributor/edit_book_draft.html', book_form=book_form
    )


@admin.route('/from_suggestion/article/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def suggestion_news_article_draft(id):
    article_entry = Suggestion.query.get(id)
    article_form = ArticleForm(
        doc_type="news_article",
        article_title=article_entry.title,
        article_description=article_entry.description,
        article_link=article_entry.link,
        document_status="draft")

    if request.method == 'POST':
        if article_form.validate_on_submit():
            if "Save Article" in request.form.values():
                save_or_submit_doc(
                    article_form, doc_type='news_article', submit='draft'
                )

            if "Submit Article" in request.form.values():
                save_or_submit_doc(
                    article_form, doc_type='news_article', submit='published'
                )

            return redirect(url_for('admin.review_suggestions'))

    return render_template(
        'adtributor/edit_news_article_draft.html', article_form=article_form
    )


@admin.route('/from_suggestion/journal/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def suggestion_journal_article_draft(id):
    journal_entry = Suggestion.query.get(id)
    journal_form = JournalArticleForm(
        journal_title=journal_entry.title,
        journal_description=journal_entry.description,
        journal_link=journal_entry.link
    )

    if request.method == 'POST':
        if journal_form.validate_on_submit():
            if "Save Journal" in request.form.values():
                save_or_submit_doc(
                    journal_form, doc_type='journal', submit='draft'
                )

            if "Submit Journal" in request.form.values():
                save_or_submit_doc(
                    journal_form, doc_type='journal', submit='published'
                )

            return redirect(url_for('admin.review_suggestions'))

    return render_template(
        'adtributor/edit_journal_article_draft.html', journal_form=journal_form
    )


@admin.route('/from_suggestion/law/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def suggestion_law_draft(id):
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
            if "Save Law" in request.form.values():
                save_or_submit_doc(law_form, doc_type='law', submit='draft')

            if "Submit Law" in request.form.values():
                save_or_submit_doc(
                    law_form, doc_type='law', submit='published'
                )

            return redirect(url_for('admin.review_suggestions'))

    return render_template('adtributor/edit_law_draft.html', law_form=law_form)


@admin.route('/from_suggestion/video/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def suggestion_video_draft(id):
    video_entry = Suggestion.query.get(id)
    video_form = VideoForm(
        doc_type="video",
        video_title=video_entry.title,
        video_description=video_entry.description,
        video_link=video_entry.link,
        document_status="draft")

    if request.method == 'POST':
        if video_form.validate_on_submit():
            if "Save Video" in request.form.values():
                save_or_submit_doc(
                    video_form, doc_type='video', submit='draft'
                )

            if "Submit Video" in request.form.values():
                save_or_submit_doc(
                    video_form, doc_type='video', submit='published'
                )

            return redirect(url_for('admin.review_suggestions'))

    return render_template(
        'adtributor/edit_video_draft.html', video_form=video_form
    )


@admin.route('/from_suggestion/report/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def suggestion_report_draft(id):
    report_entry = Suggestion.query.get(id)
    report_form = ReportForm(
        doc_type="report",
        report_title=report_entry.title,
        report_description=report_entry.description,
        report_link=report_entry.link,
        document_status="draft")

    if request.method == 'POST':
        if report_form.validate_on_submit():
            if "Save Report" in request.form.values():
                save_or_submit_doc(
                    report_form, doc_type='report', submit='draft'
                )

            if "Submit Report" in request.form.values():
                save_or_submit_doc(
                    report_form, doc_type='report', submit='published'
                )

            return redirect(url_for('admin.review_suggestions'))

    return render_template(
        'adtributor/edit_report_draft.html', report_form=report_form
    )


@admin.route('/from_suggestion/other/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def suggestion_other_draft(id):
    other_entry = Suggestion.query.get(id)
    other_form = OtherForm(
        doc_type="other",
        other_title=other_entry.title,
        other_description=other_entry.description,
        other_link=other_entry.link,
        document_status="draft"
    )

    if request.method == 'POST':
        if other_form.validate_on_submit():
            if "Save Other" in request.form.values():
                save_or_submit_doc(
                    other_form, doc_type='other', submit='draft'
                )

            if "Submit Other" in request.form.values():
                save_or_submit_doc(
                    other_form, doc_type='other', submit='published'
                )

            return redirect(url_for('admin.review_suggestions'))

    return render_template(
        'adtributor/edit_other_draft.html', other_form=other_form
    )


@admin.route('/view_all_drafts/delete/<int:id>', methods=['GET', 'POST'])
@admin_required
@contributor.route('/view_all_drafts/delete/<int:id>', methods=['GET', 'POST'])
@contributor_required
@login_required
def delete_draft(id):
    """Draft deletion endpoint."""
    draft = Document.query.get(id)
    if draft is None:
        abort(404)
    Tagged.query.filter_by(document_id=id).delete()
    update_idf(pre_tf=draft.tf, post_tf={}, doc_id=id)
    db.session.delete(draft)
    try:
        db.session.commit()
        flash(
            'Draft {} successfully deleted'.format(
                draft.title), 'form-success')
    except IntegrityError:
        db.session.rollback()
        flash('Error occurred. Please try again.', 'form-error')
        return redirect(url_for('contributor.view_all_drafts'))
    return redirect(url_for('contributor.view_all_drafts'))


@admin.route('/entry/delete/<int:id>', methods=['GET', 'POST'])
@admin_required
@login_required
def delete_entry(id):
    """Entry deletion endpoint."""
    entry = Document.query.get(id)
    if entry is None:
        abort(404)
    Tagged.query.filter_by(document_id=id).delete()
    update_idf(pre_tf=entry.tf, post_tf={}, doc_id=id)
    db.session.delete(entry)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash('Error occurred. Please try again.', 'form-error')
        return redirect(url_for('main.index'))
    return redirect(url_for('main.index'))


@admin.route('/broken_link', methods=['GET', 'POST'])
@login_required
@admin_required
def view_broken_links():
    form = UpdateLinkForm()
    if form.validate_on_submit():
        resource = Document.query.get(form.id.data)
        if resource:
            resource.link = form.link.data
            resource.broken_link = NOT_BROKEN
            db.session.commit()
    broken = Document.query.filter_by(broken_link=BROKEN).all()
    return render_template('admin/review_broken.html', broken=broken, form=form)


def save_or_submit_doc(form, doc_type, submit, entry=None):
    stemmer = SnowballStemmer("english", ignore_stopwords=True)
    stop_words = set(stopwords.words('english'))

    def update_sql_object(object, kwargs):
        for k, v in kwargs.items():
            setattr(object, k, v)
        db.session.commit()

    if doc_type == 'news_article':
        article_form = form
        new = False
        kwargs = {
            'doc_type': "news_article",
            'title': article_form.article_title.data,
            'author_first_name':
                ','.join(article_form.article_author_first_name.data),
            'author_last_name':
                ','.join(article_form.article_author_last_name.data),
            'last_edited_by': current_user.id,
            'publisher': article_form.article_publication.data,
            'day': article_form.article_publication_day.data,
            'month': article_form.article_publication_month.data,
            'year': article_form.article_publication_year.data,
            'description': article_form.article_description.data,
            'link': article_form.article_link.data,
            'file': article_form.article_file_urls.data,
            'document_status': submit,
            'broken_link': NOT_BROKEN,
        }
        if entry is not None:
            corpus = entry.corpus
            if entry.link == article_form.article_link.data:
                kwargs['broken_link'] = entry.broken_link
            update_sql_object(entry, kwargs)
        else:
            new = True
            kwargs['posted_by'] = current_user.id
            article = Document(**kwargs)
            db.session.add(article)
            corpus = article.corpus
            db.session.commit()
            entry = article

        word_tokens = word_tokenize(corpus)
        filtered_corpus = [
            stemmer.stem(w) for w in word_tokens if w not in stop_words
        ]
        new_tf = Counter(filtered_corpus)

        if new:
            update_idf(pre_tf={}, post_tf=new_tf, doc_id=article.id)

        else:
            update_idf(pre_tf=entry.tf, post_tf=new_tf, doc_id=entry.id)

        entry.tf = Counter(filtered_corpus)

        Tagged.query.filter_by(document_id=entry.id).delete()
        tag_ids = [int(x) for x in article_form.article_tags.data]
        for tag_id in tag_ids:
            tagged = Tagged(
                tag_id=tag_id,
                document_id=entry.id,
                tag_name=Tag.query.get(tag_id).tag
            )
            db.session.add(tagged)

        db.session.commit()
        flash(
            'Article \"{}\" successfully submitted'.format(
                article_form.article_title.data), 'form-success')
    elif doc_type == 'book':
        book_form = form
        new = False
        kwargs = {
            'doc_type': "book",
            'title': book_form.book_title.data,
            'volume': book_form.book_volume.data,
            'edition': book_form.book_edition.data,
            'series': book_form.book_series.data,
            'author_first_name':
                ','.join(book_form.book_author_first_name.data),
            'author_last_name':
                ','.join(book_form.book_author_last_name.data),
            'editor_first_name':
                ','.join(book_form.book_editor_first_name.data),
            'editor_last_name':
                ','.join(book_form.book_editor_last_name.data),
            'last_edited_by': current_user.id,
            'publisher': book_form.book_publisher.data,
            'month': book_form.book_publication_month.data,
            'year': book_form.book_publication_year.data,
            'description': book_form.book_description.data,
            'link': book_form.book_link.data,
            'file': book_form.book_file_urls.data,
            'document_status': submit,
            'broken_link': NOT_BROKEN,
        }
        if entry is not None:
            corpus = entry.corpus
            if entry.link == book_form.book_link.data:
                kwargs['broken_link'] = entry.broken_link
            update_sql_object(entry, kwargs)
        else:
            new = True
            kwargs['posted_by'] = current_user.id
            article = Document(**kwargs)
            db.session.add(article)
            corpus = article.corpus
            db.session.commit()
            entry = article

        word_tokens = word_tokenize(corpus)
        filtered_corpus = [
            stemmer.stem(w) for w in word_tokens if w not in stop_words
        ]
        new_tf = Counter(filtered_corpus)

        if new:
            update_idf(pre_tf={}, post_tf=new_tf, doc_id=article.id)

        else:
            update_idf(pre_tf=entry.tf, post_tf=new_tf, doc_id=entry.id)

        entry.tf = Counter(filtered_corpus)

        Tagged.query.filter_by(document_id=entry.id).delete()
        tag_ids = [int(x) for x in book_form.book_tags.data]
        for tag_id in tag_ids:
            tagged = Tagged(
                tag_id=tag_id,
                document_id=entry.id,
                tag_name=Tag.query.get(tag_id).tag
            )
            db.session.add(tagged)

        db.session.commit()
        flash(
            'Book \"{}\" successfully saved'.format(
                book_form.book_title.data), 'form-success')

    elif doc_type == 'journal_article':
        journal_form = form
        new = False
        kwargs = {
            'doc_type': "journal_article",
            'title': journal_form.journal_title.data,
            'author_first_name':
                ','.join(journal_form.journal_author_first_name.data),
            'author_last_name':
                ','.join(journal_form.journal_author_last_name.data),
            'last_edited_by': current_user.id,
            'publisher': journal_form.journal_publication.data,
            'volume': journal_form.journal_volume.data,
            'page_start': journal_form.journal_start_page.data,
            'page_end': journal_form.journal_end_page.data,
            'day': journal_form.journal_publication_day.data,
            'month': journal_form.journal_publication_month.data,
            'year': journal_form.journal_publication_year.data,
            'description': journal_form.journal_description.data,
            'link': journal_form.journal_link.data,
            'file': journal_form.journal_file_urls.data,
            'document_status': submit,
            'broken_link': NOT_BROKEN,
        }
        if entry is not None:
            corpus = entry.corpus
            if entry.link == journal_form.journal_link.data:
                kwargs['broken_link'] = entry.broken_link
            update_sql_object(entry, kwargs)
        else:
            new = True
            kwargs['posted_by'] = current_user.id
            article = Document(**kwargs)
            db.session.add(article)
            corpus = article.corpus
            db.session.commit()
            entry = article

        word_tokens = word_tokenize(corpus)
        filtered_corpus = [
            stemmer.stem(w) for w in word_tokens if w not in stop_words
        ]
        new_tf = Counter(filtered_corpus)

        if new:
            update_idf(pre_tf={}, post_tf=new_tf, doc_id=article.id)

        else:
            update_idf(pre_tf=entry.tf, post_tf=new_tf, doc_id=entry.id)

        entry.tf = Counter(filtered_corpus)

        Tagged.query.filter_by(document_id=entry.id).delete()
        tag_ids = [int(x) for x in journal_form.journal_tags.data]
        for tag_id in tag_ids:
            tagged = Tagged(
                tag_id=tag_id,
                document_id=entry.id,
                tag_name=Tag.query.get(tag_id).tag
            )
            db.session.add(tagged)

        db.session.commit()

        flash(
            'Article \"{}\" successfully saved'.format(
                journal_form.journal_title.data), 'form-success')
    elif doc_type == 'law':
        law_form = form
        new = False
        kwargs = {
            'doc_type': "law",
            'day': law_form.law_enactment_day.data,
            'month': law_form.law_enactment_month.data,
            'year': law_form.law_enactment_year.data,
            'citation': law_form.law_citation.data,
            'region': law_form.law_region.data,
            'last_edited_by': current_user.id,
            'title': law_form.law_title.data,
            'description': law_form.law_description.data,
            'country': law_form.law_country.data,
            'link': law_form.law_link.data,
            'file': law_form.law_file_urls.data,
            'govt_body': law_form.law_government_body.data,
            'section': law_form.law_section.data,
            'document_status': submit,
            'broken_link': NOT_BROKEN,
        }

        if entry is not None:
            corpus = entry.corpus
            if entry.link == law_form.law_link.data:
                kwargs['broken_link'] = entry.broken_link
            update_sql_object(entry, kwargs)
        else:
            new = True
            kwargs['posted_by'] = current_user.id
            article = Document(**kwargs)
            db.session.add(article)
            corpus = article.corpus
            db.session.commit()
            entry = article

        word_tokens = word_tokenize(corpus)
        filtered_corpus = [
            stemmer.stem(w) for w in word_tokens if w not in stop_words
        ]
        new_tf = Counter(filtered_corpus)

        if new:
            update_idf(pre_tf={}, post_tf=new_tf, doc_id=article.id)

        else:
            update_idf(pre_tf=entry.tf, post_tf=new_tf, doc_id=entry.id)

        entry.tf = Counter(filtered_corpus)

        Tagged.query.filter_by(document_id=entry.id).delete()
        tag_ids = [int(x) for x in law_form.law_tags.data]
        for tag_id in tag_ids:
            tagged = Tagged(
                tag_id=tag_id,
                document_id=entry.id,
                tag_name=Tag.query.get(tag_id).tag
            )
            db.session.add(tagged)

        db.session.commit()
        flash(
            'Law \"{}\" successfully saved'.format(
                law_form.law_title.data), 'form-success')
    elif doc_type == 'video':
        video_form = form
        new = False
        kwargs = {
            'doc_type': "video",
            'title': video_form.video_title.data,
            'author_first_name': ','.join(video_form.director_first_name.data),
            'author_last_name': ','.join(video_form.director_last_name.data),
            'last_edited_by': current_user.id,
            'series': video_form.video_series.data,
            'source': video_form.video_source.data,
            'publisher': video_form.video_publisher.data,
            'studio': video_form.video_studio.data,
            'country': video_form.video_country.data,
            'day': video_form.video_publication_day.data,
            'month': video_form.video_publication_month.data,
            'year': video_form.video_publication_year.data,
            'description': video_form.video_description.data,
            'link': video_form.video_link.data,
            'file': video_form.video_file_urls.data,
            'document_status': submit,
            'broken_link': NOT_BROKEN,
        }

        if entry is not None:
            corpus = entry.corpus
            if entry.link == video_form.video_link.data:
                kwargs['broken_link'] = entry.broken_link
            update_sql_object(entry, kwargs)
        else:
            new = True
            kwargs['posted_by'] = current_user.id
            article = Document(**kwargs)
            kwargs['posted_by'] = current_user.id
            db.session.add(article)
            corpus = article.corpus
            db.session.commit()
            entry = article

        word_tokens = word_tokenize(corpus)
        filtered_corpus = [
            stemmer.stem(w) for w in word_tokens if w not in stop_words
        ]
        new_tf = Counter(filtered_corpus)

        if new:
            update_idf(pre_tf={}, post_tf=new_tf, doc_id=article.id)

        else:
            update_idf(pre_tf=entry.tf, post_tf=new_tf, doc_id=entry.id)

        entry.tf = Counter(filtered_corpus)

        Tagged.query.filter_by(document_id=entry.id).delete()
        tag_ids = [int(x) for x in video_form.video_tags.data]
        for tag_id in tag_ids:
            tagged = Tagged(
                tag_id=tag_id,
                document_id=entry.id,
                tag_name=Tag.query.get(tag_id).tag
            )
            db.session.add(tagged)

        db.session.commit()
        flash(
            'Video \"{}\" successfully saved'.format(
                video_form.video_title.data), 'form-success')

    elif doc_type == 'report':
        report_form = form
        new = False
        kwargs = {
            'doc_type': "report",
            'title': report_form.report_title.data,
            'author_first_name':
                ','.join(report_form.report_author_first_name.data),
            'author_last_name':
                ','.join(report_form.report_author_last_name.data),
            'last_edited_by': current_user.id,
            'publisher': report_form.report_publisher.data,
            'day': report_form.report_publication_day.data,
            'month': report_form.report_publication_month.data,
            'year': report_form.report_publication_year.data,
            'description': report_form.report_description.data,
            'link': report_form.report_link.data,
            'file': report_form.report_file_urls.data,
            'document_status': submit,
            'broken_link': NOT_BROKEN,
        }
        if entry is not None:
            corpus = entry.corpus
            if entry.link == report_form.report_link.data:
                kwargs['broken_link'] = entry.broken_link
            update_sql_object(entry, kwargs)
        else:
            new = True
            kwargs['posted_by'] = current_user.id
            article = Document(**kwargs)
            db.session.add(article)
            corpus = article.corpus
            db.session.commit()
            entry = article

        word_tokens = word_tokenize(corpus)
        filtered_corpus = [
            stemmer.stem(w) for w in word_tokens if w not in stop_words
        ]
        new_tf = Counter(filtered_corpus)

        if new:
            update_idf(pre_tf={}, post_tf=new_tf, doc_id=article.id)

        else:
            update_idf(pre_tf=entry.tf, post_tf=new_tf, doc_id=entry.id)

        entry.tf = Counter(filtered_corpus)

        Tagged.query.filter_by(document_id=entry.id).delete()
        tag_ids = [int(x) for x in report_form.report_tags.data]
        for tag_id in tag_ids:
            tagged = Tagged(
                tag_id=tag_id,
                document_id=entry.id,
                tag_name=Tag.query.get(tag_id).tag
            )
            db.session.add(tagged)

        db.session.commit()
        flash(
            'Report \"{}\" successfully saved'.format(
                report_form.report_title.data), 'form-success')

    elif doc_type == 'other':
        other_form = form
        new = False
        kwargs = {
            'doc_type': "other",
            'title': other_form.other_title.data,
            'author_first_name':
                ','.join(other_form.other_author_first_name.data),
            'author_last_name':
                ','.join(other_form.other_author_last_name.data),
            'posted_by': current_user.id,
            'last_edited_by':
                current_user.first_name + " " + current_user.last_name,
            'day': other_form.other_publication_day.data,
            'month': other_form.other_publication_month.data,
            'year': other_form.other_publication_year.data,
            'description': other_form.other_description.data,
            'source': other_form.other_source.data,
            'link': other_form.other_link.data,
            'file': other_form.other_file_urls.data,
            'other_type': other_form.other_document_type.data,
            'document_status': submit,
            'broken_link': NOT_BROKEN,
        }
        if entry is not None:
            corpus = entry.corpus
            if entry.link == other_form.other_link.data:
                kwargs['broken_link'] = entry.broken_link
            update_sql_object(entry, kwargs)
        else:
            new = True
            article = Document(**kwargs)
            db.session.add(article)
            corpus = article.corpus
            db.session.commit()
            entry = article

        word_tokens = word_tokenize(corpus)
        filtered_corpus = [
            stemmer.stem(w) for w in word_tokens if w not in stop_words
        ]
        new_tf = Counter(filtered_corpus)

        if new:
            update_idf(pre_tf={}, post_tf=new_tf, doc_id=article.id)

        else:
            update_idf(pre_tf=entry.tf, post_tf=new_tf, doc_id=entry.id)

        entry.tf = Counter(filtered_corpus)

        Tagged.query.filter_by(document_id=entry.id).delete()
        tag_ids = [int(x) for x in other_form.other_tags.data]
        for tag_id in tag_ids:
            tagged = Tagged(
                tag_id=tag_id,
                document_id=entry.id,
                tag_name=Tag.query.get(tag_id).tag
            )
            db.session.add(tagged)

        db.session.commit()
        flash(
            'Other \"{}\" successfully saved'.format(
                other_form.other_title.data), 'form-success')


def update_idf(doc_id, pre_tf, post_tf):
    pre_set = set(pre_tf.keys())
    post_set = set(post_tf.keys())
    remove_set = pre_set.difference(post_set)
    add_set = post_set.difference(pre_set)
    for i in remove_set:
        term = Idf.query.get(i)
        if term is not None:
            if doc_id in term.docs:
                term.docs.remove(doc_id)
    for i in add_set:
        term = Idf.query.get(i)
        if term is not None:
            term.docs.append(doc_id)
        else:
            term = Idf(
                term=i,
                docs=[doc_id]
            )
            db.session.add(term)
    db.session.commit()


def update_tags(doc_id, tags):
    tags = tags.split(',')
    tags = [t.strip() for t in tags]
    for t in tags:
        if t.strip() != '':
            tag = Tag.query.filter(
                func.lower(Tag.tag) == func.lower(t)
            ).first()
            if not tag:
                tag = Tag(tag=t)
                db.session.add(tag)
                db.session.commit()
            tagged = Tagged(
                tag_id=tag.id,
                document_id=doc_id,
                tag_name=tag.tag
            )
            db.session.add(tagged)
            db.session.commit()


@admin.route('/ignore_link/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def ignore_link(id):
    resource = Document.query.get(id)
    resource.broken_link = IGNORE
    db.session.commit()
    return redirect(url_for('admin.view_broken_links'))


@admin.route('/upload_and_download', methods=['GET', 'POST'])
@csrf.exempt
@login_required
@admin_required
def upload_and_download():
    download_form = DownloadForm()
    document_ids = db.session.query(Document.id).all()
    document_ids = set([int(r) for (r,) in document_ids])

    if request.method == 'POST':
        if "Download" in request.form.values():

            file_path = os.environ["HOME"] + "/Downloads/"
            documents = Document.query.order_by(Document.id.desc()).all()

            if download_form.book.data:
                with io.open(
                    file_path + 'book.csv', 'w', newline=''
                ) as csvfile:

                    csv_writer = csv.writer(csvfile)

                    csv_writer.writerow([
                        'Id', 'Title', 'Author First Name', 'Author Last Name',
                        'Editor First Name', 'Editor Last Name', 'Volume',
                        'Edition', 'Series', 'Publisher Name',
                        'Publication Month', 'Publication Year', 'Description',
                        'Link', 'File', 'Document Status', 'Tags'
                    ])

                    for d in documents:
                        if d.doc_type == "book":
                            csv_writer.writerow([
                                d.id,
                                d.title,
                                d.author_first_name,
                                d.author_last_name,
                                d.editor_first_name,
                                d.editor_last_name,
                                d.volume,
                                d.edition,
                                d.series,
                                d.publisher,
                                d.month,
                                d.year,
                                d.description,
                                d.link,
                                d.file,
                                d.document_status,
                                ", ".join(t.tag_name for t in d.tags)])

            if download_form.news_article.data is True:
                with io.open(
                    file_path + 'news_article.csv', 'w', newline=''
                ) as csvfile:
                    csv_writer = csv.writer(csvfile)

                    csv_writer.writerow([
                        'Id', 'Title', 'Author First Name', 'Author Last Name',
                        'Publication', 'Publication Day', 'Publication Month',
                        'Publication Year', 'Description', 'Link', 'File',
                        'Document Status', 'Tags'
                    ])

                    for d in documents:
                        if d.doc_type == "news_article":
                            csv_writer.writerow([
                                d.id,
                                d.title,
                                d.author_first_name,
                                d.author_last_name,
                                d.publisher,
                                d.day,
                                d.month,
                                d.year,
                                d.description,
                                d.link,
                                d.file,
                                d.document_status,
                                ", ".join(t.tag_name for t in d.tags)])

            if download_form.journal_article.data is True:
                with io.open(
                    file_path + 'journal_article.csv', 'w', newline=''
                ) as csvfile:
                    csv_writer = csv.writer(csvfile)

                    csv_writer.writerow([
                        'Id', 'Title', 'Author First Name', 'Author Last Name',
                        'Publication', 'Volume', 'Start Page', 'End Page',
                        'Publication Day', 'Publication Month',
                        'Publication Year', 'Description', 'Link', 'File',
                        'Document Status', 'Tags'
                    ])

                    for d in documents:
                        if d.doc_type == "journal_article":
                            csv_writer.writerow([
                                d.id,
                                d.title,
                                d.author_first_name,
                                d.author_last_name,
                                d.publisher,
                                d.volume,
                                d.page_start,
                                d.page_end,
                                d.day,
                                d.month,
                                d.year,
                                d.description,
                                d.link,
                                d.file,
                                d.document_status,
                                ", ".join(t.tag_name for t in d.tags)])

            if download_form.law.data is True:
                with io.open(
                    file_path + 'law.csv', 'w', newline=''
                ) as csvfile:
                    csv_writer = csv.writer(csvfile)

                    csv_writer.writerow([
                        'Id',
                        'Title',
                        'Citation',
                        'Government Body*',
                        'Section',
                        'Region',
                        'Country',
                        'Enactment Day',
                        'Enactment Month',
                        'Enactment Year',
                        'Description',
                        'Link',
                        'File',
                        'Document Status',
                        'Tags'
                    ])

                    for d in documents:
                        if d.doc_type == "law":
                            csv_writer.writerow([
                                d.id,
                                d.title,
                                d.citation,
                                d.govt_body,
                                d.section,
                                d.region,
                                d.country,
                                d.day,
                                d.month,
                                d.year,
                                d.description,
                                d.link,
                                d.file,
                                d.document_status,
                                ", ".join(t.tag_name for t in d.tags)])

            if download_form.video.data is True:
                with io.open(
                    file_path + 'video.csv', 'w', newline=''
                ) as csvfile:
                    csv_writer = csv.writer(csvfile)

                    csv_writer.writerow([
                        'Id',
                        'Title',
                        'Series',
                        'First Name',
                        'Last Name',
                        'Release Day',
                        'Release Month',
                        'Release Year',
                        'Network/Studio',
                        'Published/Uploaded By',
                        'Source',
                        'Country',
                        'Description',
                        'Link',
                        'File',
                        'Document Status',
                        'Tags'
                    ])

                    for d in documents:
                        if d.doc_type == "video":
                            csv_writer.writerow([
                                d.id,
                                d.title,
                                d.series,
                                d.author_first_name,
                                d.author_last_name,
                                d.day,
                                d.month,
                                d.year,
                                d.studio,
                                d.publisher,
                                d.source,
                                d.country,
                                d.description,
                                d.link,
                                d.file,
                                d.document_status,
                                ", ".join(t.tag_name for t in d.tags)])

            if download_form.report.data is True:
                with io.open(
                    file_path + 'report.csv', 'w', newline=''
                ) as csvfile:
                    csv_writer = csv.writer(csvfile)

                    csv_writer.writerow([
                        'Id',
                        'Title',
                        'First Name',
                        'Last Name',
                        'Publisher',
                        'Day',
                        'Month',
                        'Year',
                        'Description',
                        'Link',
                        'File',
                        'Document Status',
                        'Tags'
                    ])

                    for d in documents:
                        if d.doc_type == "report":
                            csv_writer.writerow([
                                d.id,
                                d.title,
                                d.author_first_name,
                                d.author_last_name,
                                d.publisher,
                                d.day,
                                d.month,
                                d.year,
                                d.description,
                                d.link,
                                d.file,
                                d.document_status,
                                ", ".join(t.tag_name for t in d.tags)])

            if download_form.other.data is True:
                with io.open(
                    file_path + 'other.csv', 'w', newline=''
                ) as csvfile:
                    csv_writer = csv.writer(csvfile)

                    csv_writer.writerow([
                        'Id',
                        'Title',
                        'Author First Name',
                        'Author Last Name',
                        'Other Document Type',
                        'Publication Day',
                        'Publication Month',
                        'Publication Year',
                        'Description',
                        'Link',
                        'File',
                        'Document Status',
                        'Tags'
                    ])

                    for d in documents:
                        if d.doc_type == "other":
                            csv_writer.writerow([
                                d.id,
                                d.title,
                                d.author_first_name,
                                d.author_last_name,
                                d.other_type,
                                d.day,
                                d.month,
                                d.year,
                                d.description,
                                d.link,
                                d.file,
                                d.document_status,
                                ", ".join(t.tag_name for t in d.tags)])

            flash('Download Successful', 'form-success')
            return render_template('admin/upload.html', form=download_form)

        else:
            stemmer = SnowballStemmer("english", ignore_stopwords=True)
            stop_words = set(stopwords.words('english'))
            f = request.files['book-file']
            name = f.filename
            stream = io.StringIO(f.stream.read().decode("UTF8"), newline=None)
            csv_input = csv.reader(stream)
            cu_id = current_user.id

            def populate_db():
                is_new_document = True
                header_row = True
                for row in csv_input:
                    document = None
                    tags = None
                    now = datetime.datetime.utcnow().strftime(
                        "%a %b %d %H:%M:%S %Z %Y"
                    )
                    if header_row:
                        header_row = False
                        continue

                    if row[0]:
                        row[0] = int(row[0])
                    else:
                        row[0] = None

                    if row[0] and row[0] in document_ids:
                        is_new_document = False
                        entry = Document.query.filter_by(id=row[0]).first()
                        update_idf(pre_tf=entry.tf, post_tf={}, doc_id=entry.id)
                        Tagged.query.filter_by(document_id=entry.id).delete()
                        db.session.delete(entry)
                    else:
                        row[0] = None

                    if name == "book.csv" \
                            and row[1] != "Example":

                        # document status
                        ds = row[15]
                        if ds == '':
                            ds = "published"

                        int_fields = [11]
                        for i in int_fields:
                            if row[i] == '':
                                row[i] = None

                        tags = row[16]

                        document = Document(
                            id=row[0],
                            doc_type="book",
                            title=row[1],
                            author_first_name=row[2],
                            author_last_name=row[3],
                            editor_first_name=row[4],
                            editor_last_name=row[5],
                            volume=row[6],
                            edition=row[7],
                            series=row[8],
                            publisher=row[9],
                            month=row[10],
                            year=row[11],
                            description=row[12],
                            link=row[13],
                            file=row[14],
                            last_edited_date=now,
                            last_edited_by=cu_id,
                            document_status=ds
                        )

                    if name == "news_article.csv" \
                            and row[1] != "Example":

                        ds = row[11]
                        if ds == '':
                            ds = "published"

                        int_fields = [5, 7]
                        for i in int_fields:
                            if row[i] == '':
                                row[i] = None

                        tags = row[12]

                        document = Document(
                            id=row[0],
                            doc_type="news_article",
                            title=row[1],
                            author_first_name=row[2],
                            author_last_name=row[3],
                            publisher=row[4],
                            day=row[5],
                            month=row[6],
                            year=row[7],
                            description=row[8],
                            link=row[9],
                            file=row[10],
                            last_edited_date=now,
                            last_edited_by=cu_id,
                            document_status=ds
                        )

                    if name == "journal_article.csv" \
                            and row[1] != "Example":

                        # document status
                        ds = row[15]
                        if ds == '':
                            ds = "published"

                        int_fields = [9, 11]
                        for i in int_fields:
                            if row[i] == '':
                                row[i] = None

                        tags = row[16]

                        document = Document(
                            id=row[0],
                            doc_type="journal_article",
                            title=row[1],
                            author_first_name=row[2],
                            author_last_name=row[3],
                            publisher=row[4],
                            volume=row[5],
                            issue=row[6],
                            page_start=row[7],
                            page_end=row[8],
                            day=row[9],
                            month=row[10],
                            year=row[11],
                            description=row[12],
                            link=row[13],
                            file=row[14],
                            last_edited_date=now,
                            last_edited_by=cu_id,
                            document_status=ds
                        )

                    if name == "law.csv" and row[1] != "Example":

                        # document status
                        ds = row[13]
                        if ds == '':
                            ds = "published"

                        int_fields = [7, 9]
                        for i in int_fields:
                            if row[i] == '':
                                row[i] = None

                        tags = row[14]

                        document = Document(
                            id=row[0],
                            doc_type="law",
                            title=row[1],
                            citation=row[2],
                            govt_body=row[3],
                            section=row[4],
                            region=row[5],
                            country=row[6],
                            day=row[7],
                            month=row[8],
                            year=row[9],
                            description=row[10],
                            link=row[11],
                            file=row[12],
                            last_edited_date=now,
                            last_edited_by=cu_id,
                            document_status=ds
                        )

                    if name == "video.csv" \
                            and row[1] != "Example":

                        # document status
                        ds = row[15]
                        if ds is '':
                            ds = "published"

                        int_fields = [5, 7]
                        for i in int_fields:
                            if row[i] == '':
                                row[i] = None

                        tags = row[16]

                        document = Document(
                            id=row[0],
                            doc_type="video",
                            title=row[1],
                            series=row[2],
                            author_first_name=row[3],
                            author_last_name=row[4],
                            day=row[5],
                            month=row[6],
                            year=row[7],
                            studio=row[8],
                            publisher=row[9],
                            source=row[10],
                            country=row[11],
                            description=row[12],
                            link=row[13],
                            file=row[14],
                            last_edited_date=now,
                            last_edited_by=cu_id,
                            document_status=ds
                        )

                    if name == "report.csv" \
                            and row[1] != "Example":

                        ds = row[11]
                        if ds is '':
                            ds = "published"

                        int_fields = [5, 7]
                        for i in int_fields:
                            if row[i] == '':
                                row[i] = None

                        tags = row[12]

                        document = Document(
                            id=row[0],
                            doc_type="report",
                            title=row[1],
                            author_first_name=row[2],
                            author_last_name=row[3],
                            publisher=row[4],
                            day=row[5],
                            month=row[6],
                            year=row[7],
                            description=row[8],
                            link=row[9],
                            file=row[10],
                            last_edited_date=now,
                            last_edited_by=cu_id,
                            document_status=ds
                        )

                    if name == "other.csv" \
                            and row[1] != "Example":

                        ds = row[12]
                        if ds is '':
                            ds = "published"

                        int_fields = [6, 8]
                        for i in int_fields:
                            if row[i] == '':
                                row[i] = None

                        tags = row[13]

                        document = Document(
                            id=row[0],
                            doc_type="other",
                            title=row[1],
                            author_first_name=row[2],
                            author_last_name=row[3],
                            other_type=row[4],
                            source=row[5],
                            day=row[6],
                            month=row[7],
                            year=row[8],
                            description=row[9],
                            link=row[10],
                            file=row[11],
                            last_edited_date=now,
                            last_edited_by=cu_id,
                            document_status=ds
                        )

                    if document is not None:
                        if is_new_document:
                            document.posted_date = now
                            document.posted_by = cu_id
                        db.session.add(document)
                        db.session.commit()
                        doc_id = document.id
                        word_tokens = word_tokenize(document.corpus)
                        filtered_corpus = [
                            stemmer.stem(w) for w in word_tokens if w not in stop_words
                        ]
                        new_tf = Counter(filtered_corpus)
                        document.tf = new_tf
                        update_idf(pre_tf={}, post_tf=new_tf, doc_id=doc_id)
                        update_tags(doc_id=doc_id, tags=tags)

            thread = threading.Thread(target=populate_db)
            thread.start()

        return render_template('admin/upload.html', form=download_form)

    return render_template('admin/upload.html', form=download_form)
