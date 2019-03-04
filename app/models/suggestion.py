from .. import db

class Suggestion(db.Model):
    __tablename__ = 'suggestion'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(64))
    link = db.Column(db.String())
    description = db.Column(db.Text)

    @staticmethod
    def generate_fake(count=10, **kwargs):
        from sqlalchemy.exc import IntegrityError
        from faker import Faker

        fake = Faker()
        suggestions = []
        for i in range(count):
            item = Suggestion(
                title=fake.sentence(),
                link=fake.domain_name(),
                description=fake.text(max_nb_chars=1000)
            )
            suggestions.append(item)
            db.session.add(item)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
        return suggestions


    def __repr__(self):
        return '<Suggestion: Title = {}, Description = {}, Link = {}>'.format(
            self.title, self.description, self.link)
