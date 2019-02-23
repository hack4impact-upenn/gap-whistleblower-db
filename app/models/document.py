from .. import db, login_manager
from . import User
import random
from faker import Faker


class Document(db.Model):
    __tablename__ = 'document'
    id = db.Column(db.Integer, primary_key = True)
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
            s = '<Document \n'
            s += 'Type: {}\n'.format(self.doc_type)
            s += 'Title: {}\n'.format(self.title)
            s += 'Author: {}, {}\n'.format(self.author)
            s += 'Description: {}\n'.format(self.description)
            s += 'Publication'.format(self.publication)
            s += 'Publication Date: {}\n'.format(self.publication_date)
            s += 'Posted Date: {}\n'.format(self.posted_date)
            s += 'Last Edited Date: {}\n'.format(self.last_edited_date)
            s += 'Posted By: {}\n'.format(self.posted_by)
            s += 'Last Edited By: {}\n'.format(self.last_edited_by)
            s += 'Country {}\n'.format(self.country)
            s += 'State: {}\n'.format(self.state)
            s += 'Link: {}\n'.format(self.link) + '>'
            return s


