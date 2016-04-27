import cgi
import re
import pprint

from .utils import (
    get_server,
    get_dependencies
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
    )


@subscriber(IBeforeRender)
def globals_factory(event):
    master = get_renderer('templates/master.pt').implementation()
    event['master'] = master
    event['logged_in'] = False

@view_config(route_name='view_main_page', renderer='templates/main.pt',
    permission='view')
def view_main_page(request):
    logged_in=request.authenticated_userid
    olds = []
    if logged_in:
        olds = DBSession.query(OLD).all()
    params = {'env_dir': request.registry.settings['senex.env_dir']}
    return dict(
        edit_url=request.route_url('edit_senex'),
        logged_in=logged_in,
        olds=olds,
        server=get_server(),
        dependencies=get_dependencies(params)
        )

# TODO: create an "Edit Senex" page.
@view_config(route_name='edit_senex', renderer='templates/main.pt',
    permission='edit')
def edit_senex(request):
    edit_url = request.route_url('edit_senex')
    login_url = request.route_url('login')
    logout_url = request.route_url('logout')
    return dict(edit_url=edit_url, login_url=login_url)

@view_config(route_name='view_old', renderer='templates/view_old.pt',
    permission='view')
def view_old(request):
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

