from .. import db
from app.models import Document
from sqlalchemy import Table, Integer, ForeignKey


class Tag(db.Model):
    __tablename__ = 'tag'
    id = db.Column(db.Integer, primary_key=True)
    tag = db.Column(db.String())

    @staticmethod
    def generate_fake(count=10, **kwargs):
        from sqlalchemy.exc import IntegrityError
        from faker import Faker

        fake = Faker()
        tags = []
        for i in range(count):
            item = Tag(
                tag=fake.word()
            )
            db.session.add(item)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
        return tags

    def __repr__(self):
        s = '<Id: {} \n'.format(self.id)
        s += 'Tag: {}>'.format(self.tag)
        return s
