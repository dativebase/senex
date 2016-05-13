import json
import datetime
import os

from .utils import (
    get_server,
    get_dependencies
    )

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
    Unicode,
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


# Default Server Settings Values
USER_DIR = os.path.expanduser('~')
DEFAULT_ENV_DIR = u'env-old'
DEFAULT_APPS_DIR = u'oldapps'
DEFAULT_APPS_PATH = unicode(os.path.join(USER_DIR, DEFAULT_APPS_DIR))
DEFAULT_SSL_DIR = u'sslcert'
DEFAULT_VH_PATH = u'/etc/nginx/sites-available/olds'


def get_default_dependency_state():
    return unicode(json.dumps(
        get_dependencies({'env_dir': DEFAULT_ENV_DIR})))

def get_default_server_state():
    return unicode(json.dumps(get_server({'apps_path': DEFAULT_APPS_PATH})))


class OLD(Base):
    """The model for holding OLD instances.

    """

    __tablename__ = u'olds'
    id = Column(Integer, primary_key=True)

    # Name of the OLD. No spaces. Should be something short, like an ISO 639-3
    # language code. Can't be changed once created.
    name = Column(Text, unique=True)

    # Name of the OLD's directory, MySQL database and path in its URL. Created
    # by concatenating the OLD's name with "old", e.g., "blaold".
    dir_name = Column(Text, unique=True)

    # A name for the OLD that is more descriptive. E.g., "Blackfoot".
    human_name = Column(Text)

    # The URL where the OLD is being served. This is Senex's `host` value
    # followed by `dir_name`. E.g.,
    # https://app.onlinelinguisticdatabase.org/blaold/
    url = Column(Text, default='')

    # The port that paster is serving this OLD on. Something like 9000.
    port = Column(Text, unique=True)

    # True if the OLD has been successfully built.
    built = Column(Boolean, default=False)

    # Last error message, if any, from the last build attempt.
    built_error_msg = Column(Text)

    # True if the OLD is running.
    running = Column(Boolean, default=False)

    # Last error message, if any, from the last attempt to start or stop the
    # OLD.
    running_error_msg = Column(Text)


class User(Base):
    """Senex user model. For authentication.

    """

    __tablename__ = u'users'
    id = Column(Integer, primary_key=True)
    username = Column(Unicode(255), unique=True)
    password = Column(Unicode(255))
    salt = Column(Unicode(255))
    email = Column(Unicode(255))
    groups = Column(UnicodeText, default=u'[]')
    first_name = Column(Text)
    last_name = Column(Text)


class SenexState(Base):
    """The model for holding Senex's state. These values can be determined on
    each request but that seems inefficient so we only refresh these values if
    the user requests a forced refresh or if a threshold time interval has
    passed.

    Note: to keep track of the history of the state, a new state model should
    be created upon each change. That is, an existing state should never be
    modified.

    """

    __tablename__ = u'senexstate'
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

    server_state = Column(UnicodeText, default=get_default_server_state)
    dependency_state = Column(UnicodeText, default=get_default_dependency_state)
    last_state_check = Column(DateTime, default=datetime.datetime.utcnow)

    # The following attributes are settings about the server that we need to
    # know in order to create new OLDs and manage them.

    # This is the username and password of the MySQL user that will be used to
    # create the OLDs.
    mysql_user = Column(Unicode(255), default=u'old')
    mysql_pwd = Column(Unicode(255))

    # This should be the name of the directory in the user's home directory
    # where the virtual environment for the OLD is located.
    # Note/TODO: the `paster_path` var that installold.py should be
    # derived from this, e.g., ~/<env_dir>/bin/paster.
    env_dir = Column(Unicode(255), default=DEFAULT_ENV_DIR)

    # This should be the full path to the directory where the OLDs will be
    # installed. The default should be something like the expansion of
    # ~/old-apps/, or similar.
    apps_path = Column(Unicode(255), default=DEFAULT_APPS_PATH)

    # The host name of the URL where the OLDs are being served, e.g., something
    # like www.myoldurl.com.
    host = Column(Unicode(255), default=u'app.onlinelinguisticdatabase.org')

    # The server that we are using: either "apache" or "nginx".
    server = Column(Text, default='nginx')

    # Path to the Apache/Nginx virtual hosts config file. This file may exist
    # but it doesn't need to; senex will create it, if needed. Defaults to a
    # file named `olds` located in /etc/apache2/sites-available/.
    vh_path = Column(Unicode(255), default=DEFAULT_VH_PATH)

    default_ssl_path = os.path.join(USER_DIR, DEFAULT_SSL_DIR)

    # Path to the SSL .crt file.
    default_ssl_cert_path = unicode(os.path.join(default_ssl_path, u'server.crt'))
    ssl_crt_path = Column(Unicode(255), default=default_ssl_cert_path)

    # Path to the SSL .key file.
    default_ssl_key_path = unicode(os.path.join(default_ssl_path, u'server.key'))
    ssl_key_path = Column(Unicode(255), default=default_ssl_key_path)

    # Path to the SSL .pem file, i.e., the intermediate certificate. Note:
    # Apache calls this the `SSLCertificateChainFile`. This is not required, at
    # least for Nginx deployments it doesn't seem to be.
    default_ssl_pem_path = unicode(os.path.join(default_ssl_path, u''))
    ssl_pem_path = Column(Unicode(255), default=default_ssl_pem_path)

    # These are the attributes of the `SenexState` model that are deemed
    # "settings" attributes.
    settings_attrs = [
        'mysql_user',
        'mysql_pwd',
        'env_dir',
        'apps_path',
        'host',
        'server',
        'vh_path',
        'ssl_crt_path',
        'ssl_key_path',
        'ssl_pem_path'
    ]

    def get_settings(self):
        return dict([(attr, getattr(self, attr)) for attr in self.settings_attrs])


class RootFactory(object):
    """This facilitates Pyramid's own authentication/authorization system. I
    don't fully understand it yet.

    """

    __acl__ = [ (Allow, Everyone, 'view'),
                (Allow, 'group:editors', 'edit') ]
    def __init__(self, request):
        pass

