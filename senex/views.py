import cgi
import re
import pprint
import json
import datetime
import os

from .utils import (
    get_server,
    get_dependencies,
    validate_mysql_credentials,
    generate_salt
    )

from pyramid.httpexceptions import (
    HTTPFound,
    HTTPNotFound,
    )

from pyramid.view import (
    view_config,
    forbidden_view_config,
)

from pyramid.security import (
    remember,
    forget,
)

from pyramid.renderers import get_renderer
from pyramid.interfaces import IBeforeRender
from pyramid.events import subscriber

from .security import USERS

from .models import (
    DBSession,
    OLD,
    SenexState,
    )

from worker import worker_q


# Human-readable settings labels.
setting_labels_human = {
    'mysql_user': 'MySQL username',
    'mysql_pwd': 'MySQL password',
    'env_dir': 'Virtual Environment directory',
    'apps_path': 'OLD Applications path',
    'host': 'Host name',
    'vh_path': 'Apache Virtual Hosts file path',
    'ssl_crt_path': 'SSL Certificate .crt file path',
    'ssl_key_path': 'SSL Certificate .key file path',
    'ssl_pem_path': 'SSL Certificate .pem file path'
    }

# Tooltips (i.e., title values) for Senex's settings.
setting_tooltips = {
    'mysql_user': ('The username of a MySQL user that can create, alter and'
        ' drop databases and tables.'),
    'mysql_pwd': 'The password corresponding to the MySQL username.',
    'env_dir': ('The name of the directory (in your user\'s home directory)'
        ' where the Python virtual environment will be, or has been, created.'
        ' Where the OLD and its Python dependencies are installed.'),
    'apps_path': ('The full path to the directory which contains a directory'
        ' for each installed OLD.'),
    'host': ('The host name of the URL at which the OLDs will be served, e.g.,'
        ' www.myoldurl.com. OLDs will be served at a path relative to this'
        ' host.'),
    'vh_path': ('The full path to the Apache virtual hosts file for proxying'
        ' requests to specific OLDs.'),
    'ssl_crt_path': 'The full path to your SSL Certificate .crt file.',
    'ssl_key_path': 'The full path to your SSL Certificate .key file.',
    'ssl_pem_path': 'The full path to your SSL Certificate .pem file.'
    }

core_dependencies = (
    'Python',
    'OLD',
    'MySQL',
    'easy_install',
    'virtualenv',
    'MySQL-python',
    'importlib',
    'Apache'
    )


def create_new_state(previous_state=None):
    """Create a new Senex state model in our db and return it as a 2-tuple of
    `server_state` and `dependency_state`.

    """

    new_state = SenexState()
    if previous_state:
        for attr in new_state.settings_attrs:
            setattr(new_state, attr, getattr(previous_state, attr))
    server_state = get_server()
    new_state_settings = new_state.get_settings()
    dependency_state = get_dependencies(new_state_settings)
    new_state.server_state = unicode(json.dumps(get_server()))
    new_state.dependency_state = unicode(json.dumps(dependency_state))
    new_state.last_state_check = datetime.datetime.utcnow()
    DBSession.add(new_state)
    return server_state, dependency_state, new_state_settings


def state_stale_age():
    return datetime.timedelta(minutes=5)


def get_senex_state_model():
    return DBSession.query(SenexState).order_by(SenexState.id.desc()).first()


def get_state():
    """Return the state of the server, i.e., its server stats (like OS and
    version) as well as the state of our OLD dependency installation. We return
    a cached value from the db if we've checked the actual state recently. If
    our state data are stale, we refresh them.

    """

    senex_state = get_senex_state_model()
    if senex_state:
        age = datetime.datetime.utcnow() - senex_state.last_state_check
        if age > state_stale_age():
            server_state, dependency_state, settings = create_new_state(senex_state)
        else:
            dependency_state = json.loads(senex_state.dependency_state)
            server_state = json.loads(senex_state.server_state)
            settings = senex_state.get_settings()
    else:
        server_state, dependency_state, settings = create_new_state()
    return server_state, dependency_state, settings, senex_state.installation_in_progress 

