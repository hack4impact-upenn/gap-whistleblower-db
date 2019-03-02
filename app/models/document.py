from .. import db, login_manager
from . import User
import random
from faker import Faker
import flask_whooshalchemyplus

class Document(db.Model):
    __tablename__ = 'document'
    __searchable__ = ['title', 'author', 'description', 'publication']

    id = db.Column(db.Integer, primary_key=True)
    doc_type = db.Column(db.String(200))
    title = db.Column(db.String(10000))
    author = db.Column(db.String(1000))
    description = db.Column(db.Text())
    publication = db.Column(db.String(10000))
    publication_date = db.Column(db.Date())
    posted_date = db.Column(db.Date())
    last_edited_date = db.Column(db.Date())
    posted_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    last_edited_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    country = db.Column(db.String(1000))
    state = db.Column(db.String(1000))
    link = db.Column(db.String())

    @staticmethod
    def generate_fake(count=10, **kwargs):
        fake = Faker()
        for i in range(count):
            doc_type = random.choice(["book", "article", "research paper", "law", 
            "court case", "other"])
            document = Document(
                doc_type = doc_type,
                title = fake.text(max_nb_chars=200),
                author = fake.name(),
                description = fake.text(max_nb_chars=1000),
                publication = fake.text(max_nb_chars=200),
                publication_date = fake.date_time(tzinfo=None),
                posted_date = fake.date_time(tzinfo=None),
                last_edited_date = fake.date_time(tzinfo=None),
                posted_by = fake.name(),
                last_edited_by = fake.name(),
                country = fake.country(),
                state = fake.state(),
                link = fake.domain_name())
            db.session.add(document)
            db.session.commit()

    def __repr__(self):
        return ('<Document \n'
                f'Type: {self.doc_type}\n'
                f'Title: {self.title}\n'
                f'Author: {self.author}\n'
                f'Description: {self.description}\n'
                f'Publication: {self.publication}\n'
                f'Publication Date: {self.publication_date}\n'
                f'Posted Date: {self.posted_date}\n'
                f'Last Edited Date: {self.last_edited_date}\n'
                f'Posted By: {self.posted_by}\n'
                f'Last Edited By: {self.last_edited_by}\n'
                f'Country {self.country}\n'
                f'State: {self.state}\n'
                f'Link: {self.link}\n>')
