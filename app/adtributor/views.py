from flask import (Blueprint, abort, flash, redirect, render_template, request, jsonify,
                   url_for)

from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError
from sqlalchemy import update

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
    DraftEntryForm,
    JournalArticleForm,
    VideoForm
)
from app.decorators import contributor_required, admin_required
from app.models import EditableHTML, Role, User, Tag, Suggestion, Document

import json
import boto3
import boto.s3
import sys
import urllib
import tempfile
from boto.s3.key import Key
import boto.s3.connection
import ssl
from werkzeug import secure_filename
from collections import Counter
from app.email import send_email

admin = Blueprint('admin', __name__)
contributor = Blueprint('contributor', __name__)

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


@admin.route('/index',methods=['GET', 'POST'])
@admin_required
@contributor.route('/index',methods=['GET', 'POST'])
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


@admin.route('/user/<int:user_id>/change-account-type', methods=['GET', 'POST'])
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
    """Endpoint for deleting document tags."""
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
    """Review suggestions for ."""
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


@admin.route('/view_all_drafts',methods=['GET', 'POST'])
@admin_required
@contributor.route('/view_all_drafts',methods=['GET', 'POST'])
@contributor_required
@login_required
def view_all_drafts():
    user_name = current_user.first_name + " " + current_user.last_name
    contributions = Document.query.filter(Document.posted_by == user_name).order_by(Document.id.desc()).all()
    return render_template('adtributor/draft_contributions.html', contributions=contributions, user_type='contributor')