@subscriber(IBeforeRender)
def globals_factory(event):
    """This gives the master Chameleon template to all of our other templates
    so they can just fill in its slots and everything can be DRY.

    """

    master = get_renderer('templates/master.pt').implementation()
    event['master'] = master
    event['logged_in'] = False


def update_settings(request):
    senex_state = get_senex_state_model()
    new_senex_state = SenexState()
    changed = False
    for attr in new_senex_state.settings_attrs:
        if attr == 'mysql_pwd':
            if request.params[attr]:
                setattr(new_senex_state, attr, request.params[attr])
        else:
            setattr(new_senex_state, attr, request.params[attr])
        if getattr(senex_state, attr) != getattr(new_senex_state, attr):
            changed = True
    if changed:
        new_state_settings = new_senex_state.get_settings()
        dependency_state = get_dependencies(new_state_settings)
        new_senex_state.server_state = unicode(json.dumps(get_server()))
        new_senex_state.dependency_state = unicode(json.dumps(dependency_state))
        new_senex_state.last_state_check = datetime.datetime.utcnow()
        DBSession.add(new_senex_state)
        return new_senex_state
    else:
        return senex_state


def get_warnings(server_state, dependency_state, settings):
    """Return a dict of warning messages if anything is wrong with the
    passed-in state/settings.

    """

    warnings = {}

    if (server_state.get('os') != 'Ubuntu Linux' or
        server_state.get('os_version', '')[:5] not in ('14.04', '10.04')):
        warnings['server'] = ('Senex is only known to work with Ubuntu Linux'
            ' 14.04 and 10.04.')

    for dependency in dependency_state:
        if (dependency['name'] in core_dependencies and
            not dependency['installed']):
            warnings['core_dependencies'] = ('Some of the OLD\'s core'
                ' dependencies are not installed.')
            break

    if not warnings.get('core_dependencies'):
        try:
            py_ver = [d for d in dependency_state if
                d['name'] == 'Python'][0].get('version', '')
            if py_ver.strip()[:3] not in ('2.6', '2.7'):
                warnings['core_dependencies'] = ('The OLD only works with'
                    ' Python 2.6 and 2.7')
        except:
            pass

    return warnings


def validate_settings(settings, warnings):
    """Do some basic validation of Senex's settings and return the warnings
    dict with new warnings, if there are settings validation issues.

    TODOs:

    - check if you can login with the MySQL credentials 'mysql_user' and
      'mysql_pwd'
      FOX

    """

    my_warnings = []
    for ext in ('crt', 'key', 'pem'):
        if (settings.get('ssl_%s_path' % ext) and
            not os.path.isfile(settings['ssl_%s_path' % ext])):
            my_warnings.append('There is no .%s file at the specified path.' % ext)
    mysql_warning = validate_mysql_credentials(settings)
    if mysql_warning:
        my_warnings.append(mysql_warning)
    if my_warnings:
        warnings['settings'] = ' '.join(my_warnings)
    return warnings


def install_old():
    """Install the OLD and all of its dependencies, given the settings
    specified in the most recent senex_state model.

    """

    senex_state = get_senex_state_model()
    if senex_state.installation_in_progress:
        print 'install already in progress; returning.'
        return
    senex_state.installation_in_progress = True
    DBSession.add(senex_state)
    settings = senex_state.get_settings()
    worker_q.put({
        'id': generate_salt(),
        'func': 'install_old',
        'args': settings
    })


@view_config(route_name='return_status', renderer='json',
    permission='view')
def return_status(request):
    """Return a JSON object indicating the status of Senex, in particular
    whether an installation is in progress. This is called asynchronously by
    a JavaScript-based long-polling strategy. See static/scripts.js.

    """

    logged_in = request.authenticated_userid
    if logged_in:
        senex_state = get_senex_state_model()
        return {'installation_in_progress':
            senex_state.installation_in_progress}
    else:
        return {'logged_in': False}


@view_config(route_name='view_main_page', renderer='templates/main.pt',
    permission='view')
