from pyramid.security import (
    Allow,
    Everyone,
)

from sqlalchemy import (
    Column,
    Integer,
    Text,
    Boolean,
    )

from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy.orm import (
    scoped_session,
    sessionmaker,
    )

from zope.sqlalchemy import ZopeTransactionExtension

DBSession = scoped_session(sessionmaker(extension=ZopeTransactionExtension()))
Base = declarative_base()


class OLD(Base):
    __tablename__ = 'olds'
    id = Column(Integer, primary_key=True)
    name = Column(Text, unique=True)
    human_name = Column(Text)
    running = Column(Boolean)

class RootFactory(object):
    __acl__ = [ (Allow, Everyone, 'view'),
                (Allow, 'group:editors', 'edit') ]
    def __init__(self, request):
        pass

