#pylint: disable=E1121,W0105
'''
Created on Apr 30, 2014

@author: biyu
'''
from pylons import request
from agent.lib.security import agentauth

import logging
from agent.lib.base import BaseController

LOG = logging.getLogger(__name__)

class ModuleBaseController(BaseController):
    """ base controller class for pluggable module controller
        force authn & authz for any non GET call
    """

    def __call__(self, environ, start_response):
        """Invoke the Controller"""
        if request.method != 'GET':
            return agentauth.authorize(BaseController.__call__, self, environ, start_response)
        else:
            return BaseController.__call__(self, environ, start_response)

    @property
    def logger(self):
        """ logger property """
        return LOG

