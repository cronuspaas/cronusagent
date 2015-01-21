#pylint: disable=W0703, R0912,W0105
"""The base Controller API

Provides the BaseController class for subclassing.
"""

from pylons.controllers import WSGIController

import logging
from pylons import request
from agent.lib import contextutils, manifestutil

LOG = logging.getLogger(__name__)

class BaseController(WSGIController):
    """ base controller class """

    def __call__(self, environ, start_response):
        """Invoke the Controller"""
        # WSGIController.__call__ dispatches to the Controller method
        # the request is routed to. This routing information is
        # available in environ['pylons.routes_dict']

        # before setting anything new, first reset the old values from previous request if any
        contextutils.resetcontext(self)

        #LOG.debug(environ)
        if 'service' in environ['pylons.routes_dict']:
            servicename = environ['pylons.routes_dict']['service']
            #if not registered, agent will not try to replace

            if servicename is not None and servicename.count('.') == 2:
                servicename = manifestutil.expandServiceName(servicename)
                LOG.info('service name expanded %s ' % servicename)
                environ['pylons.routes_dict']['service'] = servicename
            
            contextutils.injectcontext(self, {'service': servicename})
            
        # get correlationid into context
        if 'X-CORRELATIONID' in request.headers and request.headers['X-CORRELATIONID'] is not None:
            contextutils.injectcontext(self, {'guid': request.headers['X-CORRELATIONID']})

        # get timeouts and inject into context
        if 'X-THREAD_TIMEOUT' in request.headers and request.headers['X-THREAD_TIMEOUT'] is not None:
            contextutils.injectcontext(self, {'thread_timeout': request.headers['X-AGENT_THREAD_TIMEOUT']})

        # get progress timeouts and inject into context
        if 'X-THREAD_PROGRESS_TIMEOUT' in request.headers and request.headers['X-THREAD_PROGRESS_TIMEOUT'] is not None:
            contextutils.injectcontext(self, {'thread_progress_timeout': request.headers['X-THREAD_PROGRESS_TIMEOUT']})
            
        contextutils.injectcontext(self, {'requrl': request.path_qs})

        reqChecksum = '%s %s %s' % (request.method, request.path_qs, request.body if request.body else '')
        contextutils.injectcontext(self, {'reqstr': reqChecksum})

        # get remote address from request
        remoteAddr = request.environ.get("X_FORWARDED_FOR", request.environ.get("REMOTE_ADDR"))
        contextutils.injectcontext(self, {'remote_addr': remoteAddr})

        return WSGIController.__call__(self, environ, start_response)


    def injectJobCtx(self, target):
        ''' inject both guid and callback into an object
            @param target: target
        '''
        contextutils.copycontexts(self, target, contextutils.CTX_NAMES)

