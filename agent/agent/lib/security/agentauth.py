#pylint: disable=E1121,W0105,R0914,R0912,E0602
""" agent authentication """
from agent.lib import configutil
from pylons import request, config
import logging
import re
import base64
from decorator import decorator
from agent.lib import manifestutil, utils
import os
import traceback


LOG = logging.getLogger(__name__)

def authorize():
    '''
    docorator for authorize
    @parameter inSecurity: bool indicating whether incoming security need to check
    '''
    def validate(func, self, *args, **kwargs):
        ''' function that calls authorizing function'''
        
        isAuthEnabled = True
        isPkiEnabled = False
        authPassed = False
        
        try:
            appGlobal = config['pylons.app_globals']

            isPkiEnabled = (appGlobal.encryptedtokens and configutil.getConfigAsBool('pkiauth_enabled'))
            isAuthEnabled = isPkiEnabled or configutil.hasSecurePassword()
        
        except BaseException as excep:
            LOG.error('Error loading auth config %s - %s' % (str(excep), traceback.format_exc(2)))
            
        if isAuthEnabled:
            
            inHeader = None
            if 'authorization' in request.headers:
                inHeader = request.headers['authorization']
            elif 'Authorization' in request.headers:
                inHeader = request.headers['Authorization']
            else:
                return invalidAuthHandler('Authorization header missing', {})

            message = None
            result = {}
            
            # base authentication
            if not isPkiEnabled:
                token = configutil.getConfig('password.local')
                try:
                    isAuthenticated(token, inHeader)
                    authPassed = True
                except UnauthorizedException:
                    message = 'Please provide valid username and password'
                    result['scheme'] = 'base'
                
            if not authPassed:
                # try pki authentication
                token = appGlobal.authztoken 
                try: 
                    isAuthenticated(token, inHeader)
                    authPassed = True
                except UnauthorizedException:
                    if isPkiEnabled:
                        result['scheme'] = 'pki'
                        user = request.headers['AuthorizationUser'] if 'AuthorizationUser' in request.headers else 'agent'  
                        pubKey = '%s.cert' % user 
                        if pubKey in appGlobal.encryptedtokens:
                            message = appGlobal.encryptedtokens[pubKey]
                            result['key'] = appGlobal.encryptedtokens[pubKey]
                        else:
                            message = 'Unknown AuthroizationUser %s' % user

                    return invalidAuthHandler(message, result)

        return func(self, *args, **kwargs)

    return decorator(validate)

def isAuthenticated(token, inHeader):
    ''' check whether user name and password are right '''
    message = 'Please provide valid username and password'
    try:
        if inHeader is not None:
            base64string = base64.encodestring(token)[:-1]
            match = re.match(r'\s*Basic\s*(?P<auth>\S*)$', inHeader)

            if match is not None and match.group('auth') == base64string:
                return True

        raise UnauthorizedException(message + " Header:" + str(request.headers))
    except:
        raise UnauthorizedException(message + " Header:" + str(request.headers))

def buildTokenCache(authztoken):
    """ build in memory cache for security tokens """
    # find all pub keys in agent and encrypt the security token with them
    appGlobal = config['pylons.app_globals']
    pubKeyDir = os.path.join(manifestutil.appDataPath('agent'), 'secure')
    LOG.debug('key directory %s' % pubKeyDir)
    if os.path.exists(pubKeyDir):
        try:
            pubKeyFiles = [f for f in os.listdir(pubKeyDir) if re.match(r'.*\.pub', f)]
            LOG.info('key files %s' % pubKeyFiles)
            for pubKeyFile in pubKeyFiles:
                # reload the certs from disk
                scriptPath = manifestutil.getPackageScriptPath('agent', 'active', 'agent', 'encryptkey')
                encryptedToken = utils.encrpyKey(scriptPath, os.path.join(pubKeyDir, pubKeyFile), authztoken)
                
                appGlobal.encryptedtokens[pubKeyFile] = encryptedToken    
                LOG.debug('token %s=%s' % (pubKeyFile, encryptedToken))
        except BaseException as excep:
            LOG.error('Error loading pki keys %s - %s' % (str(excep), traceback.format_exc(2)))
            
    
    
