from sqlalchemy import Column
from sqlalchemy import String
from sqlalchemy import Integer
from sqlalchemy import DateTime
from sqlalchemy.ext.declarative import declarative_base

MODELBASE = declarative_base()

class FileIndex(MODELBASE):
    """This represents a remote file
    """
    __tablename__ = "fileindex"
    pkid = Column(Integer, primary_key=True)
    url = Column(String)
    name = Column(String)
    domain = Column(String)
    last_indexed = Column(DateTime)
    content_type = Column(String)
    last_modified = Column(DateTime)
    content_length = Column(Integer)
