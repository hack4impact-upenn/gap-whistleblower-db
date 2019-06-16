from .. import db
from app.models import Document, Tag
from sqlalchemy import Integer, ForeignKey


class Tagged(db.Model):
    __tablename__ = 'tagged'
    tag_id = db.Column(db.Integer, ForeignKey('tag.id'), primary_key=True)
    document_id = db.Column(db.Integer, ForeignKey('document.id'), primary_key=True)
    tag_name = db.Column(db.String(1000))
    tag = db.relationship("Tag", backref="documents")
    document = db.relationship("Document", backref="tags")

    @staticmethod
    def generate_fake(**kwargs):
        from sqlalchemy.exc import IntegrityError
        from faker import Faker

        documents = Document.query.all()
        tags = Tag.query.all()

        fake = Faker()
        tagged_resources = []
        for tag in tags:
            for document in documents:
                num = fake.random_int(min=0, max=9999)
                if (num < 2000):
                    item = Tagged(
                        tag_id=tag.id,
                        document_id=document.id,
                        tag_name=tag.tag
                    )
                    tagged_resources.append(item)
                    db.session.add(item)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
        return tagged_resources
