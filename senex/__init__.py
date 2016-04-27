from pyramid.config import Configurator
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy

from sqlalchemy import engine_from_config

from senex.security import groupfinder

from .models import (
    DBSession,
    Base,
    )


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    Base.metadata.bind = engine
    authn_policy = AuthTktAuthenticationPolicy(
        'sosecret', callback=groupfinder, hashalg='sha512')
    authz_policy = ACLAuthorizationPolicy()
    config = Configurator(settings=settings,
                          root_factory='senex.models.RootFactory')
    config.set_authentication_policy(authn_policy)
    config.set_authorization_policy(authz_policy)
    config.include('pyramid_chameleon')
    config.add_static_view('static', 'static', cache_max_age=3600)

    config.add_route('view_main_page', '/')
    config.add_route('login', '/login')
    config.add_route('logout', '/logout')
    config.add_route('edit_senex', '/edit')

    config.add_route('view_old', '/{oldname}')
    config.add_route('add_old', '/add/{oldname}')
    config.add_route('edit_old', '/{oldname}/edit')

    config.scan()
    return config.make_wsgi_app()