@admin.route('/publish/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def publish_contribution(id):
    """Contribution Review page."""
    contribution = Document.query.filter_by(id=id).first()
    contribution.document_status = "published"
    db.session.add(contribution)
    db.session.commit()
    contributions = Document.query.order_by(Document.id.desc()).all()
    return redirect(url_for('admin.review_contributions'))


@admin.route('/review_contributions',methods=['GET', 'POST'])
@login_required
@admin_required
def review_contributions():
    contributions = Document.query.filter(Document.document_status != 'draft').filter(Document.document_status != 'published').order_by(Document.id.desc()).all()
    return render_template('admin/review_contributions.html', contributions=contributions)


@admin.route('/see_contribution/<int:id>', methods=['GET'])
@login_required
@admin_required
def other_contribution(id):
    """Contribution Review page."""
    contribution = Document.query.get(id)
    return render_template('adtributor/contribution.html', contribution=contribution, user_type='admin', comes_from='contribution')


@admin.route('/contribution/<int:id>', methods=['GET'])
@admin_required
@contributor.route('/contribution/<int:id>', methods=['GET'])
@contributor_required
@login_required
def contribution(id):
    contribution = Document.query.get(id)
    return render_template('adtributor/contribution.html', contribution=contribution, user_type='contributor')


@admin.route('/draft/book/<int:id>', methods=['GET', 'POST'])
@admin_required
@contributor.route('/draft/book/<int:id>', methods=['GET', 'POST'])
@contributor_required
@login_required
def view_book_draft(id):
    contribution = Document.query.get(id)
    book_entry = Document.query.filter_by(id=id).first()
    book_form = BookForm(
        doc_type = "book",
        book_title = book_entry.title,
        book_volume = book_entry.volume,
        book_edition = book_entry.edition,
        book_series = book_entry.series,
        book_author_first_name = book_entry.author_first_name,
        book_author_last_name = book_entry.author_last_name,
        book_publisher_name = book_entry.name,
        book_publication_month = book_entry.month,
        book_publication_year = book_entry.year,
        book_description = book_entry.description,
        book_link = book_entry.link)

    if request.method == 'POST':
        if book_form.validate_on_submit():
            if "Save Book" in request.form.values():
                save_or_submit_doc(book_form, doc_type='book', submit='draft')

            if "Submit Book" in request.form.values():
                save_or_submit_doc(book_form, doc_type='book', submit=dest_from_role())

            return view_all_drafts()


    return render_template('adtributor/edit_book_draft.html', book_form=book_form, c=contribution)


@admin.route('/draft/article/<int:id>', methods=['GET', 'POST'])
@admin_required
@contributor.route('/draft/article/<int:id>', methods=['GET', 'POST'])
@contributor_required
@login_required
def view_article_draft(id):
    contribution = Document.query.get(id)
    article_entry = Document.query.filter_by(id=id).first()
    article_form = ArticleForm(
                    doc_type = "article",
                    article_title = article_entry.title,
                    article_author_first_name = article_entry.author_first_name,
                    article_author_last_name = article_entry.author_last_name,
                    article_publication = article_entry.name,
                    article_publication_day = article_entry.day,
                    article_publication_month = article_entry.month,
                    article_publication_year = article_entry.year,
                    article_description = article_entry.description,
                    article_link = article_entry.link,
                    document_status = "draft")

    if request.method == 'POST':
        if article_form.validate_on_submit():
            if "Save Article" in request.form.values():
                save_or_submit_doc(article_form, doc_type='article', submit='draft')

            if "Submit Article" in request.form.values():
                save_or_submit_doc(article_form, doc_type='article', submit=dest_from_role())

            return view_all_drafts()

    return render_template('adtributor/edit_article_draft.html', article_form=article_form, c=contribution)


    """Contribution Review page."""
    contribution = Document.query.get(id)
    return render_template('adtributor/edit_article_draft.html', contribution=contribution)


@admin.route('/draft/journal/<int:id>', methods=['GET', 'POST'])
@admin_required
@contributor.route('/draft/journal/<int:id>', methods=['GET', 'POST'])
@contributor_required
@login_required
def view_journal_draft(id):
    contribution = Document.query.get(id)
    journal_entry = Document.query.filter_by(id=id).first()
    journal_form = JournalArticleForm(
                    doc_type = "journal",
                    article_title = journal_entry.title,
                    article_author_first_name = journal_entry.author_first_name,
                    article_author_last_name = journal_entry.author_last_name,
                    publisher_name = journal_entry.name,
                    volume = journal_entry.volume,
                    start_page = journal_entry.page_start,
                    end_page = journal_entry.page_end,
                    article_publication = journal_entry.name,
                    article_publication_day = journal_entry.day,
                    article_publication_month = journal_entry.month,
                    article_publication_year = journal_entry.year,
                    article_description = journal_entry.description,
                    article_link = journal_entry.link,
                    document_status = "draft")

    if request.method == 'POST':
        if journal_form.validate_on_submit():

            if "Save Article" in request.form.values():
                save_or_submit_doc(journal_form, doc_type='journal', submit='draft')

            if "Submit Article" in request.form.values():
                save_or_submit_doc(journal_form, doc_type='journal', submit=dest_from_role())

            return view_all_drafts()

    return render_template('adtributor/edit_journal_draft.html', journal_form=journal_form, c=contribution)


    """Contribution Review page."""
    contribution = Document.query.get(id)
    return render_template('adtributor/edit_article_draft.html', contribution=contribution)


@admin.route('/draft/law/<int:id>', methods=['GET', 'POST'])
@admin_required
@contributor.route('/draft/law/<int:id>', methods=['GET', 'POST'])
@contributor_required
@login_required
def view_law_draft(id):
    """Contribution Review page."""
    contribution = Document.query.get(id)
    law_entry = Document.query.filter_by(id=id).first()

    law_form = LawForm(
        doc_type = "law",
        law_title = law_entry.title,
        law_government_body = law_entry.govt_body,
        law_section = law_entry.section,
        law_citation = law_entry.citation,
        law_region = law_entry.region,
        law_enactment_day = law_entry.day,
        law_enactment_month = law_entry.month,
        law_enactment_year = law_entry.year,
        law_city = law_entry.city,
        law_state = law_entry.state,
        law_country = law_entry.country,
        law_description = law_entry.description,
        law_link = law_entry.link,
        document_status = "draft")

    if request.method == 'POST':
        if law_form.validate_on_submit():
            if "Save Law" in request.form.values():
                save_or_submit_doc(law_form, doc_type='law', submit='draft')

            if "Submit Law" in request.form.values():
                save_or_submit_doc(law_form, doc_type='law', submit=dest_from_role())

            return view_all_drafts()

    return render_template('adtributor/edit_law_draft.html', law_form=law_form, c=contribution)


@admin.route('draft/video/<int:id>', methods=['GET', 'POST'])
@admin_required
@contributor.route('draft/video/<int:id>', methods=['GET', 'POST'])
@contributor_required
@login_required
def view_video_draft(id):
    contribution = Document.query.get(id)
    video_entry = Document.query.filter_by(id=id).first()
    video_form = VideoForm(
                    doc_type = "video",
                    video_title = video_entry.title,
                    director_first_name = video_entry.author_first_name,
                    director_last_name = video_entry.author_last_name,
                    video_post_source = video_entry.post_source,
                    video_publisher = video_entry.name,
                    video_country = video_entry.country,
                    video_publication_day = video_entry.day,
                    video_publication_month = video_entry.month,
                    video_publication_year = video_entry.year,
                    video_description = video_entry.description,
                    video_link = video_entry.link,
                    document_status = "draft")

    if request.method == 'POST':
        if video_form.validate_on_submit():
            if "Save Video" in request.form.values():
                save_or_submit_doc(video_form, doc_type='video', submit='draft')

            if "Submit Video" in request.form.values():
                save_or_submit_doc(video_form, doc_type='video', submit=dest_from_role())

            return view_all_drafts()

    return render_template('adtributor/edit_video_draft.html', video_form=video_form, c=contribution)


@admin.route('/draft/report/<int:id>', methods=['GET', 'POST'])
@admin_required
@contributor.route('/draft/report/<int:id>', methods=['GET', 'POST'])
@contributor_required
@login_required
def view_report_draft(id):
    contribution = Document.query.get(id)
    report_entry = Document.query.filter_by(id=id).first()
    report_form = ReportForm(
        doc_type = "report",
        report_title = report_entry.title,
        report_author_first_name = report_entry.author_first_name,
        report_author_last_name = report_entry.author_last_name,
        book_publisher_name = report_entry.name,
        book_publication_day= report_entry.day,
        book_publication_month = report_entry.month,
        book_publication_year = report_entry.year,
        book_description = report_entry.description,
        book_link = report_entry.link)
    if request.method == 'POST':
        if report_form.validate_on_submit():
            if "Save Book" in request.form.values():
                save_or_submit_doc(report_form, doc_type='report', submit='draft')

            if "Submit Book" in request.form.values():
                save_or_submit_doc(report_form, doc_type='report', submit=dest_from_role())

            return view_all_drafts()

    return render_template('adtributor/edit_report_draft.html', report_form=report_form, c=contribution)


@admin.route('/draft/other/<int:id>', methods=['GET', 'POST'])
@admin_required
@contributor.route('/draft/other/<int:id>', methods=['GET', 'POST'])
@contributor_required
@login_required
def view_other_draft(id):
    contribution = Document.query.get(id)
    other_entry = Document.query.filter_by(id=id).first()
    other_form = OtherForm(
                    doc_type = "other",
                    other_document_type = other_entry.other_type,
                    other_title = other_entry.title,
                    other_author_first_name = other_entry.author_first_name,
                    other_author_last_name = other_entry.author_last_name,
                    other_publication_day = other_entry.day,
                    other_publication_month = other_entry.month,
                    other_publication_year = other_entry.year,
                    other_description = other_entry.description,
                    other_link = other_entry.link,
                    document_status = "draft")

    if request.method == 'POST':
        if other_form.validate_on_submit():
            if "Save Other" in request.form.values():
                save_or_submit_doc(other_form, doc_type='other', submit='draft')

            if "Submit Law" in request.form.values():
                save_or_submit_doc(other_form, doc_type='other', submit=dest_from_role())

            return view_all_drafts()

    return render_template('adtributor/edit_other_draft.html', other_form=other_form, c=contribution)


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
                    save_or_submit_doc(book_form, doc_type='book', submit='draft')

                if "Submit Book" in request.form.values():
                    save_or_submit_doc(book_form, doc_type='book', submit=dest_from_role())

                return view_all_drafts()

            return render_template('adtributor/submit.html', book_form=book_form, report_form=report_form,
            article_form=article_form, law_form=law_form, other_form=other_form, journal_form = journal_form, video_form=video_form, active="book", user_type='contributor')

        if form_name == 'article_form':

            if article_form.validate_on_submit():

                if "Save Article" in request.form.values():
                    save_or_submit_doc(article_form, doc_type='article', submit='draft')

                if "Submit Article" in request.form.values():
                    save_or_submit_doc(article_form, doc_type='article', submit=dest_from_role())

                return view_all_drafts()

            return render_template('adtributor/submit.html', book_form=book_form, report_form=report_form,
            article_form=article_form, law_form=law_form, other_form=other_form, journal_form = journal_form, video_form = video_form, active="article", user_type='contributor')

        if form_name == 'journal_form':

            if journal_form.validate_on_submit():

                if "Save Article" in request.form.values():
                    save_or_submit_doc(journal_form, doc_type='journal', submit='draft')

                if "Submit Article" in request.form.values():
                    save_or_submit_doc(journal_form, doc_type='journal', submit=dest_from_role())

                return view_all_drafts()

            return render_template('adtributor/submit.html', book_form=book_form, report_form=report_form,
            article_form=article_form, law_form=law_form, other_form=other_form, journal_form = journal_form, video_form = video_form, active="journal", user_type='contributor')

        if form_name == 'law_form':

            if law_form.validate_on_submit():

                if "Save Law" in request.form.values():
                    save_or_submit_doc(law_form, doc_type='law', submit='draft')

                if "Submit Law" in request.form.values():
                    save_or_submit_doc(law_form, doc_type='law', submit=dest_from_role())

                return view_all_drafts()

            return render_template('adtributor/submit.html', book_form=book_form, report_form=report_form,
            article_form=article_form, law_form=law_form, other_form=other_form, journal_form = journal_form, video_form = video_form, active="law", user_type='contributor')

        if form_name == 'video_form':

            if video_form.validate_on_submit():

                if "Save Video" in request.form.values():
                    save_or_submit_doc(video_form, doc_type='video', submit='draft')

                if "Submit Video" in request.form.values():
                    save_or_submit_doc(video_form, doc_type='video', submit=dest_from_role())

                return view_all_drafts()

            return render_template('adtributor/submit.html', book_form=book_form, report_form=report_form,
            article_form=article_form, law_form=law_form, other_form=other_form, journal_form = journal_form, video_form = video_form, active="video", user_type='contributor')

        if form_name == 'report_form':

            if report_form.validate_on_submit():

                if "Save Report" in request.form.values():
                    save_or_submit_doc(report_form, doc_type='report', submit='draft')

                if "Submit Report" in request.form.values():
                    save_or_submit_doc(report_form, doc_type='report', submit=dest_from_role())

                return view_all_drafts()

            return render_template('adtributor/submit.html', book_form=book_form, report_form=report_form,
            article_form=article_form, law_form=law_form, other_form=other_form, journal_form = journal_form, video_form = video_form, active="report", user_type='contributor')

        if form_name == 'other_form':

            if other_form.validate_on_submit():

                if "Save Other" in request.form.values():
                    save_or_submit_doc(other_form, doc_type='other', submit='draft')

                if "Submit Other" in request.form.values():
                    save_or_submit_doc(other_form, doc_type='other', submit=dest_from_role())

                return view_all_drafts()

            return render_template('adtributor/submit.html', book_form=book_form, report_form=report_form,
            article_form=article_form, law_form=law_form, other_form=other_form, journal_form=journal_form, video_form=video_form, active="other", user_type='contributor')

    return render_template('adtributor/submit.html', book_form=book_form, report_form=report_form,
    article_form=article_form, law_form=law_form, other_form=other_form, journal_form=journal_form, video_form=video_form, active="book", user_type='contributor')


@admin.route('/contribution/book/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def contribution_book(id):
    contribution = Document.query.get(id)
    book_entry = Document.query.filter_by(id=id).first()
    book_form = BookForm(
        doc_type = "book",
        book_title = book_entry.title,
        book_volume = book_entry.volume,
        book_edition = book_entry.edition,
        book_series = book_entry.series,
        book_author_first_name = book_entry.author_first_name,
        book_author_last_name = book_entry.author_last_name,
        book_publisher_name = book_entry.name,
        book_publication_month = book_entry.month,
        book_publication_year = book_entry.year,
        book_description = book_entry.description,
        book_link = book_entry.link)
    if request.method == 'POST':
        if book_form.validate_on_submit():
            if "Save Book" in request.form.values():
                save_or_submit_doc(book_form, doc_type='book', submit="under review")

            if "Submit Book" in request.form.values():
                save_or_submit_doc(book_form, doc_type='book', submit="published")

            return view_all_drafts()

    return render_template('adtributor/edit_book_draft.html', book_form=book_form, c=contribution)


@admin.route('/contribution/article/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def contribution_article(id):
    contribution = Document.query.get(id)
    article_entry = Document.query.filter_by(id=id).first()
    article_form = ArticleForm(
                    doc_type = "article",
                    article_title = article_entry.title,
                    article_author_first_name = article_entry.author_first_name,
                    article_author_last_name = article_entry.author_last_name,
                    article_publication = article_entry.name,
                    article_publication_day = article_entry.day,
                    article_publication_month = article_entry.month,
                    article_publication_year = article_entry.year,
                    article_description = article_entry.description,
                    article_link = article_entry.link,
                    document_status = "draft")

    if request.method == 'POST':
        if article_form.validate_on_submit():
            if "Save Article" in request.form.values():
                save_or_submit_doc(article_form, doc_type='article', submit="under review")

            if "Submit Article" in request.form.values():
                save_or_submit_doc(article_form, doc_type='article', submit="published")

            return view_all_drafts()

    return render_template('adtributor/edit_article_draft.html', article_form=article_form, c=contribution)


@admin.route('/contribution/journal/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def contribution_journal(id):
    contribution = Document.query.get(id)
    journal_entry = Document.query.filter_by(id=id).first()
    journal_form = JournalArticleForm(
                    doc_type = "journal",
                    article_title = journal_entry.title,
                    article_author_first_name = journal_entry.author_first_name,
                    article_author_last_name = journal_entry.author_last_name,
                    publisher_name = journal_entry.name,
                    volume = journal_entry.volume,
                    start_page = journal_entry.page_start,
                    end_page = journal_entry.page_end,
                    article_publication = journal_entry.name,
                    article_publication_day = journal_entry.day,
                    article_publication_month = journal_entry.month,
                    article_publication_year = journal_entry.year,
                    article_description = journal_entry.description,
                    article_link = journal_entry.link,
                    document_status = "draft")

    if request.method == 'POST':
        if journal_form.validate_on_submit():
            if "Save Article" in request.form.values():
                save_or_submit_doc(journal_form, doc_type='journal', submit="under review")

            if "Submit Article" in request.form.values():
                save_or_submit_doc(journal_form, doc_type='journal', submit="published")

            return view_all_drafts()


    return render_template('adtributor/edit_journal_draft.html', journal_form=journal_form, c=contribution)


@admin.route('/contribution/law/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def contribution_law(id):
    """Contribution Review page."""
    contribution = Document.query.get(id)
    law_entry = Document.query.filter_by(id=id).first()

    law_form = LawForm(
        doc_type = "law",
        law_title = law_entry.title,
        law_government_body = law_entry.govt_body,
        law_section = law_entry.section,
        law_citation = law_entry.citation,
        law_region = law_entry.region,
        law_enactment_day = law_entry.day,
        law_enactment_month = law_entry.month,
        law_enactment_year = law_entry.year,
        law_city = law_entry.city,
        law_state = law_entry.state,
        law_country = law_entry.country,
        law_description = law_entry.description,
        law_link = law_entry.link,
        document_status = "draft")

    if request.method == 'POST':
        if law_form.validate_on_submit():
            if "Save Law" in request.form.values():
                save_or_submit_doc(law_form, doc_type='law', submit="under review")

            if "Submit Law" in request.form.values():
                save_or_submit_doc(law_form, doc_type='law', submit="published")

            return view_all_drafts()

    return render_template('adtributor/edit_law_draft.html', law_form=law_form, c=contribution)


@admin.route('/contribution/video/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def contribution_video(id):
    contribution = Document.query.get(id)
    video_entry = Document.query.filter_by(id=id).first()
    video_form = VideoForm(
                    doc_type = "video",
                    video_title = video_entry.title,
                    director_first_name = video_entry.author_first_name,
                    director_last_name = video_entry.author_last_name,
                    video_post_source = video_entry.post_source,
                    video_publisher = video_entry.name,
                    video_publication_day = video_entry.day,
                    video_publication_month = video_entry.month,
                    video_publication_year = video_entry.year,
                    video_description = video_entry.description,
                    video_link = video_entry.link,
                    document_status = "draft")

    if request.method == 'POST':
        if video_form.validate_on_submit():
            if "Save Video" in request.form.values():
                save_or_submit_doc(video_form, doc_type='video', submit="under review")

            if "Submit Video" in request.form.values():
                save_or_submit_doc(video_form, doc_type='video', submit="published")

            return view_all_drafts()

    return render_template('adtributor/edit_video_draft.html', video_form=video_form, c=contribution)


@admin.route('/contribution/report/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def contribution_report(id):
    contribution = Document.query.get(id)
    report_entry = Document.query.filter_by(id=id).first()
    report_form = ReportForm(
                    doc_type = "report",
                    report_title = report_entry.title,
                    report_author_first_name = report_entry.author_first_name,
                    report_author_last_name = report_entry.author_last_name,
                    report_publisher_name = report_entry.name,
                    report_publication_day= report_entry.day,
                    report_publication_month = report_entry.month,
                    report_publication_year = report_entry.year,
                    report_description = report_entry.description,
                    report_link = report_entry.link,
                    document_status = 'draft')

    if request.method == 'POST':
        if report_form.validate_on_submit():
            if "Save Report" in request.form.values():
                save_or_submit_doc(video_form, doc_type='report', submit="under review")

            if "Submit Report" in request.form.values():
                save_or_submit_doc(video_form, doc_type='report', submit="published")

            return view_all_drafts()

    return render_template('adtributor/edit_report_draft.html', report_form=report_form, c=contribution)


@admin.route('/contribution/other/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def contribution_other(id):
    contribution = Document.query.get(id)
    other_entry = Document.query.filter_by(id=id).first()
    other_form = OtherForm(
                    doc_type = "other",
                    other_document_type = other_entry.other_type,
                    other_title = other_entry.title,
                    other_author_first_name = other_entry.author_first_name,
                    other_author_last_name = other_entry.author_last_name,
                    other_publication_day = other_entry.day,
                    other_publication_month = other_entry.month,
                    other_publication_year = other_entry.year,
                    other_description = other_entry.description,
                    other_link = other_entry.link,
                    document_status = "draft")

    if request.method == 'POST':
        if other_form.validate_on_submit():
            if "Save Other" in request.form.values():
                save_or_submit_doc(other_form, doc_type='other', submit="under review")

            if "Submit Other" in request.form.values():
                save_or_submit_doc(other_form, doc_type='other', submit="published")

            return view_all_drafts()

    return render_template('adtributor/edit_other_draft.html', other_form=other_form, c=contribution)


@admin.route('/from_suggestion/book/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def suggestion_book_draft(id):
    book_entry = Document.query.get(id)
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
                save_or_submit_doc(book_form, doc_type='book', submit='published')

            return review_suggestions()

    return render_template('adtributor/edit_book_draft.html', book_form=book_form, c=book_entry)


@admin.route('/from_suggestion/article/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def suggestion_article_draft(id):
    article_entry = Suggestion.query.get(id)
    article_form = ArticleForm(
        doc_type="article",
        article_title=article_entry.title,
        article_description=article_entry.description,
        article_link=article_entry.link,
        document_status="draft")

    if request.method == 'POST':
        if article_form.validate_on_submit():
            if "Save Article" in request.form.values():
                save_or_submit_doc(article_form, doc_type='article', submit='draft')

            if "Submit Article" in request.form.values():
                save_or_submit_doc(article_form, doc_type='article', submit='published')

            return review_suggestions()

    return render_template('adtributor/edit_article_draft.html', article_form=article_form, c=article_entry)


@admin.route('/from_suggestion/journal/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def suggestion_journal_draft(id):
    journal_entry = Suggestion.query.get(id)
    journal_form = JournalArticleForm(
        doc_type="journal",
        article_title=journal_entry.title,
        article_description=journal_entry.description,
        article_link=journal_entry.link,
        document_status="draft")

    if request.method == 'POST':
        if journal_form.validate_on_submit():
            if "Save Article" in request.form.values():
                save_or_submit_doc(journal_form, doc_type='journal', submit='draft')

            if "Submit Article" in request.form.values():
                save_or_submit_doc(journal_form, doc_type='journal', submit='published')

            return review_suggestions()

    return render_template('adtributor/edit_journal_draft.html', journal_form=journal_form, c=journal_entry)


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
                save_or_submit_doc(law_form, doc_type='law', submit='published')

            return review_suggestions()

    return render_template('adtributor/edit_law_draft.html', law_form=law_form, c=law_entry)


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
                save_or_submit_doc(video_form, doc_type='video', submit='draft')

            if "Submit Video" in request.form.values():
                save_or_submit_doc(video_form, doc_type='video', submit='published')

            return review_suggestions()

    return render_template('adtributor/edit_video_draft.html', video_form=video_form, c=video_entry)


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
                save_or_submit_doc(report_form, doc_type='report', submit='draft')

            if "Submit Report" in request.form.values():
                save_or_submit_doc(report_form, doc_type='report', submit='published')

            return review_suggestions()

    return render_template('adtributor/edit_report_draft.html', report_form=report_form, c=report_entry)


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
        document_status="draft")

    if request.method == 'POST':
        if other_form.validate_on_submit():
            if "Save Other" in request.form.values():
                save_or_submit_doc(other_form, doc_type='other', submit='draft')

            if "Submit Other" in request.form.values():
                save_or_submit_doc(other_form, doc_type='other', submit='published')

            return review_suggestions()

    return render_template('adtributor/edit_other_draft.html', other_form=other_form, c=other_entry)


@admin.route('sign-s3/')
@admin_required
@contributor.route('sign-s3/')
@contributor_required
@login_required
def sign_s3():
    # Load necessary information into the application
        S3_BUCKET = "h4i-test2"
        TARGET_FOLDER = 'json/'
        # Load required data from the request
        pre_file_name = request.args.get('file-name')
        file_name = ''.join(pre_file_name.split('.')[:-1]) +\
            str(time.time()).replace('.',  '-') + '.' +  \
            ''.join(pre_file_name.split('.')[-1:])
        file_type = request.args.get('file-type')

        # Initialise the S3 client
        s3 = boto3.client('s3', 'us-east-2')

        # Generate and return the presigned URL
        presigned_post = s3.generate_presigned_post(
        Bucket=S3_BUCKET,
        Key=TARGET_FOLDER + file_name,
        Fields={
            "acl": "public-read",
            "Content-Type": file_type
        },
        Conditions=[{
            "acl": "public-read"
        }, {
            "Content-Type": file_type
        }],
        ExpiresIn=60000)

        # Return the data to the client
        return json.dumps({
            'data':
            presigned_post,
            'url_upload':
            'https://%s.%s.amazonaws.com' % (S3_BUCKET, S3_REGION),
            'url':
            'https://%s.amazonaws.com/%s/json/%s' % (S3_REGION, S3_BUCKET,
                                                     file_name)
        })


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


@admin.route('/broken_link', methods=['GET', 'POST'])
@login_required
@admin_required
def view_broken_links():
    broken = Document.query.filter(Document.broken_link == True)
    return render_template('admin/review_broken.html', broken=broken)


def save_or_submit_doc(form, doc_type, submit):
    if doc_type == 'article':
        article_form = form
        article = Document(
            doc_type="article",
            title=article_form.article_title.data,
            author_first_name=article_form.article_author_first_name.data,
            author_last_name=article_form.article_author_last_name.data,
            posted_by=current_user.first_name + " " + current_user.last_name,
            last_edited_by=current_user.first_name + " " + current_user.last_name,
            name=article_form.article_publication.data,
            day=article_form.article_publication_day.data,
            month=article_form.article_publication_month.data,
            year=article_form.article_publication_year.data,
            description=article_form.article_description.data,
            link=article_form.article_link.data,
            document_status="draft" if not submit else "needs review",
            tf=Counter(article_form.article_description.data))
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
            volume=book_form.book_volume.data,
            edition=book_form.book_edition.data,
            series=book_form.book_series.data,
            author_first_name=book_form.book_author_first_name.data,
            author_last_name=book_form.book_author_last_name.data,
            posted_by=current_user.first_name + " " + current_user.last_name,
            last_edited_by=current_user.first_name + " " + current_user.last_name,
            name=book_form.book_publisher_name.data,
            month=book_form.book_publication_month.data,
            year=book_form.book_publication_year.data,
            description=book_form.book_description.data,
            link=book_form.book_link.data,
            document_status="draft" if not submit else "needs review",
            tf=Counter(book_form.book_description.data))
        db.session.add(book)
        db.session.commit()
        flash(
            'Book \"{}\" successfully saved'.format(
                book_form.book_title.data), 'form-success')
    elif doc_type == 'journal':
        journal_form = form
        article = Document(
            doc_type="journal",
            title=journal_form.article_title.data,
            author_first_name=journal_form.article_author_first_name.data,
            author_last_name=journal_form.article_author_last_name.data,
            posted_by=current_user.first_name + " " + current_user.last_name,
            last_edited_by=current_user.first_name + " " + current_user.last_name,
            name=journal_form.publisher_name.data,
            volume=journal_form.volume.data,
            page_start=journal_form.start_page.data,
            page_end=journal_form.end_page.data,
            day=journal_form.article_publication_day.data,
            month=journal_form.article_publication_month.data,
            year=journal_form.article_publication_year.data,
            description=journal_form.article_description.data,
            link=journal_form.article_link.data,
            document_status="draft" if not submit else "needs review",
            tf=Counter(journal_form.article_description.data))

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
            posted_by=current_user.first_name + " " + current_user.last_name,
            last_edited_by=current_user.first_name + " " + current_user.last_name,
            title=law_form.law_title.data,
            description=law_form.law_description.data,
            city=law_form.law_city.data,
            state=law_form.law_state.data,
            country=law_form.law_country.data,
            link=law_form.law_link.data,
            govt_body=law_form.law_government_body.data,
            section=law_form.law_section.data,
            document_status="draft" if not submit else "needs review",
            tf=Counter(law_form.law_description.data))

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
            posted_by=current_user.first_name + " " + current_user.last_name,
            last_edited_by=current_user.first_name + " " + current_user.last_name,
            name=video_form.video_publisher.data,
            day=video_form.video_publication_day.data,
            month=video_form.video_publication_month,
            year=video_form.video_publication_year.data,
            description=video_form.video_description.data,
            link=video_form.video_link.data,
            document_status="draft" if not submit else "needs review",
            tf=Counter(video_form.video_description.data))

        db.session.add(video)
        db.session.commit()
        flash(
            'Video \"{}\" successfully saved'.format(
                video_form.video_title.data), 'form-success')

    elif doc_type == 'report':
        report_form = form
        report = Document(
            doc_type="report",
            title=report_form.report_title.data,
            author_first_name=report_form.report_author_first_name.data,
            author_last_name=report_form.report_author_last_name.data,
            posted_by=current_user.first_name + " " + current_user.last_name,
            name=report_form.report_publisher.data,
            day=report_form.report_publication_day.data,
            month=report_form.report_publication_month.data,
            year=report_form.report_publication_year.data,
            description=report_form.report_description.data,
            link=report_form.report_link.data,
            document_status="draft" if not submit else "needs review",
            tf=(report_form.report_description.data))

        db.session.add(report)
        db.session.commit()
        flash(
            'Report \"{}\" successfully saved'.format(
                report_form.report_title.data), 'form-success')

    elif doc_type == 'other':
        other_form = form
        other = Document(
            doc_type="other",
            title=other_form.other_title.data,
            author_first_name=other_form.other_author_first_name.data,
            author_last_name=other_form.other_author_last_name.data,
            posted_by=current_user.first_name + " " + current_user.last_name,
            last_edited_by=current_user.first_name + " " + current_user.last_name,
            day=other_form.other_publication_day.data,
            month=other_form.other_publication_month.data,
            year=other_form.other_publication_year.data,
            description=other_form.other_description.data,
            link=other_form.other_link.data,
            other_type=other_form.other_document_type.data,
            document_status="draft" if not submit else "needs review",
            tf=Counter(other_form.other_description.data))

        db.session.add(other)
        db.session.commit()
        flash(
            'Other \"{}\" successfully saved'.format(
                other_form.other_title.data), 'form-success')
