from .. import db, login_manager
from . import User
import random
from faker import Faker
from sqlalchemy import Column, Integer, DateTime, PickleType
import datetime
from collections import Counter

class Document(db.Model):
    __tablename__ = 'document'
    id = db.Column(db.Integer, primary_key=True)
    #These files are generic
    doc_type = db.Column(db.String(200))
    day = db.Column(db.Integer()) #Publication/case/ennactment of law day
    month = db.Column(db.String(20)) #Publication/case/ennactment of law month
    year = db.Column(db.Integer()) #Publication/case/enactment of law year
    posted_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    last_edited_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    posted_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    last_edited_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    title = db.Column(db.String(10000))
    description = db.Column(db.Text())
    link = db.Column(db.String())
    file = db.Column(db.String())
    citation = db.Column(db.String())
    document_status = db.Column(db.String(), default='draft')

    #Specific to Book
    volume = db.Column(db.String(10))
    edition = db.Column(db.String(10))
    series = db.Column(db.String(500))
    ISBN = db.Column(db.String(30))

    #Specific to Book/Article
    author_first_name = db.Column(db.String(100))
    author_last_name = db.Column(db.String(100))

    #Specific to Journal Article
    page_start = db.Column(db.Integer())
    page_end = db.Column(db.Integer())

    #Specific to Book
    name = db.Column(db.String(1000)) #Publisher or court name
    city = db.Column(db.String(500)) #Publisher or court city
    state = db.Column(db.String(500)) #Publisher or court state
    country = db.Column(db.String(500)) #Publisher or court country

    #Specific to Law
    govt_body = db.Column(db.String(1000))
    section = db.Column(db.String(1000))
    region = db.Column(db.String(1000))

    #Specific to other
    other_type = db.Column(db.String(1000)) #Doc type (if other selected)

    #Specific to video
    post_source = db.Column(db.String(1000))

    tf = db.Column(db.PickleType())

    @staticmethod
    def generate_fake(count=10, **kwargs):
        fake = Faker()
        for i in range(count):
            ISBN = fake.numerify(text="###") + "-" + fake.numerify(text="#") + "-" + fake.numerify(text="##") + "-" + fake.numerify(text = "######") + "-" + fake.numerify(text="#")
            user_id = random.randint(2,11)
            text = fake.text(max_nb_chars=500)
            document = Document(
                doc_type = "book",
                day =  random.randint(1, 28),
                month = fake.month_name(),
                year = fake.year(),
                posted_by = user_id,
                last_edited_by = user_id,
                title = fake.text(max_nb_chars=50),
                description = text,
                link = fake.domain_name(),
                volume = random.randint(1, 10),
                edition = random.randint(1, 5),
                series = fake.text(max_nb_chars=50),
                ISBN = ISBN,
                author_first_name = fake.first_name(),
                author_last_name = fake.last_name(),
                name = fake.company(),
                city = fake.city(),
                state = fake.state(),
                country = "United States",
                document_status = random.choice(["draft", "needs review", "under review","published"],
                tf = Counter(text))
            )
            db.session.add(document)
        for i in range(count):
            user_id = random.randint(2,11)
            text = fake.text(max_nb_chars=500)
            article = Document(
                doc_type = "news article",
                day =  random.randint(1, 28),
                month = fake.month_name(),
                year = fake.year(),
                name = fake.sentence(),
                posted_by = user_id,
                last_edited_by = user_id,
                title = fake.text(max_nb_chars=50),
                description = text,
                link = fake.domain_name(),
                author_first_name = fake.first_name(),
                author_last_name = fake.last_name(),
                document_status = random.choice(["draft", "needs review", "under review","published"],
                tf = Counter(text))
            )
            db.session.add(article)
        for i in range(count):
            user_id = random.randint(2,11)
            text = fake.text(max_nb_chars=500)
            journal = Document(
                doc_type = "journal article",
                day =  random.randint(1, 28),
                month = fake.month_name(),
                year = fake.year(),
                name = fake.sentence(),
                volume = random.randint(1, 10),
                page_start = random.randint(1,10),
                page_end = random.randint(11,20),
                posted_by = user_id,
                last_edited_by = user_id,
                title = fake.text(max_nb_chars=50),
                description = text,
                link = fake.domain_name(),
                author_first_name = fake.first_name(),
                author_last_name = fake.last_name(),
                document_status = random.choice(["draft", "needs review", "under review","published"],
                tf = Counter(text))
            )
            db.session.add(journal)
        for i in range(count):
            user_id = random.randint(2,11)
            doc_type = random.choice(["film", "audio", "photograph"])
            text = fake.text(max_nb_chars=500)
            other = Document(
                doc_type = "other",
                day =  random.randint(1, 28),
                month = fake.month_name(),
                year = fake.year(),
                posted_by = user_id,
                last_edited_by = user_id,
                title = fake.text(max_nb_chars=50),
                description = text,
                link = fake.domain_name(),
                author_first_name = fake.first_name(),
                author_last_name = fake.last_name(),
                other_type= doc_type,
                document_status = random.choice(["draft", "needs review", "under review","published"],
                tf = Counter(text))
            )
            db.session.add(other)
        for i in range(count):
            user_id = random.randint(2,11)
            body = random.choice(["105th Congress", "106th Congress", "107th Congress"])
            text = fake.text(max_nb_chars=500)
            law = Document(
                doc_type = "law",
                day =  random.randint(1, 28),
                month = fake.month_name(),
                year = fake.year(),
                citation = fake.sentence(),
                region = fake.country(),
                posted_by = user_id,
                last_edited_by = user_id,
                title = fake.text(max_nb_chars=50),
                description = text,
                city = fake.city(),
                state = fake.state(),
                country = "United States",
                link = fake.domain_name(),
                govt_body = body,
                section = random.randint(1, 100),
                document_status = random.choice(["draft", "needs review", "under review","published"],
                tf = Counter(text))
            )
            db.session.add(law)
        for i in range(count):
            user_id = random.randint(2,11)
            text = fake.text(max_nb_chars=500)
            video = Document(
                doc_type = "video",
                day =  random.randint(1, 28),
                month = fake.month_name(),
                year = fake.year(),
                name = fake.sentence(),
                post_source = fake.name(),
                posted_by = user_id,
                last_edited_by = user_id,
                title = fake.text(max_nb_chars=50),
                description = text,
                link = fake.domain_name(),
                author_first_name = fake.first_name(),
                author_last_name = fake.last_name(),
                document_status = random.choice(["draft", "needs review", "under review","published"],
                tf = Counter(text))
            )
            db.session.add(video)
        db.session.commit()

    def __repr__(self):
        return ('<Document \n'
                f'Type: {self.doc_type}\n'
                f'Day: {self.day}\n'
                f'Month: {self.month}\n'
                f'Year: {self.year}\n'
                f'Posted Date: {self.posted_date}\n'
                f'Last Edited Date: {self.last_edited_date}\n'
                f'Posted By: {self.posted_by}\n'
                f'Last Edited By: {self.last_edited_by}\n'
                f'Title: {self.title}\n'
                f'Description: {self.description}\n'
                f'Link: {self.link}\n>'
                f'File: {self.file}\n>'
                f'Citation: {self.citation}\n>'
                f'Volume: {self.volume}\n>'
                f'Edition: {self.edition}\n>'
                f'Series: {self.series}\n>'
                f'ISBN: {self.ISBN}\n>'
                f'Author First Name: {self.author_first_name}\n>'
                f'Author Last Name: {self.author_last_name}\n>'
                f'Name: {self.name}\n>'
                f'City: {self.city}\n>'
                f'State: {self.state}\n>'
                f'Country: {self.country}\n>'
                f'Affiliated Government Body: {self.govt_body}\n>'
                f'Section: {self.section}\n>'
                f'Type (if other): {self.other_type}\n>'
                f'Document Status: {self.document_status}\n>')

    def __str__(self):
        return self.__repr__()
