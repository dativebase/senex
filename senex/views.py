import cgi
import re
import pprint
import json
import datetime
import os
import string

from .buildold import (
    build,
    disable_cronjob,
    stop_serving,
    add_virtual_host,
    restart_server,
    get_dir_name_from_old_name,
    )

from .utils import (
    get_server,
    get_dependencies,
    validate_mysql_credentials,
    generate_salt,
    encrypt_password
    )

from pyramid.httpexceptions import (
    HTTPFound,
    HTTPNotFound,
    )

from pyramid.view import (
    view_config,
    forbidden_view_config,
    notfound_view_config,
)

from pyramid.security import (
    remember,
    forget,
)

from pyramid.renderers import get_renderer
from pyramid.interfaces import IBeforeRender
from pyramid.events import subscriber

from .models import (
    DBSession,
    OLD,
    User,
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
    'vh_path': 'Virtual Hosts file path',
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
    'vh_path': ('The full path to the Nginx/Apache virtual hosts file for proxying'
        ' requests to specific OLDs.'),
    'ssl_crt_path': 'The full path to your SSL Certificate .crt file.',
    'ssl_key_path': 'The full path to your SSL Certificate .key file.',
    'ssl_pem_path': 'The full path to your SSL Certificate .pem file.'
    }


def get_core_dependencies(server_settings):
    core_dependencies = [
        'Python',
        'OLD',
        'MySQL',
        'easy_install',
        'virtualenv',
        'MySQL-python',
        'importlib'
        ]
    if server_settings.get('server') == 'nginx':
        core_dependencies.append('Nginx')
    else:
        core_dependencies.append('Apache')
    return core_dependencies


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


def get_state(force_refresh=False):
    """Return the state of the server, i.e., its server stats (like OS and
    version) as well as the state of our OLD dependency installation. We return
    a cached value from the db if we've checked the actual state recently. If
    our state data are stale, we refresh them.

    """

    senex_state = get_senex_state_model()
    if senex_state:
        age = datetime.datetime.utcnow() - senex_state.last_state_check
        if age > state_stale_age() or force_refresh:
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

    core_dependencies = get_core_dependencies(settings)
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
    permission='edit')
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


