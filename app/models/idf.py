from .. import db
from . import User, MutableList
from sqlalchemy import Column, Integer, String
from sqlalchemy.dialects.postgresql import ARRAY


class Idf(db.Model):
    __tablename__ = 'idf'
    term = db.Column(db.String(1000), primary_key=True)
    docs = db.Column(MutableList.as_mutable(ARRAY(Integer())))
