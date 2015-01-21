#pylint: disable=W0703,R0912,R0915,E0102,E1101,E0202,R0904,W0105,R0914
""" Thread to perform creation of a service """
from agent.lib import manifestutil
import os
import shutil
import traceback

import pylons

from agent.lib.agent_thread.manifest_control import ManifestControl
from agent.lib.errors import AgentException, Errors
from agent.lib.utils import readlink, symlink, islink


class ActivateManifest(ManifestControl):
    """ This thread will attempt to activate a manifest
    This means going throuh each package
    call the stop
    call the deactivate
    delete the active link
    call the activate
    create the active link
    call start
    """

    ACTION_ACTIVATION = 'activate'
    ACTION_DEACTIVATION = 'deactivate'
    ACTION_RESET = 'reset' 

    def __init__(self, threadMgr, service, manifest, action = 'activate', parentId = None):
        """ Constructor """
        ManifestControl.__init__(self, threadMgr, service, manifest, parentId = parentId)
        self.__action = action
        self.setName('%s_manifest' % action)

    def doRun(self):
        """ Main body of the thread """
        errorMsg = ""
        errorCode = None
        symlinkSwitched = False
        failed = False
        
        try:
            activePath = manifestutil.manifestPath(self._service)
            oldManifest = None
            
            # make sure that if the active path exists, it's a link
            # if not log that and delete the link
            if (os.path.exists(activePath) and not islink(activePath)):
                self._LOG.error('%s is not a link.  Attempted to delete' % activePath)
                shutil.rmtree(activePath)

            if (os.path.exists(activePath)):
                oldManifest = os.path.basename(readlink(activePath))
            # reset requires a valid active link exist
            else:
                if self.__action == ActivateManifest.ACTION_RESET:
                    raise AgentException(error = Errors.ACTIVEMANIFEST_MANIFEST_MISSING, 
                                         errorMsg = ('No active manifest - cannot %s service' 
                                                     % self.__action))

            if self.__action == ActivateManifest.ACTION_ACTIVATION:
                # install new manifest
                self.__installManifest(self._service, self._manifest)
            
            self._deactivateManifest(self._service, oldManifest, 11, 50)
            
            if self.__action == ActivateManifest.ACTION_ACTIVATION:
                # special logic to handle agent upgrade
                # agent upgrade will not run full activation agent will shutdown before activate exit
                if self._service == 'agent':
                    appGlobal = pylons.config['pylons.app_globals']
                    # persist threads result before shutting down
                    if (hasattr(appGlobal, 'threadMgr') and appGlobal.threadMgr != None):
                        killStatus = {}
                        killStatus['httpStatus'] = 500
                        killStatus['error'] = Errors.THREAD_KILLED_AGENT_RESTART
                        killStatus['errorMsg'] = 'thread killed, agent restart'
                        appGlobal.threadMgr.snapshot(killStatus, True)
            
                # switch active symlink
                symlinkSwitched = self.__switchSymlink(self._service, self._manifest)
                # activate new manifest
                self._activateManifest(self._service, self._manifest, 51, 80)

            elif self.__action == ActivateManifest.ACTION_DEACTIVATION:
                # remove active link on deactivate
                activePath = self.__getSymlinkPath(self._service)
                self.__removeSymlink(activePath)

            else:
                # activate new manifest
                self._activateManifest(self._service, self._manifest, 51, 80)

        except SystemExit as exc:
            failed = True
            if (len(exc.args) == 2):
                # ok we got {err code, err msg}
                errorCode = exc.args[0]
                errorMsg = exc.args[1]
            raise exc
        
        except AgentException as exc:
            failed = True
            errorMsg = '%s manifest - Agent Exception - %s' % (self.__action, exc.getMsg())
            errorCode = exc.getCode()
        
        except Exception as exc:
            failed = True
            errorMsg = '%s manifest - Unknown error - (%s/%s) - %s - %s' \
                        % (self.__action, self._service, self._manifest, 
                           str(exc), traceback.format_exc(5))
            errorCode = Errors.UNKNOWN_ERROR
        
        finally:
            if failed: 
                if not self._skipCleanupOnFailure():
                    self.__cleanup(symlinkSwitched, errorMsg, errorCode)

                self._LOG.warning(errorMsg)
                self._updateStatus(httpStatus = 500, error = errorCode, errorMsg = errorMsg)
            else:
                self._updateProgress(100)

    def __cleanup(self, symlinkSwitched, errorMsg, errorCode):
        """ cleanup if activate is not good """
        self._LOG.info("Start cleanup")
        try:
            if symlinkSwitched:
                self._LOG.info("Deactivate failed manifest (%s, %s)" % (self._service, self._manifest))

                # best effort shutdown
                try:
                    self._execPackages('shutdown', self._service, self._manifest, 81, 90)
                except Exception:
                    pass
        
                # best effort deactivate
                try:
                    self._execPackages('deactivate', self._service, self._manifest, 91, 99)
                except Exception:
                    pass

                # remove symlink only if deactivation successful, this is to leave 
                # symlink for future cleanup if deactivation fail
                self._LOG.debug("Remove active link")
                activePath = self.__getSymlinkPath(self._service)
                self.__removeSymlink(activePath)

        except Exception as exc:
            self._LOG.warning(" Exception while recovery:%s" % exc)

    def __installManifest(self, service, manifest):
        """ install a manifest.  This means calling install on the manifest
        @param service - service of manifest to activate
        @param manifest - manifest to activate
        @param stack - stack for recovery
        """
        self._LOG.debug("Install manifest %s-%s" % (service, manifest))
        if (manifest == None):
            return

        try:
            self._execPackages('install', service, manifest, 1, 10)
        
        finally:
            pass

    def __switchSymlink(self, service, manifest):
        """ remove old symlink and create new one """
        self._LOG.info("Switch active link for %s-%s" % (service, manifest))
        if (manifest == None):
            return

        #remove symlink
        activePath = self.__getSymlinkPath(service)
        self.__removeSymlink(activePath)

        # create the active link
        symlink(manifest, activePath)
        return True

    def __removeSymlink(self, activePath):
        """ remove symlink """
        if os.path.exists(activePath):
            if (os.path.islink(activePath)): # *nix
                os.remove(activePath)
            else:
                raise AgentException('Running platform seems to be neither win32 nor *nix with any (sym)link support. Can\'t proceed with link deletion')

    def __getSymlinkPath(self, service):
        """ return symlink path for a service """
        return manifestutil.manifestPath(service)
