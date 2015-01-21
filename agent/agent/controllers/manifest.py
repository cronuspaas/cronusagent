# pylint: disable=W0703, W0141,R0914,R0911,W0105
""" manifest lifecycle """
from agent.lib.base import BaseController
from agent.lib.result import doneResult
from agent.lib.result import errorResult
from agent.lib.result import statusResult
from agent.lib.utils import readlink, trackable
from agent.lib.errors import Errors
from agent.lib.errors import AgentException
from agent.lib import manifestutil, serviceutil
from agent.controllers.applog import ApplogController
from agent.lib.agent_thread.manifest_delete import ManifestDelete
from agent.lib.security.agentauth import authorize

from pylons import request, response, config
import glob
import os
import json
import logging
import traceback

LOG = logging.getLogger(__name__)

class ManifestController(BaseController):
    """ Manifest Controller Class """

    @authorize()
    @trackable()
    def post(self, service, manifest):
        """ Create a new service object """
        from agent.lib.agent_thread.manifest_create import ManifestCreate

        try:

            LOG.info('Post for service (%s) and manifest (%s) with body: %s',
                      service, manifest, request.body)

            serviceutil.createServiceIfNeeded(service)

            # check to see if the manifest already exists
            path = manifestutil.manifestPath(service, manifest)
            if (os.path.isdir(path)):
                return doneResult(request, response, httpStatus=201, controller=self)

            # parse the body
            if (request.body == ""):
                return errorResult(request, response, Errors.MANIFEST_PACKAGE_PARSING_ERROR,
                                   'No body found in post command',
                                   controller=self)

            body = json.loads(request.body)

            packages = body['package']
            forcedPackages = body['forcePackageName'] if 'forcePackageName' in body else None

            LOG.debug('pkgs = %s, %s', packages, forcedPackages)

            # parse the package list
            for idx, package in enumerate(packages):
                # to support reuse of an package from an existing manifest (active if possible)
                # without sending the complete package location in request body
                if package.startswith('/'):
                    packageRef = package
                    tokens = package.split('/')
                    pkgnamePrefix = tokens[-1].rstrip()
                    fullPkgLoc = manifestutil.getPackageFullLocByName(service, manifest=None, pkgnamePrefix=pkgnamePrefix)
                    if fullPkgLoc is None:
                        return errorResult(request, response, Errors.MANIFEST_PACKAGE_DOES_NOT_EXIST,
                                           'manifest (%s/%s) package (%s) does not exist' % 
                                           (service, manifest, packages), controller=self)
                    else:
                        LOG.info('expanding package reuse ref %s with full package location %s' % (packageRef, fullPkgLoc))
                        packages[idx] = fullPkgLoc

            appGlobal = config['pylons.app_globals']
            
            # start a thread to create the package
            manThread = ManifestCreate(appGlobal.threadMgr, service, manifest, packages, forcePackages=forcedPackages)
            self.injectJobCtx(manThread)
            manThread.start()
            manThread.threadMgrEvent.wait()

            return statusResult(request, response, manThread, controller=self)
        
        except AgentException as excep:
            return errorResult(request, response, error=excep.getCode(), errorMsg=excep.getMsg(), controller=self)
        
        except Exception as excep:
            return errorResult(request, response, error=Errors.UNKNOWN_ERROR,
                               errorMsg='Unknown error for activateManifest(%s/%s) - %s - %s' % 
                               (service, manifest, str(excep), traceback.format_exc(2)),
                               controller=self)

    @authorize()
    @trackable()
    def delete(self, service, manifest):
        """ Delete a new service object """
        try:
            path = manifestutil.manifestPath(service, manifest)
            if (not os.path.isdir(path)):
                return errorResult(request, response, Errors.MANIFEST_NOT_FOUND,
                                   'manifest (%s/%s) missing service' % (service, manifest),
                                   controller=self)

            # first check that this isn't the active manifest
            path = manifestutil.manifestPath(service)
            if (os.path.exists(path)):
                activePath = os.path.basename(readlink(path))
                deletePath = os.path.basename(manifestutil.manifestPath(service, manifest))

                if (activePath == deletePath):
                    return errorResult(request, response, Errors.MANIFEST_DELETING_ACTIVE_MANIFEST,
                                       'Manifest(%s, %s) attempting to delete active manifest'
                                       % (service, manifest),
                                       controller=self)

            # now try to delete the manifest directory
            appGlobal = config['pylons.app_globals']
            manThread = ManifestDelete(appGlobal.threadMgr, service, manifest)
            self.injectJobCtx(manThread)
            manThread.start()
            manThread.threadMgrEvent.wait()

            return statusResult(request, response, manThread, controller=self)

        except Exception as excep:
            return errorResult(request, response, error=Errors.UNKNOWN_ERROR,
                               errorMsg='Unknown error for delete manifest(%s/%s) - %s - %s' % 
                               (service, manifest, str(excep), traceback.format_exc(2)),
                               controller=self)

    @trackable()
    def get(self, service, manifest):
        """ Get a new service object """
        LOG.info('Get for service (%s) and manifest (%s)', service, manifest)

        try:
            # first check that the manifest directory exists
            path = manifestutil.manifestPath(service, manifest)
            if (not os.path.isdir(path)):
                return errorResult(request, response, Errors.MANIFEST_NOT_FOUND,
                                   'manifest (%s/%s) missing service' % (service, manifest),
                                   controller=self)

            # now go through the list of packages in the manifest
            packages = []
            packageLinkNames = glob.glob(os.path.join(manifestutil.manifestPath(service, manifest), '*'))
            for packageLink in packageLinkNames:

                package = readlink(packageLink)

                LOG.debug('Get package (%s) in manifest (%s)', package, manifest)

                # deal with the case where the package has a / or \ (for windoz) at the end
                package = package.rstrip('/')
                package = package.rstrip('\\')

                # the name of the package can be constructed from the last two path components
                (head, version) = os.path.split(package)
                (head, name) = os.path.split(head)

                LOG.debug('Add package %s-%s.cronus' % (name, version))
                packages.append('%s-%s.cronus' % (name, version))

        except OSError as excp:
            return errorResult(request, response, Errors.MANIFEST_PATH_ERROR,
                               'Manifest(%s, %s) path error: %s' % (service, manifest, str(excp)),
                               controller=self)

        return doneResult(request, response, result=packages, controller=self)


    @authorize()
    @trackable()
    def activate(self, service, manifest):
        """ activate manifest, if already active then skip """
        from agent.lib.agent_thread.activate_manifest import ActivateManifest
        LOG.info('activateManifest for service(%s) with body: %s', service, request.body)
        try:
            appGlobal = config['pylons.app_globals']
            
            if manifestutil.getActiveManifest(service) == manifest:
                return doneResult(request, response, controller=self)
            
            else:
                if request.body:
                    pushedData = json.loads(request.body)
                    serviceutil.updateLcmMeta(service, pushedData)
                    
                mf_path = os.path.join(manifestutil.manifestPath(service, manifest))
                if (not os.path.exists(mf_path)):
                    return errorResult(request, response, Errors.ACTIVEMANIFEST_MANIFEST_MISSING,
                                   'Manifest(%s, %s) path missing' % (service, manifest),
                                   controller=self)
                LOG.debug('Manifest path exists: %s' % (mf_path))
                activateThread = ActivateManifest(appGlobal.threadMgr, service, manifest,
                                                  action=ActivateManifest.ACTION_ACTIVATION)
                self.injectJobCtx(activateThread)
                activateThread.start()
                activateThread.threadMgrEvent.wait()

            return statusResult(request, response, activateThread, controller=self)

        except Exception as excep:
            msg = 'Unknown error for activateManifest(%s/%s) - %s - %s' % (service, manifest, str(excep), traceback.format_exc(2))
            return errorResult(request, response, error=Errors.UNKNOWN_ERROR,
                               errorMsg=msg, controller=self)

    @trackable()
    def log(self, service, manifest):
        """ Get manifest logs """
        LOG.info('Get for service (%s) and manifest (%s)', service, manifest)

        try:
            # first check that the manifest directory exists
            path = manifestutil.manifestPath(service, manifest)
            if (not os.path.isdir(path)):
                return errorResult(request, response, Errors.MANIFEST_NOT_FOUND,
                                   'manifest (%s/%s) missing service' % (service, manifest),
                                   controller=self)
            packageList = manifestutil.packagesInManifest(service, manifest)
            return ApplogController.prepareOutput(packageList, ("/log/list/applog?service=%s&manifest=%s&package=" % (service, manifest)), manifestutil.manifestPath(service), "List Of Packages")
        except OSError as excp:
            return errorResult(request, response, Errors.MANIFEST_PATH_ERROR,
                               'Manifest(%s, %s) path error: %s' % (service, manifest, str(excp)),
                               controller=self)
            

