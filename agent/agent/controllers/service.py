#pylint: disable=W0703,W0106,W0612,R0904,R0914,W0105
""" Service Controller """

from agent.controllers.applog import ApplogController
from agent.lib import manifestutil, utils, serviceutil
from agent.lib.base import BaseController
from agent.lib.errors import Errors
from agent.lib.result import doneResult, errorResult, statusResult
from agent.lib.security.agentauth import authorize
from agent.lib.utils import readlink, trackable
from pylons import request, response, config
import json
import logging
import os
import pylons
import shutil
import time
import traceback


LOG = logging.getLogger(__name__)

class ServiceController(BaseController):
    """ Service Controller Class.  This class handles all service rest calls. """
    
    @authorize()
    @trackable()
    def getServicesSummary(self):
        """ service summary, all about service in one call """
        try:
            services_data = serviceutil.getServiceSummary()
            return  doneResult(request, response, result = services_data, controller = self)
        except Exception as excep:
            return errorResult(request, response, error = Errors.UNKNOWN_ERROR,
                               errorMsg = 'Unknown error when get services summary %s - %s' %
                               (str(excep), traceback.format_exc(2)),
                               controller = self)
        

    @trackable()
    def listServices(self):
        """ list all the services in the agent """
        try:
            services = ServiceController.getServices()
            return  doneResult(request, response, result = services, controller = self)
        except Exception as excep:
            return errorResult(request, response, error = Errors.UNKNOWN_ERROR,
                               errorMsg = 'Unknown error when listing services %s - %s' %
                               (str(excep), traceback.format_exc(2)),
                               controller = self)

    @authorize()
    @trackable()
    def post(self, service):
        """ Create a new service object """
        try:

            path = ServiceController.servicePath(service)

            # skip if the path already exists
            if os.path.exists(path) and os.path.isdir(path):
                return doneResult(request, response, httpStatus = 201, result = service, controller = self)
            else:
                serviceutil.createServiceIfNeeded(service)

            # save metadata from payload if any
            if request.body:
                lcm_meta = json.loads(request.body)
                serviceutil.updateLcmMeta(service, lcm_meta)

            return doneResult(request, response, result = service, controller = self)

        except OSError:
            return errorResult(request, response, Errors.SERVICE_EXISTS,
                               "Service(%s) already exists(or %s)" % (service, traceback.format_exc(2)),
                               controller = self)
        except Exception as excep:
            return errorResult(request, response, error = Errors.UNKNOWN_ERROR,
                               errorMsg = 'Unknown error when posting services %s - %s' %
                               (str(excep), traceback.format_exc(2)),
                               controller = self)

    @authorize()
    @trackable()
    def delete(self, service):
        """ Delete a new service object """
        from agent.lib.agent_thread.service_delete import ServiceDelete
        try:
            LOG.info('Got a delete request for service ' + service)

            path = ServiceController.servicePath(service)

            if (not os.path.exists(path) and not os.path.isdir(path)):
                return errorResult(request, response, Errors.SERVICE_NOT_FOUND, "No service(%s) found" % service, controller = self)

            # see if active manifest exist for the service
            if manifestutil.hasActiveManifest(service):
                return errorResult(request, response, Errors.MANIFEST_DELETING_ACTIVE_MANIFEST,
                                   'Active manifest exists for service %s, deactivate the manifest first before deleting service' % (service),
                                   controller = self)

            # start the delete thread
            appGlobal = config['pylons.app_globals']
            deleteThread = ServiceDelete(appGlobal.threadMgr, service, path)
            self.injectJobCtx(deleteThread)
            deleteThread.start()
            deleteThread.threadMgrEvent.wait()

            return statusResult(request, response, deleteThread, controller = self)
        except Exception as excep:
            return errorResult(request, response, error = Errors.UNKNOWN_ERROR,
                               errorMsg = 'Unknown error when deleting service(%s) %s - %s' %
                               (service, str(excep), traceback.format_exc(2)),
                               controller = self)

    @trackable()
    def get(self, service):
        """ Get a new service object """
        try:
            from agent.lib.agent_thread.manifest_create import ManifestCreate

            # make sure the service path exists
            path = ServiceController.servicePath(service)
            if (not os.path.exists(path)):
                return errorResult(request, response, error = Errors.SERVICE_NOT_FOUND,
                                   errorMsg = 'Unable to find service (%s)' % service,
                                   controller = self)

            path = ServiceController.manifestPath(service)

            activeManifest = None
            manifestList = []
            for manifest in os.listdir(path):
                if (ManifestCreate.isInProgress(manifest)):
                    continue

                manifestPath = os.path.join(path, manifest)
                if (manifest == 'active'):
                    activeLink = readlink(manifestPath)

                    if (activeLink == None):
                        manifestList.append(manifest)
                    else:
                        activeManifest = os.path.basename(activeLink)
                else:
                    manifestList.append(manifest)

            result = {}
            manifestList.sort()
            result['manifest'] = manifestList
            result['activemanifest'] = activeManifest

            return  doneResult(request, response, result = result, controller = self)

        except Exception as excep:
            return errorResult(request, response, error = Errors.UNKNOWN_ERROR,
                               errorMsg = 'Unknown error when getting service (%s) %s - %s' %
                               (service, str(excep), traceback.format_exc(2)),
                               controller = self)

    @trackable()
    def log(self, service):
        """ Get service logs """
        if (service == ''):
            return errorResult(request, response, Errors.LOG_PARAM_REQUIRED,
                'Missing service', controller = self)
        if (not os.path.isdir(manifestutil.manifestPath(service))):
            return errorResult(request, response, Errors.SERVICE_NOT_FOUND,
                'Service specified is not found', controller = self)
        packageList = manifestutil.packagesInManifest(service)
        return ApplogController.prepareOutput(packageList, "/log/list/applog?service=" + service + "&package=", manifestutil.manifestPath(service), "List Of Packages")

    @authorize()
    @trackable()
    def updateMetadata(self, service):
        """ create or update .metadata file for a service """
        # now connect to state server to store metadata for the service in .metadata
        metadata = None
        if request.body:
            # two flavor of updatemetadata call, one with body, one without
            body = json.loads(request.body)
            if 'metadata' in body:
                metadata = body['metadata']

        try:
            result = {}
            
            appGlobal = pylons.config['pylons.app_globals']

            if metadata is not None and 'monitoring.metric.tags' in metadata:
                appGlobal.agentMonitor.reloadMonitors()
            
            result = manifestutil.updateServiceMetaFile(service, metadata)
            
            return doneResult(request, response, result = result, controller = self)

        except Exception as excep:
            return errorResult(request, response, error = Errors.UNKNOWN_ERROR,
                               errorMsg = 'Unknown error when update service metadata (%s) %s - %s' %
                               (service, str(excep), traceback.format_exc(2)),
                               controller = self)

    @trackable()
    def getMetadata(self, service):
        """ get .metadata file for a service """
        try:
            result = manifestutil.readJsonServiceMeta(service)
            return doneResult(request, response, result = result, controller = self)

        except Exception as excep:
            return errorResult(request, response, error = Errors.UNKNOWN_ERROR,
                               errorMsg = 'Unknown error get service metadata (%s) %s - %s' %
                               (service, str(excep), traceback.format_exc(2)),
                               controller = self)
            
    
    @trackable()
    def getMetadataAsProps(self, service):
        """ get .metadata file for a service as property file, 
            kvp: name=value, 
            array: name=v1,v2,v3, 
            dict: name1.name2=value etc.
        """
        try:
            result = manifestutil.readJsonServiceMeta(service)
            response.content_type = 'text/plain'
            return utils.nestedDictStr(result)        

        except Exception as excep:
            return errorResult(request, response, error = Errors.UNKNOWN_ERROR,
                               errorMsg = 'Unknown error get service metadata (%s) %s - %s' %
                               (service, str(excep), traceback.format_exc(2)),
                               controller = self)

    @trackable()
    def getMetadataValue(self, service, name):
        """ get .metadata file for a service as property file, 
            kvp: name=value, 
            array: name=v1,v2,v3, 
            dict: name1.name2=value etc.
        """
        try:
            result = manifestutil.readJsonServiceMeta(service)
            response.content_type = 'text/plain'
            return result[name] if name in result else ''        

        except Exception as excep:
            return errorResult(request, response, error = Errors.UNKNOWN_ERROR,
                               errorMsg = 'Unknown error get service metadata (%s) %s - %s' %
                               (service, str(excep), traceback.format_exc(2)),
                               controller = self)

    @trackable()
    def listPackages(self, service):
        """ list installed packages in this service"""
        result = {}
        installedRoot = manifestutil.installedPkgRootPath(service)
        pkgs = [ packageDir for packageDir in os.listdir(installedRoot) ]
        pkgsVersions = []
        for pkg in pkgs:
            pkgVersions = {}
            pkgVersions['pkgName'] = os.path.basename(pkg)
            pkgVersions['pkgVersion'] = [ os.path.basename(verDir) for verDir in os.listdir(os.path.join(installedRoot, pkg)) ]
            pkgsVersions.append(pkgVersions)

        result['packages'] = pkgsVersions
        return doneResult(request, response, result = result, controller = self)


    #####################################################
    # utility members
    #####################################################

    @staticmethod
    def serviceRootPath():
        """ compute the path to this service node root """
        return os.path.realpath(os.path.join(config['agent_root'], 'service_nodes'))

    @staticmethod
    def servicePath(service):
        """ compute the path to this service node """
        return os.path.join(ServiceController.serviceRootPath(), service)

    @staticmethod
    def installedPkgPath(service):
        """ compute the path to this service installed packages path """
        return os.path.join(ServiceController.servicePath(service), 'installed-packages')

    @staticmethod
    def manifestPath(service):
        """ compute the path to this service manifest path """
        return os.path.join(ServiceController.servicePath(service), 'manifests')

    @staticmethod
    def streamsRootPath(service):
        """ compute the path to streams folder in this service """
        return os.path.join(ServiceController.servicePath(service), 'streams')
    @staticmethod
    def downloadedPkgPath(service):
        """ compute the path to downloaded-packages in this service.
            this folder is to keep track or untarred packages in install_folder/cronus/software/packages folder
        """
        return os.path.join(ServiceController.servicePath(service), 'downloaded-packages')

    @staticmethod
    def serviceCat(service):
        """ compute the path to this service manifest path """
        return 'Service/%s' % service

    @staticmethod
    def getServices():
        """ return the list of services under this agent """
        path = ServiceController.serviceRootPath()
        dirs = os.listdir(path)
        dirs.sort()
        return dirs

    @staticmethod
    def cleanupServices():
        """
        for all services clean up partially completed manifests
        This should only be called during startup.
        """
        from agent.lib.agent_thread.manifest_create import ManifestCreate

        try:
            services = ServiceController.getServices()
            for service in services:
                manPath = ServiceController.manifestPath(service)
                manifestPaths = [os.path.join(manPath, path) for path in os.listdir(manPath)]

                [shutil.rmtree(manifestPath) for manifestPath in manifestPaths
                 if ManifestCreate.isInProgress(os.path.basename(manifestPath))]

        except OSError:
            pass


    @staticmethod
    def startServicesOnAgentStartup():
        """
        when agent is restarted,
        0. check for agent selfupdate
        1. start all service with active manifest, this requires service startup script be idempotent
        2. load dynamic controllers and routes if any
        """
        # check for agent update
        from agent.lib.agenthealth import checkAgentVersion
        checkAgentVersion(True)

        # startup services
        from agent.lib.agent_thread.startstop_service import StartStopService
        appGlobal = config['pylons.app_globals']
        appdelay = int(config['app_restart_init_delay']) if 'app_restart_init_delay' in config else 0
        if appdelay > 0:
            time.sleep(appdelay)
            
        # check if this is agent restart or system restart
        if os.path.exists("/proc/uptime"):
            uptime, _ = [float(f) for f in open("/proc/uptime").read().split()]
        else:
            uptime = 500

        systemRestartTimeThreshold = pylons.config['system_restart_time_threshold']
        if (int(systemRestartTimeThreshold) <= uptime):
            LOG.info('agent recover from agent restart, not goint to restart managed apps')
            return
            
        LOG.info('agent recover from system reboot, restart all managed apps')
        for service in manifestutil.getServices():
            if service != 'agent':
                if manifestutil.hasActiveManifest(service):
                    try:
                        LOG.info('startup for service(%s)', service)

                        startupThread = StartStopService(appGlobal.threadMgr, service, StartStopService.ACTION_STARTUP)
                        startupThread.start()
                        startupThread.threadMgrEvent.wait()

                    except Exception as excep:
                        LOG.error('Unknown error starting service(%s) - %s - %s' % (service, str(excep), traceback.format_exc(2)))
