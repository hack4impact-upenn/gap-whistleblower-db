from .. import db, login_manager
from . import User, Idf, MutableDict
import random
from faker import Faker
from sqlalchemy import Column, Integer, DateTime, PickleType, String, ForeignKey
import datetime
from collections import Counter
import os
import nltk
nltk.data.path.append(os.environ.get('NLTK_DATA'))
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from sqlalchemy.dialects.postgresql import ARRAY

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
    posted_by = db.Column(db.String(1000))
    last_edited_by = db.Column(db.String(1000))
    title = db.Column(db.String(1000))
    description = db.Column(db.Text())
    link = db.Column(db.String())
    file = db.Column(db.String())
    citation = db.Column(db.String())
    document_status = db.Column(db.String(), default='draft')

    #Specific to Book
    volume = db.Column(db.String(10))
    edition = db.Column(db.String(10))
    series = db.Column(db.String(500))

    editor_first_name = db.Column(db.String(10000))
    editor_last_name = db.Column(db.String(10000))

    #Specific to Book/Article
    author_first_name = db.Column(db.String(10000))
    author_last_name = db.Column(db.String(10000))

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

    tf = db.Column(MutableDict.as_mutable(PickleType))

    broken_link = db.Column(db.Boolean)

    @staticmethod
    def generate_fake(count=1000, **kwargs):
        fake = Faker()
        for i in range(count):
            name = fake.name()
            text = fake.text(max_nb_chars=100)
            stop_words = set(stopwords.words('english'))
            word_tokens = word_tokenize(text)
            filtered_query = [w for w in word_tokens if not w in stop_words]
            document = Document(
                doc_type = "book",
                day =  random.randint(1, 28),
                month = fake.month_name(),
                year = fake.year(),
                posted_by = name,
                last_edited_by = name,
                title = fake.text(max_nb_chars=50),
                description = text,
                link = 'http://' + fake.domain_name(),
                volume = random.randint(1, 10),
                edition = random.randint(1, 5),
                series = fake.text(max_nb_chars=50),
                author_first_name = fake.first_name(),
                author_last_name = fake.last_name(),
                editor_first_name = fake.first_name(),
                editor_last_name = fake.last_name(),
                name = fake.company(),
                document_status = random.choice(["draft", "published"]),
                tf = Counter(filtered_query))

            db.session.add(document)

            for key in Counter(filtered_query):
                entry = Idf.query.get(key)
                if entry is None:
                    idf = Idf(
                        term = key,
                        docs = [document.id]
                    )
                    db.session.add(idf)
                else:
                    entry.docs.append(document.id)
        print('one')
        for i in range(count):
            name = fake.name()
            text = fake.text(max_nb_chars=100)
            stop_words = set(stopwords.words('english'))
            word_tokens = word_tokenize(text)
            filtered_query = [w for w in word_tokens if not w in stop_words]
            article = Document(
                doc_type = "news_article",
                day =  random.randint(1, 28),
                month = fake.month_name(),
                year = fake.year(),
                name = fake.sentence(),
                posted_by = name,
                last_edited_by = name,
                title = fake.text(max_nb_chars=50),
                description = text,
                link = 'http://' + fake.domain_name(),
                author_first_name = fake.first_name(),
                author_last_name = fake.last_name(),
                document_status = random.choice(["draft", "published"]),
                tf = Counter(filtered_query))

            db.session.add(article)

            for key in Counter(filtered_query):
                entry = Idf.query.get(key)
                if entry is None:
                    idf = Idf(
                        term = key,
                        docs = [article.id]
                    )
                    db.session.add(idf)
                else:
                    entry.docs.append(article.id)
        print('two')
        for i in range(count):
            name = fake.name()
            text = fake.text(max_nb_chars=100)
            stop_words = set(stopwords.words('english'))
            word_tokens = word_tokenize(text)
            filtered_query = [w for w in word_tokens if not w in stop_words]
            journal = Document(
                doc_type = "journal_article",
                day =  random.randint(1, 28),
                month = fake.month_name(),
                year = fake.year(),
                name = fake.sentence(),
                volume = random.randint(1, 10),
                page_start = random.randint(1,10),
                page_end = random.randint(11,20),
                posted_by = name,
                last_edited_by = name,
                title = fake.text(max_nb_chars=50),
                description = text,
                link = 'http://' + fake.domain_name(),
                author_first_name = fake.first_name(),
                author_last_name = fake.last_name(),
                document_status = random.choice(["draft", "published"]),
                tf = Counter(filtered_query))

            db.session.add(journal)

            for key in Counter(filtered_query):
                entry = Idf.query.get(key)
                if entry is None:
                    idf = Idf(
                        term = key,
                        docs = [journal.id]
                    )
                    db.session.add(idf)
                else:
                    entry.docs.append(journal.id)
        print('three')
        for i in range(count):
            name = fake.name()
            doc_type = random.choice(["film", "audio", "photograph"])
            text = fake.text(max_nb_chars=100)
            stop_words = set(stopwords.words('english'))
            word_tokens = word_tokenize(text)
            filtered_query = [w for w in word_tokens if not w in stop_words]
            other = Document(
                doc_type = "other",
                day =  random.randint(1, 28),
                month = fake.month_name(),
                year = fake.year(),
                posted_by = name,
                last_edited_by = name,
                title = fake.text(max_nb_chars=50),
                description = text,
                link = 'http://' + fake.domain_name(),
                author_first_name = fake.first_name(),
                author_last_name = fake.last_name(),
                other_type= doc_type,
                document_status = random.choice(["draft", "published"]),
                tf = Counter(filtered_query))

            db.session.add(other)

            for key in Counter(filtered_query):
                entry = Idf.query.get(key)
                if entry is None:
                    idf = Idf(
                        term = key,
                        docs = [other.id]
                    )
                    db.session.add(idf)
                else:
                    entry.docs.append(other.id)
        print('four')
        for i in range(count):
            name = fake.name()
            body = random.choice(["105th Congress", "106th Congress", "107th Congress"])
            text = fake.text(max_nb_chars=100)
            stop_words = set(stopwords.words('english'))
            word_tokens = word_tokenize(text)
            filtered_query = [w for w in word_tokens if not w in stop_words]
            law = Document(
                doc_type = "law",
                day =  random.randint(1, 28),
                month = fake.month_name(),
                year = fake.year(),
                citation = fake.sentence(),
                region = fake.country(),
                posted_by = name,
                last_edited_by = name,
                title = fake.text(max_nb_chars=50),
                description = text,
                city = fake.city(),
                state = fake.state(),
                country = "United States",
                link = 'http://' + fake.domain_name(),
                govt_body = body,
                section = random.randint(1, 100),
                document_status = random.choice(["draft", "published"]),
                tf = Counter(filtered_query))

            db.session.add(law)

            for key in Counter(filtered_query):
                entry = Idf.query.get(key)
                if entry is None:
                    idf = Idf(
                        term = key,
                        docs = [law.id]
                    )
                    db.session.add(idf)
                else:
                    entry.docs.append(law.id)
        print('five')
        for i in range(count):
            name = fake.name()
            text = fake.text(max_nb_chars=100)
            stop_words = set(stopwords.words('english'))
            word_tokens = word_tokenize(text)
            filtered_query = [w for w in word_tokens if not w in stop_words]
            video = Document(
                doc_type = "video",
                day =  random.randint(1, 28),
                month = fake.month_name(),
                year = fake.year(),
                name = fake.sentence(),
                post_source = fake.name(),
                posted_by = name,
                last_edited_by = name,
                title = fake.text(max_nb_chars=50),
                description = text,
                link = 'http://' + fake.domain_name(),
                author_first_name = fake.first_name(),
                author_last_name = fake.last_name(),
                document_status = random.choice(["draft", "published"]),
                tf = Counter(filtered_query))

            db.session.add(video)

            for key in Counter(filtered_query):
                entry = Idf.query.get(key)
                if entry is None:
                    idf = Idf(
                        term = key,
                        docs = [video.id]
                    )
                    db.session.add(idf)
                else:
                    entry.docs.append(video.id)

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
