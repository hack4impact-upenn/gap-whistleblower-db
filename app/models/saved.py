from .. import db
import random
from faker import Faker
from . import User, Document
from sqlalchemy import Column, Integer, DateTime
from sqlalchemy.exc import IntegrityError
import datetime


class Saved(db.Model):
    __tablename__ = 'saved'
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    doc_id = db.Column(db.Integer, db.ForeignKey('document.id'))
    saved_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    @staticmethod
    def generate_fake(**kwargs):
        documents = Document.query.all()
        users = User.query.all()

        fake = Faker()
        saved_resources = []
        for user in users:
            for document in documents:
                num = fake.random_int(min=0, max=9999)
                if (num < 2000):
                    item = Saved(
                        user_id=user.id,
                        doc_id=document.id,
                        saved_date=fake.date_time(tzinfo=None)
                    )
                    saved_resources.append(item)
                    db.session.add(item)
                    try:
                        db.session.commit()
                    except IntegrityError:
                        db.session.rollback()
        return saved_resources

    def __repr__(self):
        return '<Saved Resource: User ID={}, Resource ID={}, Date={}'.format(
            self.user_id, self.doc_id, self.saved_date
        )
