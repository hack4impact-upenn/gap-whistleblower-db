from .. import db

class Tag(db.Model):
    __tablename__ = 'tag'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String())
    num_docs = db.Column(db.Integer())

    @staticmethod
    def generate_fake(count=10, **kwargs):
        from sqlalchemy.exc import IntegrityError
        from faker import Faker

        fake = Faker()
        tags = []
        for i in range(count):
            item = Tag(
                name=fake.word(),
                num_docs=fake.random_int(min=0, max=1000)
            )
            tags.append(item)
            db.session.add(item)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
        return tags

    def __repr__(self):
        return '<Tag: Name = {}>'.format(self.name)
