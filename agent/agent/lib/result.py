#pylint: disable=W0105
"""This object helps create the result output"""

import logging
import json
from pylons import url
from agent.lib import contextutils

LOG = logging.getLogger(__name__)

NORMAL = '0'
WARNING = '1'
CRITICAL = '2'
DEBUG = '99'

def doneResult(request, response, httpStatus=200, result = None, controller = None):
    """ return a done result """

    response.status_int = httpStatus
    response.content_type = 'application/json'
    res = {}
    res['progress'] = 100
    res['status'] = url(controller='status', action='done')
    if (result != None):
        res['result'] = result

    __injectcontext(controller, NORMAL, result)

    return json.dumps(res)

def statusResultRaw(request, response, result):
    """ take a json object and directly return to client as status """
    response.status_int = 200
    response.content_type = 'application/json'
    return json.dumps(result)

def statusResult(request, response, thread, controller = None, maxProgress = 100):
    """ set and return the status result """

    threadStatus = thread.getStatus()
    response.status_int = threadStatus['httpStatus']
    response.content_type = 'application/json'

    res = getThreadStatus(thread, maxProgress)
    
    # check if the result is an error not not
    if (threadStatus['error'] == None):
        status = NORMAL
        msg = 'progress %s' % str(threadStatus['progress'])
    else:
        status = CRITICAL
        msg = threadStatus['errorMsg']

    __injectcontext(controller, status, msg)

    return json.dumps(res)

def errorResult(request, response, error, errorMsg, httpStatus = 500, result = None, controller = None):
    """ set and return the error result
        @param controller: pylon controller handling the request, where cal context is injected and later retrieved by trackable
    """

    response.status_int = httpStatus
    response.content_type = 'application/json'

    res = {'error':error, 'errorMsg':errorMsg}
    if (result != None):
        res['result'] = result

    msg = 'Error Result - (%s, %s)' % (str(error), errorMsg)
    __injectcontext(controller, CRITICAL, msg)
    LOG.warning(msg)

    return json.dumps(res)

def __injectcontext(target, status, msg = None):
    ''' inject additional status and message
        @param target: target to inject context
        @param status: status
        @param msg: message
    '''
    if target is not None:
        if status is not None:
            contextutils.injectcontext(target, {'resstatus':status})
        if msg is not None:
            contextutils.injectcontext(target, {'resmsg':msg})

def getThreadStatus(thread, maxProgress = 100):
    ''' construct thread status json '''
    res = thread.status2msg()
    res['status'] = '/status/%s' % thread.getUuid()
    res['requrl'] = contextutils.getcontext(thread, "requrl", None)            

    return res
