from .. import db
from . import User
from sqlalchemy import Column, Integer, String, PickleType
from sqlalchemy.ext.mutable import Mutable
from sqlalchemy.dialects.postgresql import ARRAY

class MutableList(Mutable, list):
  def append(self, value):
    list.append(self, value)
    self.changed()

  def remove(self, value):
    value = list.remove(self, value)
    self.changed()
    return value

  @classmethod
  def coerce(cls, key, value):
    if not isinstance(value, MutableList):
      if isinstance(value, list):
        return MutableList(value)
      return Mutable.coerce(key, value)
    else:
      return value

class Idf(db.Model):
    __tablename__ = 'idf'
    term = db.Column(db.String(1000), primary_key=True)
    docs = db.Column(MutableList.as_mutable(ARRAY(String(1000))))
