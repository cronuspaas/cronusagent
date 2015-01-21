#pylint: disable=W0703,R0912,R0915,E0102,E1101,E0202,R0904,R0914,W0105
""" Thread to perform creation of a service """

import os
import traceback
            
from agent.lib.errors import Errors
from agent.lib.errors import AgentException
from agent.lib import manifestutil, contextutils
from agent.lib.agent_thread.manifest_control import ManifestControl
from agent.lib.agent_thread.manifest_create import ManifestCreate
from agent.lib.agent_thread.activate_manifest import ActivateManifest


class DeployService(ManifestControl):
    """ This thread will attempt 
    1. create service if not exist
    2. create manifets if not exist
    3. activate if not already activated
    """

    THREAD_NAME = 'deploy_service'

    def __init__(self, threadMgr, service, manifest, packages):
        """ Constructor """
        ManifestControl.__init__(self, threadMgr, service, manifest)
        self.setName(DeployService.THREAD_NAME)
        self.__packages = packages

    def doRun(self):
        """ Main body of the thread """
        self._updateProgress(1)

        errorMsg = ""
        errorCode = None
        failed = False
        
        try:
            # create manifest if not already exist
            mpath = manifestutil.manifestPath(self._service, self._manifest)
            if (not os.path.exists(mpath) or not os.path.isdir(mpath)):
                self._LOG.debug('pkgs = %s', self.__packages)

                # parse the package list
                for idx, package in enumerate(self.__packages):
                    if package.startswith('/'):
                        packageRef = package
                        tokens = package.split('/')
                        pkgnamePrefix = tokens[-1].rstrip()
                        fullPkgLoc = manifestutil.getPackageFullLocByName(self._service, manifest = None, pkgnamePrefix = pkgnamePrefix)
                        if fullPkgLoc is None:
                            raise AgentException(Errors.MANIFEST_PACKAGE_DOES_NOT_EXIST, 
                                                 'manifest (%s/%s) package (%s) does not exist' % 
                                                 (self._service, self._manifest, self.__packages))
                        else:
                            self._LOG.info('expanding package reuse ref %s with full package location %s' % (packageRef, fullPkgLoc))
                            self.__packages[idx] = fullPkgLoc

                # start a thread to create the package
                manThread = ManifestCreate(self._threadMgr, self._service, self._manifest, self.__packages, parentId = self.getUuid())
                contextutils.copyJobContexts(self, manThread)
                manThread.run()
                
                self._addChildExeThreadId(manThread.getChildExeThreadIds())

                status = manThread.getStatus()
                if (status['error'] != None):
                    raise AgentException(status['error'], status['errorMsg'])
                
            
            self._updateProgress(60)
            if (not os.path.exists(mpath)):
                raise AgentException(Errors.ACTIVEMANIFEST_MANIFEST_MISSING,
                                'Manifest(%s, %s) path missing' % (self._service, self._manifest))

            # activate manifest if not already activated
            activateThread = ActivateManifest(self._threadMgr, self._service, self._manifest, parentId = self.getUuid())
            contextutils.copyJobContexts(self, activateThread)
            activateThread.run()
            
            self._addChildExeThreadId(activateThread.getChildExeThreadIds())

            status = activateThread.getStatus()
            if (status['error'] != None):
                raise AgentException(status['error'], status['errorMsg'])

            if manifestutil.getActiveManifest(self._service) != self._manifest:
                raise AgentException(Errors.ACTIVEMANIFEST_MANIFEST_MISSING,
                                    'Manifest(%s, %s) path missing' % (self._service, self._manifest))

        except SystemExit as exc:
            failed = True
            if (len(exc.args) == 2):
                # ok we got {err code, err msg}
                errorCode = exc.args[0]
                errorMsg = exc.args[1]
        
        except AgentException as exc:
            failed = True
            errorMsg = 'Deploy Service - Agent Exception - %s' % exc.getMsg()
            errorCode = exc.getCode()
        
        except Exception as exc:
            failed = True
            errorMsg = 'Deploy Service - Unknown error - (%s/%s) - %s - %s' \
                        % (self._service, self._manifest, str(exc), traceback.format_exc(5))
            errorCode = Errors.UNKNOWN_ERROR
        
        finally:
            if failed: 
                self._LOG.warning(errorMsg)
                self._updateStatus(httpStatus = 500, error = errorCode, errorMsg = errorMsg)
            else:
                self._updateProgress(100)

