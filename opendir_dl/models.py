from sqlalchemy import Column
from sqlalchemy import String
from sqlalchemy import Integer
from sqlalchemy import DateTime
from sqlalchemy import Table
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

MODELBASE = declarative_base()

# The association table relates file indexes with tags
ASSOCIATION_TABLE = Table('associations', MODELBASE.metadata,
                          Column('left_pkid', Integer, ForeignKey('fileindex.pkid')),
                          Column('right_pkid', Integer, ForeignKey('tags.pkid')))

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
    tags = relationship("Tags", secondary=ASSOCIATION_TABLE, back_populates="indexes")

class Tags(MODELBASE):
    """This represents a tag
    """
    __tablename__ = "tags"
    pkid = Column(Integer, primary_key=True)
    name = Column(String)
    indexes = relationship("FileIndex", secondary=ASSOCIATION_TABLE, back_populates="tags")
