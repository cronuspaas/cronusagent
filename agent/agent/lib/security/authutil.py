#pylint: disable=W0702
""" authentication utils """
import json
import logging
import os
import traceback

from agent.lib import manifestutil


LOG = logging.getLogger(__name__)

def readSecureMeta():
    """ get all secure metadata """
    result = {}
    metaContentPath = os.path.join(manifestutil.appDataPath('agent'), 'secure', '.metadata.json')
    try:
        with open(metaContentPath, 'rb') as metadata_fp:
            result = json.load(metadata_fp)
    except BaseException:
        # fine, file not exist
        pass
    
    return result   

def updateSecureMeta(pushedData=None):
    """ create/update secure .metadata.json 
        @pushedData: more data to be pushed to .metadata file
        @return dict written to the file 
    """ 
    result_cleaned = {}
    try:
        # load existing metadata
        result = readSecureMeta()
        dataFound = False

        if type(pushedData) == dict:
            for key, value in pushedData.iteritems():
                if isinstance(value, basestring):
                    dataFound = True
                    result[key] = value
                else:
                    LOG.warn('metadata value is not string %s: %s' % (key, value))

        # now remove none
        result_cleaned = dict((k, v) for k, v in result.iteritems() if v is not None)

        # update if there is data
        if dataFound:
            metaContentPath = os.path.join(manifestutil.appDataPath('agent'), 'secure', '.metadata.json')
            _writeJsonServiceMeta(result_cleaned, metaContentPath)
        else:
            LOG.info('no data found, skip secure .metadata update')
                                
    except BaseException as excep:
        LOG.error('Error updating secure metadata file %s - %s' % (str(excep), traceback.format_exc(2)))
            
    return result_cleaned

def _writeJsonServiceMeta(mainHash, metaContentPath):
    """Write an .metadata.json-format representation of the configuration state."""
    with open(metaContentPath, 'wb+') as md_fp:
        jsonStr = json.dumps(mainHash)
        md_fp.write(jsonStr)
        md_fp.write("\n")
