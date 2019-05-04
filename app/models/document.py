from .. import db, login_manager
from . import User, Idf, MutableDict
import random
from faker import Faker
from sqlalchemy import Column, Integer, DateTime, PickleType, String, ForeignKey
from sqlalchemy.orm import composite
import datetime
from collections import Counter
import os
import nltk
nltk.data.path.append(os.environ.get('NLTK_DATA'))
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method
from nltk.stem.snowball import SnowballStemmer

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
    name = db.Column(db.String(1000))
    city = db.Column(db.String(500))
    state = db.Column(db.String(500))
    country = db.Column(db.String(500))

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

    @hybrid_property
    def corpus(self):
        corpus = []
        fields = self.__dict__
        for key, value in fields.items():
            if key not in ['tf', 'page_start', 'id', 'day', 'posted_date',
            'last_edited_date', 'posted_by', 'last_edited_by', 'edition',
            'broken_link', 'volume', 'file', 'document_status', '_sa_instance_state',
            'link', 'author_first_name', 'author_last_name'] and value != None:
                corpus.append(str(value))
            elif key in ['author_first_name', 'author_last_name'] and value != None:
                authors = value.split(',')
                for a in authors:
                    corpus.append(a)
        return ' '.join(corpus)

    @hybrid_property
    def date(self):
        if self.year != "":
            if self.month != "":
                if self.day != "":
                    return self.month + " " + str(self.day) + ", " + str(self.year)
                return self.month + " " + str(self.year)
            return str(self.year)
        return ""

    @hybrid_method
    def is_after(self, start_date):
        month_dict = {'January': 1, 'February': 2, 'March': 3, 'April': 4,
        'May': 5, 'June': 6, 'July': 7, 'August': 8, 'September': 9,
        'October': 10, 'November': 11, 'December': 12}
        now_tuple = (self.year, month_dict.get(self.month), self.day)
        return now_tuple >= start_date

    @hybrid_method
    def is_before(self, end_date):
        month_dict = {'January': 1, 'February': 2, 'March': 3, 'April': 4,
        'May': 5, 'June': 6, 'July': 7, 'August': 8, 'September': 9,
        'October': 10, 'November': 11, 'December': 12}
        now_tuple = (self.year, month_dict.get(self.month), self.day)
        return now_tuple <= end_date


    @staticmethod
    def generate_fake(count=1000, **kwargs):
        stemmer = SnowballStemmer("english", ignore_stopwords=True)
        stop_words = set(stopwords.words('english'))
        fake = Faker()
        for i in range(count):
            name = fake.name()
            text = fake.text(max_nb_chars=100)
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
                document_status = random.choice(["draft", "published"]))
            db.session.add(document)
            word_tokens = word_tokenize(document.corpus)
            filtered_query = [stemmer.stem(w).lower() for w in word_tokens if not w in stop_words]
            document.tf = Counter(filtered_query)

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
                document_status = random.choice(["draft", "published"]))

            db.session.add(article)
            word_tokens = word_tokenize(article.corpus)
            filtered_query = [stemmer.stem(w).lower() for w in word_tokens if not w in stop_words]
            article.tf = Counter(filtered_query)

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
                document_status = random.choice(["draft", "published"]))

            db.session.add(journal)
            word_tokens = word_tokenize(journal.corpus)
            filtered_query = [stemmer.stem(w).lower() for w in word_tokens if not w in stop_words]
            journal.tf = Counter(filtered_query)

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
                document_status = random.choice(["draft", "published"]))

            db.session.add(other)
            word_tokens = word_tokenize(other.corpus)
            filtered_query = [stemmer.stem(w).lower() for w in word_tokens if not w in stop_words]
            other.tf = Counter(filtered_query)

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
            word_tokens = word_tokenize(law.corpus)
            filtered_query = [stemmer.stem(w).lower() for w in word_tokens if not w in stop_words]
            law.tf = Counter(filtered_query)

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
                document_status = random.choice(["draft", "published"]))

            db.session.add(video)
            word_tokens = word_tokenize(video.corpus)
            filtered_query = [stemmer.stem(w).lower() for w in word_tokens if not w in stop_words]
            video.tf = Counter(filtered_query)

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