def get_old_installed(dependency_state):
    try:
        return [d for d in dependency_state if d['name'] == 'OLD'][0]['installed']
    except:
        return False


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
        users = DBSession.query(User).all()
        server_state, dependency_state, settings, installation_in_progress = get_state()
        warnings = get_warnings(server_state, dependency_state, settings)
        if request.params.get('validate_settings') == 'true':
            warnings = validate_settings(settings, warnings)
        old_installed = get_old_installed(dependency_state)
        if settings.get('mysql_pwd'):
            settings['mysql_pwd'] = '********************'
        core_dependencies = get_core_dependencies(settings)
        return dict(
            add_old_url=request.route_url('add_old'),
            edit_settings_url=request.route_url('view_main_page'),
            validate_settings_url='%s?validate_settings=true' % request.route_url('view_main_page'),
            return_status_url=request.route_url('return_status'),
            install_old_deps_url='%s?install_old_deps=true' % request.route_url('view_main_page'),
            logged_in=logged_in,
            olds=olds,
            users=users,
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


def get_view_old_msg(request):
    if request.params.get('msg'):
        return {
            'notbuiltnostart':
                'This OLD has not been built so it cannot be started.',
            'notbuiltnostop':
                'This OLD has not been built so it cannot be stopped.'

            }.get(request.params['msg'], None)
    return None


@view_config(route_name='view_old', renderer='templates/view_old.pt',
    permission='edit')
def view_old(request):
    """View a specific OLD.

    """

    oldname = request.matchdict['oldname']
    old = DBSession.query(OLD).filter_by(name=oldname).first()
    msg = get_view_old_msg(request)
    if old is None:
        raise HTTPNotFound('No such OLD')
    edit_url = request.route_url('edit_old', oldname=oldname)
    login_url = request.route_url('login')
    logout_url = request.route_url('logout')
    return dict(
        old=old,
        msg=msg,
        logged_in=request.authenticated_userid,
        edit_url=request.route_url('edit_old', oldname=oldname),
        login_url=request.route_url('login'),
        logout_url=request.route_url('logout')
        )


def validate_old(old):
    errors = {}
    name_error = validate_old_name(old)
    if name_error:
        errors['name'] = name_error
    return errors


def validate_old_name(old):
    if not re.search('^\w+$', old.name.strip()):
        return ('The name of an OLD can only contain letters, numbers'
            ' and/or the underscore.')
    existing_old = DBSession.query(OLD).filter_by(name=old.name).first()
    if existing_old:
        return ('There is already an OLD with the name %s installed here.'
            ' Please try again with a different name.' % old.name)
    existing_old = DBSession.query(OLD).filter_by(dir_name=old.dir_name).first()
    if existing_old:
        return ('Sorry, the name %s cannot be used because it is too similar to'
            ' an OLD that already exists. Please try again with a different'
            ' name.' % old.name)
    return None


@view_config(route_name='stop_old', renderer='templates/view_old.pt',
    permission='edit')
def stop_old(request):
    """Stop the OLD from being served, if it is being served. This should
    redirect requests to this OLD to some kind of error page so that users can
    see that they have the URL correct but that this particular OLD has just
    been stopped, probably temporarily.

    """

    oldname = request.matchdict['oldname']
    old = DBSession.query(OLD).filter_by(name=oldname).first()
    if not old:
        raise HTTPNotFound('No such OLD: %s' % oldname)
    if not old.built:
        location = '%s?msg=notbuiltnostop' % request.route_url(
            'view_old', oldname=old.name)
        return HTTPFound(location=location)
    build_params, warnings = get_build_params_and_warnings(old)
    build_params['old_port'] = old.port
    if not warnings:
        try:
            existing_olds = DBSession.query(OLD).all()
            for existing_old in existing_olds:
                if existing_old.name == old.name:
                    existing_old.running = False
            build_params['existing_olds'] = existing_olds
            add_virtual_host(build_params)
            restart_server(build_params)
        except SystemExit as e:
            print ('This error occurred when attempting to stop the OLD'
                ' %s: %s' % (old.name, e))
        except Exception as e:
            print ('This error occurred when attempting to stop the OLD'
                ' %s: %s' % (old.name, e))
        else:
            old.running = False
    DBSession.add(old)
    return HTTPFound(location = request.route_url('view_old', oldname=old.name))


@view_config(route_name='start_old', renderer='templates/view_old.pt',
    permission='edit')
def start_old(request):
    """Start a stopped OLD.

    """

    oldname = request.matchdict['oldname']
    old = DBSession.query(OLD).filter_by(name=oldname).first()
    if not old:
        raise HTTPNotFound('No such OLD: %s' % oldname)
    if not old.built:
        location = '%s?msg=notbuiltnostart' % request.route_url(
            'view_old', oldname=old.name)
        return HTTPFound(location=location)
    build_params, warnings = get_build_params_and_warnings(old)
    build_params['old_port'] = old.port
    if not warnings:
        try:
            existing_olds = DBSession.query(OLD).all()
            for existing_old in existing_olds:
                if existing_old.name == old.name:
                    existing_old.running = True
            build_params['existing_olds'] = existing_olds
            add_virtual_host(build_params)
            restart_server(build_params)
        except SystemExit as e:
            print ('This error occurred when attempting to stop the OLD'
                ' %s: %s' % (old.name, e))
        except Exception as e:
            print ('This error occurred when attempting to stop the OLD'
                ' %s: %s' % (old.name, e))
        else:
            old.running = True
    DBSession.add(old)
    return HTTPFound(location = request.route_url('view_old', oldname=old.name))


def get_build_params_and_warnings(old):
    build_params = get_build_params(old)
    server_state, dependency_state, settings, installation_in_progress = \
        get_state(True)
    warnings = get_warnings(server_state, dependency_state, settings)
    warnings = validate_settings(settings, warnings)
    return build_params, warnings


@view_config(route_name='add_old', renderer='templates/edit_old.pt',
    permission='edit')
def add_old(request):
    """Either create a new OLD or display the form for creating one.

    """

    if 'form.submitted' in request.params:
        name = request.params['name'].strip()
        dir_name = get_dir_name_from_old_name(name)
        human_name = request.params['human_name'].strip()
        old = OLD(name=name, dir_name=dir_name, human_name=human_name)
        errors = validate_old(old)
        if errors:
            return dict(old=old, errors=errors,
                logged_in=request.authenticated_userid,
                save_url=request.route_url('add_old'))
        build_params, warnings = get_build_params_and_warnings(old)
        if not warnings:
            try:
                existing_olds = DBSession.query(OLD).all()
                old.running = True
                existing_olds.append(old)
                build_params['existing_olds'] = existing_olds
                url, port = build(build_params, False)
            except SystemExit as e:
                print ('This error occurred when attempting to build the OLD'
                    ' %s: %s' % (old.name, e))
                old.running = False
            except Exception as e:
                print ('This error occurred when attempting to build the OLD'
                    ' %s: %s' % (old.name, e))
                old.running = False
            else:
                old.built = True
                old.url = url
                old.port = port
        DBSession.add(old)
        return HTTPFound(location = request.route_url('view_old', oldname=old.name))
    old = OLD(name='')
    return dict(old=old, errors={}, logged_in=request.authenticated_userid,
        save_url=request.route_url('add_old'))


def get_build_params(old):
    """Return the build params, a dict describing the OLD to be built and
    relevant aspects of Senex's state. This dict is needed by buildold.py's
    `build` function.

    """

    senex_state = get_senex_state_model()
    env_dir = senex_state.env_dir
    paster_path = os.path.join(os.path.expanduser('~'), env_dir, 'bin',
            'paster')
    olds = DBSession.query(OLD).all()
    used_ports = dict([(o.dir_name, o.port) for o in olds])
    return {
        'old_name': old.name,
        'old_dir_name': old.dir_name,
        'mysql_user': senex_state.mysql_user,
        'mysql_pwd': senex_state.mysql_pwd,
        'paster_path': paster_path,
        'apps_path': senex_state.apps_path,
        'server': senex_state.server,
        'vh_path': senex_state.vh_path,
        'ssl_crt_path': senex_state.ssl_crt_path,
        'ssl_key_path': senex_state.ssl_key_path,
        'ssl_pem_path': senex_state.ssl_pem_path,
        'host': senex_state.host,
        'used_ports': used_ports,
        'actions': [] # remembers what we've done, in case abort needed.
    }


@view_config(route_name='edit_old', renderer='templates/edit_old.pt',
    permission='edit')
def edit_old(request):
    """Edit an existing OLD or display the form for editing one. Note: only the
    `human_name` of an OLD can be edited.

    """

    oldname = request.matchdict['oldname']
    old = DBSession.query(OLD).filter_by(name=oldname).first()
    if 'form.submitted' in request.params:
        old.human_name = request.params['human_name']
        DBSession.add(old)
        return HTTPFound(location = request.route_url('view_old',
                                                      oldname=oldname))
    return dict(old=old, errors={}, logged_in=request.authenticated_userid,
        save_url=request.route_url('edit_old', oldname=oldname))


@notfound_view_config(renderer='templates/notfound.pt')
def notfound(request):
    request.response.status = '404 Not Found'
    return dict(msg='That page does not exist.')


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
        user = DBSession.query(User).filter_by(username=login).first()
        if user:
            salt = user.salt
            encrypted_password = unicode(encrypt_password(password, str(salt)))
            user2 = DBSession.query(User).filter_by(username=login)\
                    .filter_by(password=encrypted_password).first()
            if user2:
                headers = remember(request, login)
                return HTTPFound(location = came_from, headers = headers)
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


@view_config(route_name='edit_user', renderer='templates/edit_user.pt',
    permission='edit')
def edit_user(request):
    username = request.matchdict['username']
    user = DBSession.query(User).filter_by(username=username).first()
    if not user:
        raise HTTPNotFound('No such user: %s' % username)
    if 'form.submitted' in request.params:
        user.username = request.params['username'].strip()
        password = request.params['password'].strip()
        if password:
            user.oldpassword = user.password
            user.password = password
        user.email = request.params['email'].strip()
        user.groups = unicode(json.dumps(['group:editors']))
        user.first_name = request.params['first_name'].strip()
        user.last_name = request.params['last_name'].strip()
        errors = validate_user(user)
        if errors:
            if getattr(user, 'oldpassword', None):
                user.password = user.oldpassword
            return dict(
                user=user,
                errors=errors,
                logged_in=request.authenticated_userid,
                submit_url=request.route_url('edit_user', username=user.username),
                )
        if password:
            user.password = unicode(encrypt_password(user.password,
                str(user.salt)))
        DBSession.add(user)
        return HTTPFound(location = request.route_url('view_user',
            username=user.username))
    return dict(
        user=user,
        errors={},
        logged_in=request.authenticated_userid,
        submit_url=request.route_url('edit_user', username=user.username),
        )


@view_config(route_name='add_user', renderer='templates/edit_user.pt',
    permission='edit')
def add_user(request):
    if 'form.submitted' in request.params:
        username = request.params['username'].strip()
        password = request.params['password'].strip()
        salt = generate_salt()
        email = request.params['email'].strip()
        groups = unicode(json.dumps(['group:editors']))
        first_name = request.params['first_name'].strip()
        last_name = request.params['last_name'].strip()
        user = User(
            username=username,
            password=password,
            salt=salt,
            email=email,
            groups=groups,
            first_name=first_name,
            last_name=last_name
            )
        errors = validate_user(user)
        if errors:
            return dict(
                user=user,
                errors=errors,
                logged_in=request.authenticated_userid,
                submit_url=request.route_url('add_user'),
                )
        user.password = unicode(encrypt_password(user.password, str(user.salt)))
        DBSession.add(user)
        return HTTPFound(location = request.route_url('view_user',
            username=user.username))
    return dict(
        user=User(),
        errors={},
        logged_in=request.authenticated_userid,
        submit_url=request.route_url('add_user'),
        )


@view_config(route_name='view_user', renderer='templates/view_user.pt',
    permission='edit')
def view_user(request):
    """View a specific user.

    """

    username = request.matchdict['username']
    user = DBSession.query(User).filter_by(username=username).first()
    if user is None:
        raise HTTPNotFound('No such user')
    edit_url = request.route_url('edit_user', username=username)
    login_url = request.route_url('login')
    logout_url = request.route_url('logout')
    return dict(
        user=user,
        logged_in=request.authenticated_userid,
        edit_url=request.route_url('edit_user', username=username),
        login_url=request.route_url('login'),
        logout_url=request.route_url('logout')
        )



def validate_user(user):
    errors = {}
    username_error = validate_user_username(user)
    if username_error:
        errors['username'] = username_error
    password_error = validate_user_password(user)
    if password_error:
        errors['password'] = password_error
    if not user.email:
        errors['email'] = 'An email address must be provided'
    return errors


def validate_user_username(user):
    if not user.username:
        return 'A username must be provided'
    if len(user.username) < 4:
        return 'A username must contain at least 4 characters'
    badchars = [c for c in user.username if c not in string.digits +
        string.letters + '_']
    if badchars:
        return 'A username can only contain letters, digits and the underscore'
    existing_user = DBSession.query(User).filter_by(username=user.username)\
        .first()
    if existing_user and user.id != existing_user.id:
        return ('There is already a user with the username %s. Please choose'
            ' another.' % user.username)
    return None


def validate_user_password(user):
    if getattr(user, 'id', None):
        if not user.password:
            return None
        if user.password == getattr(user, 'oldpassword', None):
            return None
    digits = [c for c in user.password if c in string.digits]
    uppercase = [c for c in user.password if c in string.uppercase]
    lowercase = [c for c in user.password if c in string.lowercase]
    punctuation = [c for c in user.password if c in string.punctuation]
    if (len(user.password) < 10 or
        len(digits) < 2 or
        len(uppercase) < 2 or
        len(lowercase) < 2 or
        len(punctuation) < 2):
        return ('Passwords must be at least 10 characters long and must contain'
            ' at least 2 digits, 2 uppercase letters, 2 lowercase letters, and'
            ' 2 punctuation characters.')
    return None

