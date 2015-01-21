#pylint: disable=W0703,W0105
""" cronus pylon app """
from pylons.wsgiapp import PylonsApp
import logging
import traceback

LOG = logging.getLogger(__name__)

class CronusPylonApp(PylonsApp):
    '''
    classdocs
    '''

    def __init__(self, config=None, **kwargs):
        '''
        Constructor
        '''
        super(CronusPylonApp, self).__init__(config)
                
    
    def find_controller(self, controller):
        ''' find controller '''
        val = None
        try:
            if (controller in self.globals.dynacontrollers):
                val = self.globals.dynacontrollers[controller]
            else:
                val = super(CronusPylonApp, self).find_controller(controller)
                            
        except Exception as excep:
            err_msg = 'Error status (%s) - %s' % (excep, traceback.format_exc(2))
            LOG.error('Unexpected error: %s' % err_msg)
            
        return val
