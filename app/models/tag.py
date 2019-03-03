from .. import db

class Tag(db.Model):
    __tablename__ = 'tag'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String())

    @staticmethod
    def generate_fake(count=10, **kwargs):
        from sqlalchemy.exc import IntegrityError
        from faker import Faker

        fake = Faker()
        tags = []
        for i in range(count):
            item = Tag(
                name=fake.word()
            )
            tags.append(item)
            db.session.add(item)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
        return tag


    def __repr__(self):
        return '<Tag: Name = {}>'.format(self.name)
