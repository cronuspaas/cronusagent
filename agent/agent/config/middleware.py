#pylint: disable=W0142,W0105
"""Pylons middleware initialization"""


from agent.config.environment import load_environment
from agent.lib.cronuspylonapp import CronusPylonApp
from beaker.middleware import SessionMiddleware
from paste.cascade import Cascade
from paste.deploy.converters import asbool
from paste.registry import RegistryManager
from paste.urlparser import StaticURLParser
from pylons.middleware import ErrorHandler, StatusCodeRedirect
from routes.middleware import RoutesMiddleware
from agent.config import gzipmiddelware

def make_app(global_conf, full_stack=True, static_files=True, gzip=True, **app_conf):
    """Create a Pylons WSGI application and return it

    ``global_conf``
        The inherited configuration for this application. Normally from
        the [DEFAULT] section of the Paste ini file.

    ``full_stack``
        Whether this application provides a full WSGI stack (by default,
        meaning it handles its own exceptions and errors). Disable
        full_stack when this application is "managed" by another WSGI
        middleware.

    ``static_files``
        Whether this application serves its own static files; disable
        when another web server is responsible for serving them.

    ``app_conf``
        The application's local configuration. Normally specified in
        the [app:<name>] section of the Paste ini file (where <name>
        defaults to main).

    """
    # Configure the Pylons environment
    config = load_environment(global_conf, app_conf)

    # The Pylons WSGI app
    #app = PylonsApp(config=config)
    app = CronusPylonApp(config=config)

    # Routing/Session/Cache Middleware
    app = RoutesMiddleware(app, config['routes.map'], singleton=False)
    app = SessionMiddleware(app, config)

    # CUSTOM MIDDLEWARE HERE (filtered by error handling middlewares)

    if asbool(full_stack):
        # Handle Python exceptions
        app = ErrorHandler(app, global_conf, **config['pylons.errorware'])

        # Display error documents for 401, 403, 404 status codes (and
        # 500 when debug is disabled)
#        if asbool(config['debug']):
#            app = StatusCodeRedirect(app)
#        else:
#            app = StatusCodeRedirect(app, [400, 401, 403, 404, 500])
        app = StatusCodeRedirect(app, errors=())

    # Establish the Registry for this application
    app = RegistryManager(app)
    apps = [app]
    if asbool(static_files):
        # Serve static files
        static_app = StaticURLParser(config['pylons.paths']['static_files'])
        apps.insert(0, static_app)
        #app = Cascade([static_app, app])
        
    if asbool(gzip):
        # serve gzip response
        gzip_app = gzipmiddelware.gzipmiddleware(app, compress_level=6)
        apps.insert(0, gzip_app)
        
    app = Cascade(apps)
    app.config = config
    return app
