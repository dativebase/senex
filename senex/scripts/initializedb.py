import os
import json
import sys
import transaction

from sqlalchemy import engine_from_config

from pyramid.paster import (
    get_appsettings,
    setup_logging,
    )

from ..models import (
    DBSession,
    OLD,
    User,
    SenexState,
    Base,
    )

from ..utils import (
    generate_salt,
    encrypt_password,
    )


def usage(argv):
    cmd = os.path.basename(argv[0])
    print('usage: %s <config_uri>\n'
          '(example: "%s development.ini")' % (cmd, cmd))
    sys.exit(1)


def main(argv=sys.argv):
    if len(argv) != 2:
        usage(argv)
    config_uri = argv[1]
    setup_logging(config_uri)
    settings = get_appsettings(config_uri)
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    Base.metadata.create_all(engine)

    with transaction.manager:
        senex_state = SenexState()
        DBSession.add(senex_state)
        admin = generate_default_administrator()
        DBSession.add(admin)


def generate_default_administrator():
    admin = User()
    admin.username = u'admin'
    admin.salt = generate_salt()
    admin.password = unicode(encrypt_password(u'adminAA11!!', str(admin.salt)))
    admin.groups = unicode(json.dumps(['group:editors']))
    admin.email = u'admin@example.com'
    admin.first_name = u'Admin'
    admin.last_name = u'Admin'
    return admin

