import datetime

from pyramid.security import (
    Allow,
    Everyone,
)

from sqlalchemy import (
    Column,
    Integer,
    Text,
    Boolean,
    UnicodeText,
    DateTime,
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
    """The model for holding OLD instances.

    """

    __tablename__ = 'olds'
    id = Column(Integer, primary_key=True)
    name = Column(Text, unique=True)
    human_name = Column(Text)
    running = Column(Boolean)


class SenexState(Base):
    """The model for holding Senex's state. These values can be determined on
    each request but that seems inefficient so we only refresh these values if
    the user requests a forced refresh or if a threshold time interval has
    passed.

    Note: to keep track of the history of the state, a new state model should
    be created upon each change. That is, an existing state should never be
    modified.

    """

    __tablename__ = 'senexstate'
    id = Column(Integer, primary_key=True)

    # Set to `True` when the OLD and/or its dependencies are being installed.
    # We don't want multiple concurrent install requests to be possible.
    installation_in_progress = Column(Boolean, default=False)

    # Set to `True` when an OLD is being changed, i.e., created, started,
    # stopped. We don't want multiple concurrent OLD manipulation requests to be
    # possible.
    old_change_in_progress = Column(Boolean, default=False)

    # The following two columns hold JSON-serialized data structures that
    # encode our server's state.
    server_state = Column(UnicodeText)
    dependency_state = Column(UnicodeText)
    last_state_check = Column(DateTime, default=datetime.datetime.utcnow)


class RootFactory(object):
    """This facilitates Pyramid's own authentication/authorization system. I
    don't fully understand it yet.

    """

    __acl__ = [ (Allow, Everyone, 'view'),
                (Allow, 'group:editors', 'edit') ]
    def __init__(self, request):
        pass

