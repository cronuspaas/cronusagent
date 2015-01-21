""" agent security """
from pylons import request, response
from agent.lib.result import errorResult
from agent.lib.errors import Errors

def invalidAuthHandler(message, result):
    ''' call back when unauthenticated user comes '''
    return errorResult(request, response, Errors.INVALID_AUTH, message, 401, result = result)

class UnauthorizedException(Exception):
    ''' exception thrown if it's a authenticated user'''
    def __init__(self, message):
        ''' constructor '''
        super(UnauthorizedException, self).__init__(message)
        self.message = message
