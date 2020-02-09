from .. import db
from . import Idf, MutableDict
import random
from faker import Faker
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method
from nltk.stem.snowball import SnowballStemmer
from sqlalchemy import PickleType
import datetime
from collections import Counter
import os
import nltk
nltk.data.path.append(os.environ.get('NLTK_DATA'))


class Document(db.Model):
    __tablename__ = 'document'
    id = db.Column(db.Integer, primary_key=True)
    # These files are generic
    doc_type = db.Column(db.String(200))
    day = db.Column(db.Integer())  # Publication/case/enactment of law day
    month = db.Column(db.String(20))  # Publication/case/enactment of law month
    year = db.Column(db.Integer())  # Publication/case/enactment of law year
    posted_date = db.Column(
        db.String(200),
        default=datetime.datetime.utcnow().strftime("%a %b %d %H:%M:%S %Z %Y")
    )
    last_edited_date = db.Column(
        db.String(200),
        default=datetime.datetime.utcnow().strftime("%a %b %d %H:%M:%S %Z %Y")
    )
    posted_by = db.Column(db.String(1000))
    last_edited_by = db.Column(db.String(1000))
    title = db.Column(db.String(1000))
    description = db.Column(db.Text())
    link = db.Column(db.String())
    file = db.Column(db.String())
    citation = db.Column(db.String())
    document_status = db.Column(db.String(), default='draft')

    # Specific to Book
    volume = db.Column(db.String(100))
    edition = db.Column(db.String(100))
    series = db.Column(db.String(500))
    publisher = db.Column(db.String(1000))

    editor_first_name = db.Column(db.String(1000))
    editor_last_name = db.Column(db.String(1000))

    # Specific to Book/Article
    author_first_name = db.Column(db.String(1000))
    author_last_name = db.Column(db.String(1000))

    # Specific to Journal Article
    page_start = db.Column(db.String(20))
    page_end = db.Column(db.String(20))
    issue = db.Column(db.String(100))

    # Specific to Law
    govt_body = db.Column(db.String(1000))
    section = db.Column(db.String(1000))
    region = db.Column(db.String(1000))
    country = db.Column(db.String(1000))

    # Specific to other
    other_type = db.Column(db.String(1000))  # Doc type (if other selected)

    # Specific to video
    source = db.Column(db.String(1000))
    studio = db.Column(db.String(1000))

    tf = db.Column(MutableDict.as_mutable(PickleType))

    broken_link = db.Column(db.Integer())

    @hybrid_property
    def corpus(self):
        corpus = []
        fields = self.__dict__
        for key, value in fields.items():
            if key not in [
                'tf', 'page_start', 'id', 'day', 'posted_date',
                'last_edited_date', 'posted_by', 'last_edited_by', 'edition',
                'broken_link', 'volume', 'file', 'document_status',
                '_sa_instance_state', 'link', 'author_first_name',
                'author_last_name', 'tags', 'doc_type', 'editor_first_name',
                'editor_last_name'
            ] and value is not None:
                corpus.append(str(value))
            elif key in [
                'author_first_name',
                'author_last_name'
            ] and value is not None:
                authors = value.split(',')
                for a in authors:
                    corpus.append(a)
            elif key in [
                'editor_first_name',
                'editor_last_name'
            ] and value is not None:
                editors = value.split(',')
                for e in editors:
                    corpus.append(e)
            elif key == 'doc_type':
                type = value.split('_')
                for t in type:
                    corpus.append(t)
        return ' '.join(corpus)

    @hybrid_property
    def date(self):
        if self.year != "":
            if self.month != "":
                if self.day != "":
                    return self.month + " "
                    + str(self.day) + ", "
                    + str(self.year)
                return self.month + " " + str(self.year)
            return str(self.year)
        return ""

    @hybrid_method
    def is_after(self, start_date):
        month_dict = {
            'January': 1, 'February': 2, 'March': 3, 'April': 4,
            'May': 5, 'June': 6, 'July': 7, 'August': 8, 'September': 9,
            'October': 10, 'November': 11, 'December': 12
        }
        now_tuple = (self.year, month_dict.get(self.month), self.day)
        return now_tuple >= start_date

    @hybrid_method
    def is_before(self, end_date):
        month_dict = {
            'January': 1, 'February': 2, 'March': 3, 'April': 4,
            'May': 5, 'June': 6, 'July': 7, 'August': 8, 'September': 9,
            'October': 10, 'November': 11, 'December': 12
        }
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
                doc_type="book",
                day=random.randint(1, 28),
                month=fake.month_name(),
                year=fake.year(),
                posted_by=name,
                last_edited_by=name,
                title=fake.text(max_nb_chars=50),
                description=text,
                link='http://' + fake.domain_name(),
                volume=random.randint(1, 10),
                edition=random.randint(1, 5),
                series=fake.text(max_nb_chars=50),
                author_first_name=fake.first_name(),
                author_last_name=fake.last_name(),
                editor_first_name=fake.first_name(),
                editor_last_name=fake.last_name(),
                name=fake.company(),
                document_status=random.choice(["draft", "published"]))
            db.session.add(document)
            word_tokens = word_tokenize(document.corpus)
            filtered_query = [
                stemmer.stem(w).lower() for w in word_tokens
                if w not in stop_words
            ]
            document.tf = Counter(filtered_query)

            for key in Counter(filtered_query):
                entry = Idf.query.get(key)
                if entry is None:
                    idf = Idf(
                        term=key,
                        docs=[document.id]
                    )
                    db.session.add(idf)
                else:
                    entry.docs.append(document.id)
        for i in range(count):
            name = fake.name()
            text = fake.text(max_nb_chars=100)
            article = Document(
                doc_type="news_article",
                day=random.randint(1, 28),
                month=fake.month_name(),
                year=fake.year(),
                name=fake.sentence(),
                posted_by=name,
                last_edited_by=name,
                title=fake.text(max_nb_chars=50),
                description=text,
                link='http://' + fake.domain_name(),
                author_first_name=fake.first_name(),
                author_last_name=fake.last_name(),
                document_status=random.choice(["draft", "published"]))

            db.session.add(article)
            word_tokens = word_tokenize(article.corpus)
            filtered_query = [
                stemmer.stem(w).lower()
                for w in word_tokens if w not in stop_words
            ]
            article.tf = Counter(filtered_query)

            for key in Counter(filtered_query):
                entry = Idf.query.get(key)
                if entry is None:
                    idf = Idf(
                        term=key,
                        docs=[article.id]
                    )
                    db.session.add(idf)
                else:
                    entry.docs.append(article.id)
        for i in range(count):
            name = fake.name()
            text = fake.text(max_nb_chars=100)
            journal = Document(
                doc_type="journal_article",
                day=random.randint(1, 28),
                month=fake.month_name(),
                year=fake.year(),
                name=fake.sentence(),
                volume=random.randint(1, 10),
                page_start=random.randint(1, 10),
                page_end=random.randint(11, 20),
                posted_by=name,
                last_edited_by=name,
                title=fake.text(max_nb_chars=50),
                description=text,
                link='http://' + fake.domain_name(),
                author_first_name=fake.first_name(),
                author_last_name=fake.last_name(),
                document_status=random.choice(["draft", "published"]))

            db.session.add(journal)
            word_tokens = word_tokenize(journal.corpus)
            filtered_query = [
                stemmer.stem(w).lower()
                for w in word_tokens
                if w not in stop_words
            ]
            journal.tf = Counter(filtered_query)

            for key in Counter(filtered_query):
                entry = Idf.query.get(key)
                if entry is None:
                    idf = Idf(
                        term=key,
                        docs=[journal.id]
                    )
                    db.session.add(idf)
                else:
                    entry.docs.append(journal.id)
        for i in range(count):
            name = fake.name()
            doc_type = random.choice(["film", "audio", "photograph"])
            text = fake.text(max_nb_chars=100)
            other = Document(
                doc_type="other",
                day=random.randint(1, 28),
                month=fake.month_name(),
                year=fake.year(),
                posted_by=name,
                last_edited_by=name,
                title=fake.text(max_nb_chars=50),
                description=text,
                link='http://' + fake.domain_name(),
                author_first_name=fake.first_name(),
                author_last_name=fake.last_name(),
                other_type=doc_type,
                document_status=random.choice(["draft", "published"]))

            db.session.add(other)
            word_tokens = word_tokenize(other.corpus)
            filtered_query = [
                stemmer.stem(w).lower()
                for w in word_tokens
                if w not in stop_words
            ]
            other.tf = Counter(filtered_query)

            for key in Counter(filtered_query):
                entry = Idf.query.get(key)
                if entry is None:
                    idf = Idf(
                        term=key,
                        docs=[other.id]
                    )
                    db.session.add(idf)
                else:
                    entry.docs.append(other.id)
        for i in range(count):
            name = fake.name()
            body = random.choice([
                "105th Congress", "106th Congress", "107th Congress"
            ])
            text = fake.text(max_nb_chars=100)
            law = Document(
                doc_type="law",
                day=random.randint(1, 28),
                month=fake.month_name(),
                year=fake.year(),
                citation=fake.sentence(),
                region=fake.country(),
                posted_by=name,
                last_edited_by=name,
                title=fake.text(max_nb_chars=50),
                description=text,
                country="United States",
                link='http://' + fake.domain_name(),
                govt_body=body,
                section=random.randint(1, 100),
                document_status=random.choice(["draft", "published"]),
                tf=Counter(filtered_query))

            db.session.add(law)
            word_tokens = word_tokenize(law.corpus)
            filtered_query = [
                stemmer.stem(w).lower()
                for w in word_tokens
                if w not in stop_words
            ]
            law.tf = Counter(filtered_query)

            for key in Counter(filtered_query):
                entry = Idf.query.get(key)
                if entry is None:
                    idf = Idf(
                        term=key,
                        docs=[law.id]
                    )
                    db.session.add(idf)
                else:
                    entry.docs.append(law.id)
        for i in range(count):
            name = fake.name()
            text = fake.text(max_nb_chars=100)
            video = Document(
                doc_type="video",
                day=random.randint(1, 28),
                month=fake.month_name(),
                year=fake.year(),
                name=fake.sentence(),
                source=fake.name(),
                posted_by=name,
                last_edited_by=name,
                title=fake.text(max_nb_chars=50),
                description=text,
                link='http://' + fake.domain_name(),
                author_first_name=fake.first_name(),
                author_last_name=fake.last_name(),
                document_status=random.choice(["draft", "published"]))

            db.session.add(video)
            word_tokens = word_tokenize(video.corpus)
            filtered_query = [
                stemmer.stem(w).lower()
                for w in word_tokens
                if w not in stop_words
            ]
            video.tf = Counter(filtered_query)

            for key in Counter(filtered_query):
                entry = Idf.query.get(key)
                if entry is None:
                    idf = Idf(
                        term=key,
                        docs=[video.id]
                    )
                    db.session.add(idf)
                else:
                    entry.docs.append(video.id)

        db.session.commit()

    def __repr__(self):
        return (
            '<Document \n'
            'Type: {self.doc_type}\n'
            'Day: {self.day}\n'
            'Month: {self.month}\n'
            'Year: {self.year}\n'
            'Posted Date: {self.posted_date}\n'
            'Last Edited Date: {self.last_edited_date}\n'
            'Posted By: {self.posted_by}\n'
            'Last Edited By: {self.last_edited_by}\n'
            'Title: {self.title}\n'
            'Description: {self.description}\n'
            'Link: {self.link}\n>'
            'File: {self.file}\n>'
            'Citation: {self.citation}\n>'
            'Volume: {self.volume}\n>'
            'Edition: {self.edition}\n>'
            'Series: {self.series}\n>'
            'Author First Name: {self.author_first_name}\n>'
            'Author Last Name: {self.author_last_name}\n>'
            'Name: {self.name}\n>'
            'Country: {self.country}\n>'
            'Affiliated Government Body*: {self.govt_body}\n>'
            'Section: {self.section}\n>'
            'Type (if other): {self.other_type}\n>'
            'Document Status: {self.document_status}\n>'
        )

    def __str__(self):
        return self.__repr__()