def view_main_page(request):
    logged_in = request.authenticated_userid
    if logged_in:
        if ('form.submitted' in request.params and
            'edit.settings' in request.params):
            update_settings(request)
        if 'install_old_deps' in request.params:
            install_old()
        olds = DBSession.query(OLD).all()
        server_state, dependency_state, settings, installation_in_progress = get_state()
        warnings = get_warnings(server_state, dependency_state, settings)
        if request.params.get('validate_settings') == 'true':
            warnings = validate_settings(settings, warnings)
        old_installed = [d for d in dependency_state if d['name'] == 'OLD'][0]['installed']
        if settings.get('mysql_pwd'):
            settings['mysql_pwd'] = '********************'
        return dict(
            edit_settings_url=request.route_url('view_main_page'),
            validate_settings_url='%s?validate_settings=true' % request.route_url('view_main_page'),
            return_status_url=request.route_url('return_status'),
            install_old_deps_url='%s?install_old_deps=true' % request.route_url('view_main_page'),
            logged_in=logged_in,
            olds=olds,
            server=server_state,
            dependencies=dependency_state,
            core_dependencies=[d for d in dependency_state if d['name'] in core_dependencies],
            soft_dependencies=[d for d in dependency_state if d['name'] not in core_dependencies],
            settings=settings,
            setting_labels_human=setting_labels_human,
            setting_tooltips=setting_tooltips,
            old_installed=old_installed,
            installation_in_progress=installation_in_progress,
            warnings=warnings
            )
    else:
        return dict(logged_in=logged_in)

@view_config(route_name='view_old', renderer='templates/view_old.pt',
    permission='view')
def view_old(request):
    """View a specific OLD.

    """

    oldname = request.matchdict['oldname']
    old = DBSession.query(OLD).filter_by(name=oldname).first()
    if old is None:
        return HTTPNotFound('No such OLD')
    edit_url = request.route_url('edit_old', oldname=oldname)
    login_url = request.route_url('login')
    logout_url = request.route_url('logout')
    return dict(
        old=old,
        logged_in=request.authenticated_userid,
        edit_url=request.route_url('edit_old', oldname=oldname),
        login_url=request.route_url('login'),
        logout_url=request.route_url('logout')
        )


@view_config(route_name='add_old', renderer='templates/edit_old.pt',
    permission='edit')
def add_old(request):
    oldname = request.matchdict['oldname']
    if 'form.submitted' in request.params:
        # body = request.params['body']
        # TODO: get form field values from request params and instantiate a new
        # OLD with them.
        old = OLD(name=oldname)
        DBSession.add(old)
        return HTTPFound(location = request.route_url('view_old',
                                                      oldname=oldname))
    old = OLD(name='')
    return dict(
        old=old,
        logged_in=request.authenticated_userid,
        save_url=request.route_url('add_old', oldname=oldname),
        login_url=request.route_url('login'),
        logout_url=request.route_url('logout')
        )


@view_config(route_name='edit_old', renderer='templates/edit_old.pt',
    permission='edit')
def edit_old(request):
    oldname = request.matchdict['oldname']
    old = DBSession.query(OLD).filter_by(name=oldname).one()
    if 'form.submitted' in request.params:
        # TODO: use request params to modify `old` with form input values.
        # old.data = request.params['body']
        old.human_name = request.params['human_name']
        DBSession.add(old)
        return HTTPFound(location = request.route_url('view_old',
                                                      oldname=oldname))
    return dict(
        old=old,
        logged_in=request.authenticated_userid,
        save_url=request.route_url('edit_old', oldname=oldname),
        login_url=request.route_url('login'),
        logout_url=request.route_url('logout')
        )

@view_config(route_name='login', renderer='templates/login.pt')
@forbidden_view_config(renderer='templates/login.pt')
def login(request):
    login_url = request.route_url('login')
    referrer = request.url
    if referrer == login_url:
        referrer = '/' # never use the login form itself as came_from
    came_from = request.params.get('came_from', referrer)
    message = ''
    login = ''
    password = ''
    if 'form.submitted' in request.params:
        login = request.params['login']
        password = request.params['password']
        if USERS.get(login) == password:
            headers = remember(request, login)
            return HTTPFound(location = came_from,
                             headers = headers)
        message = 'Failed login'

    return dict(
        message = message,
        url = request.application_url + '/login',
        came_from = came_from,
        login = login,
        password = password
        )

@view_config(route_name='logout')
def logout(request):
    headers = forget(request)
    return HTTPFound(location = request.route_url('view_main_page'),
                     headers = headers)

