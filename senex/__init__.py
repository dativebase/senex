import json
from pyramid.config import Configurator
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.security import unauthenticated_userid
from pyramid.authorization import ACLAuthorizationPolicy

from sqlalchemy import engine_from_config

from .models import (
    DBSession,
    Base,
    User,
    )

from worker import start_worker


def get_user(request):
    userid = unauthenticated_userid(request)
    if userid is None:
        return None
    else:
        user = DBSession.query(User).filter_by(username=userid).first()
        if user:
            return user
        else:
            return None


def groupfinder(userid, request):
    user = request.user
    if user is not None:
        return json.loads(user.groups)
    return None


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    Base.metadata.bind = engine
    start_worker()
    authn_policy = AuthTktAuthenticationPolicy(
        'blargon5', callback=groupfinder, hashalg='sha512', timeout=900)
    authz_policy = ACLAuthorizationPolicy()
    config = Configurator(settings=settings,
                          root_factory='senex.models.RootFactory')
    config.set_authentication_policy(authn_policy)
    config.set_authorization_policy(authz_policy)
    config.add_request_method(get_user, 'user', reify=True)
    config.include('pyramid_chameleon')
    config.add_static_view('static', 'static', cache_max_age=3600)

    config.add_route('view_main_page', '/')
    config.add_route('return_status', '/senexstatus')
    config.add_route('login', '/login')
    config.add_route('logout', '/logout')

    config.add_route('add_old', '/olds/add')
    config.add_route('view_old', '/olds/{oldname}')
    config.add_route('edit_old', '/olds/{oldname}/edit')

    config.add_route('add_user', '/users/add')
    config.add_route('view_user', '/users/{username}')
    config.add_route('edit_user', '/users/{username}/edit')

    config.scan()
    return config.make_wsgi_app()

