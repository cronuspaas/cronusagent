#pylint: disable=R0915,C0301,W0105
"""Routes configuration

The more specific and detailed routes should be defined first so they
may take precedent over the more generic routes. For more information
refer to the routes manual at http://routes.groovie.org/docs/
"""
from routes import Mapper

def make_map(config):
    """Create, configure and return the routes Mapper"""
    mapObj = Mapper(directory=config['pylons.paths']['controllers'],
                 always_scan=config['debug'])
    mapObj.minimization = False
    mapObj.explicit = False
    prefix = "/agent"

    # The ErrorController route (handles 404/500 error pages); it should
    # likely stay at the top, ensuring it can always be resolved
    mapObj.connect('/error/{action}', controller='error')
    mapObj.connect('/error/{action}/{id}', controller='error')

    # CUSTOM ROUTES HERE


    # routes for services
    mapObj.connect('/services/', 
                   controller='service', action='listServices',
                   conditions=dict(method=['GET']))
    
    mapObj.connect('/services', 
                   controller='service', action='listServices',
                   conditions=dict(method=['GET']))
    
    mapObj.connect('/services/{service}', 
                   controller='service', action='post',
                   conditions=dict(method=['POST']))
    
    mapObj.connect('/services/{service}', 
                   controller='service', action='delete',
                   conditions=dict(method=['DELETE']))
    
    mapObj.connect('/services/{service}', 
                   controller='service', action='get',
                   conditions=dict(method=['GET']))
    
    mapObj.connect('/services/{service}/action/log',
                   controller='service', action='log',
                   conditions=dict(method=['GET']))
    
    mapObj.connect('/services/{service}/action/updatemetadata',
                   controller='service', action='updateMetadata',
                   conditions=dict(method=['POST']))
    
    mapObj.connect('/services/{service}/action/getmetadata',
                   controller='service', action='getMetadata',
                   conditions=dict(method=['GET']))
    
    mapObj.connect('/services/{service}/action/getmetadataprops',
                   controller='service', action='getMetadataAsProps',
                   conditions=dict(method=['GET']))
    
    mapObj.connect('/services/{service}/action/getmetadatavalue/{name}',
                   controller='service', action='getMetadataValue',
                   conditions=dict(method=['GET']))

    mapObj.connect('/services/{service}/action/listpackages',
                   controller='service', action='listPackages',
                   conditions=dict(method=['GET']))

    # routes for manifests
    mapObj.connect('/services/{service}/manifests/{manifest}',
                   controller='manifest', action='post',
                   conditions=dict(method=['POST']))
    
    mapObj.connect('/services/{service}/manifests/{manifest}',
                   controller='manifest', action='delete',
                   conditions=dict(method=['DELETE']))
    
    mapObj.connect('/services/{service}/manifests/{manifest}',
                   controller='manifest', action='get',
                   conditions=dict(method=['GET']))
    
    mapObj.connect('/services/{service}/manifests/{manifest}/action/log',
                   controller='manifest', action='log',
                   conditions=dict(method=['GET']))

    mapObj.connect('/services/{service}/manifests/{manifest}/action/activate',
                   controller='manifest', action='activate',
                   conditions=dict(method=['POST']))
    
    # routes for distribution client
    mapObj.connect('/services/dist/startdownload',
                   controller='distribution', action='startdownload',
                   conditions=dict(method=['POST']))
    
    mapObj.connect('/services/dist/validatepackage',
                   controller='distribution', action='validatePackage',
                   conditions=dict(method=['POST']))
    
    mapObj.connect('/services/dist/listpackages',
                   controller='distribution', action='listPackages',
                   conditions=dict(method=['GET']))
    
    mapObj.connect('/services/dist/uploadpackage',
                   controller='distribution', action='uploadPackage',
                   conditions=dict(method=['POST']))
    
    mapObj.connect('/services/dist/{package}',
                   controller='distribution', action='deletePackage',
                   conditions=dict(method=['DELETE']))

    # routes for status
    mapObj.connect('/status/done', 
                   controller='status', action='done',
                   conditions=dict(method=['GET']))
    
    mapObj.connect('/status/{uuid}', 
                   controller='status', action='get',
                   conditions=dict(method=['GET']))
    
    mapObj.connect('/status/{uuid}', 
                   controller='status', action='delete',
                   conditions=dict(method=['DELETE']))

    mapObj.connect('/status/uuidoutput/{uuid}',
                   controller='status', action='getUuidOutput',
                   conditions=dict(method=['GET']))

    mapObj.connect('/status/guidoutput/{guid}',
                   controller='status', action='getGuidOutput',
                   conditions=dict(method=['GET']))

    #validate internals
    mapObj.connect(prefix + '/logs', 
                   controller='validate_internals', action='getLogDirectory',
                   conditions=dict(method=['GET']))
    
    mapObj.connect(prefix + '/logs/{fileName}', 
                   controller='validate_internals', action='getLogFile',
                   conditions=dict(method=['GET']))
    
    mapObj.connect(prefix + '/pkgs', 
                   controller='validate_internals', action='getPkgUploadPage',
                   conditions=dict(method=['GET']))

    mapObj.connect(prefix, 
                   controller='validate_internals', action='getInfo', isHtml = 'True',
                   conditions=dict(method=['GET']))
    
    mapObj.connect(prefix + '/ValidateInternals', 
                   controller='validate_internals', action='getInfo', isHtml = 'False',
                   conditions=dict(method=['GET']))
    
    mapObj.connect(prefix + '/ValidateInternals.html', 
                   controller='validate_internals', action='getInfo', isHtml = 'True',
                   conditions=dict(method=['GET']))
    
    mapObj.connect(prefix + '/agenthealth', 
                   controller='validate_internals', action='getAgentHealth',
                   conditions=dict(method=['GET']))
    
    mapObj.connect(prefix + '/monitors', 
                   controller='validate_internals', action='getMonitors',
                   conditions=dict(method=['GET']))
    
    mapObj.connect(prefix + '/threads', 
                   controller='validate_internals', action='getThreads',
                   conditions=dict(method=['GET']))

    # routes for log
    mapObj.connect('/applog/applog', 
                   controller='applog', action='listAppLog',
                   conditions=dict(method=['GET']))
    
    mapObj.connect('/applog/packages', 
                   controller='applog', action='listPackages',
                   conditions=dict(method=['GET']))
    
    mapObj.connect('/applog/services', 
                   controller='applog', action='listServices',
                   conditions=dict(method=['GET']))
    
    mapObj.connect('/applog/manifests', 
                   controller='applog', action='listManifests',
                   conditions=dict(method=['GET']))

    # routes for service actions
    mapObj.connect('/services/{service}/action/restart',
                   controller='action', action='restart',
                   conditions=dict(method=['POST']))
    
    mapObj.connect('/services/{service}/action/reset',
                   controller='action', action='reset',
                   conditions=dict(method=['POST']))
    
    mapObj.connect('/services/{service}/action/startup',
                   controller='action', action='startup',
                   conditions=dict(method=['POST']))
    
    mapObj.connect('/services/{service}/action/shutdown',
                   controller='action', action='shutdown',
                   conditions=dict(method=['POST']))
    
    mapObj.connect('/services/{service}/useraction/{useraction}',
                   controller='action', action='useraction',
                   conditions=dict(method=['POST']))

    mapObj.connect('/services/{service}/action/deactivatemanifest',
                   controller='action', action='deactivatemanifest',
                   conditions=dict(method=['POST']))
    
    mapObj.connect('/services/{service}/action/deploy',
                   controller='action', action='deployservice',
                   conditions=dict(method=['POST']))
    
    mapObj.connect('/services/{service}/action/rollback',
                   controller='action', action='rollbackservice',
                   conditions=dict(method=['POST']))

    mapObj.connect('/services/{service}/action/cleanup',
                   controller='action', action='cleanupservice',
                   conditions=dict(method=['DELETE']))

    mapObj.connect('/services/{service}/action/sendmonwres/{resSec}',
                   controller='action', action='sendMetrics',
                   conditions=dict(method=['POST']))

    mapObj.connect('/services/{service}/action/sendmonwres/{resSec}/{monitorgroup}',
                   controller='action', action='sendMetrics',
                   conditions=dict(method=['POST']))
    
    #routes for cleanup services
    mapObj.connect(prefix + '/cleanup',
               controller='cleanup', action='post',
               conditions=dict(method=['POST']))

    mapObj.connect('/cleanup/{package}',
                   controller='cleanup', action='deleteCronusPackage',
                   conditions=dict(method=['DELETE']))


    #routes for agent actions
    mapObj.connect(prefix + '/shutdown',
                   controller='agentaction', action='shutdown',
                   conditions=dict(method=['POST']))
    
    mapObj.connect(prefix + '/safeshutdown',
                   controller='agentaction', action='safeshutdown',
                   conditions=dict(method=['POST']))
    
    mapObj.connect(prefix + '/reloadmonitors',
                   controller='agentaction', action='reloadmonitors',
                   conditions=dict(method=['POST']))
    
    mapObj.connect(prefix + '/selfupdate',
                   controller='agentaction', action='selfupdate',
                   conditions=dict(method=['POST']))

    mapObj.connect(prefix + '/selfupdate',
                   controller='agentaction', action='cancelSelfUpdate',
                   conditions=dict(method=['DELETE']))
    
    mapObj.connect(prefix + '/config',
                   controller='agentaction', action='getConfig',
                   conditions=dict(method=['GET']))
    
    mapObj.connect(prefix + '/config',
                   controller='agentaction', action='pokeConfig',
                   conditions=dict(method=['POST']))
    
    mapObj.connect(prefix + '/config',
                   controller='agentaction', action='cleanConfig',
                   conditions=dict(method=['DELETE']))
    
    mapObj.connect(prefix + '/cleanproc',
                   controller='cleanup', action='cleanupProcess',
                   conditions=dict(method=['POST']))
    
    mapObj.connect(prefix + '/gettaskslareport/{task}/{threshold}/{starttime}/{fmt}',
                   controller='agentaction', action='getTaskSlaReport',
                   conditions=dict(method=['GET']))
    
    mapObj.connect(prefix + '/api',
                   controller='agentaction', action='getRoutes',
                   conditions=dict(method=['GET']))

    mapObj.connect(prefix + '/dumpmemory',
                   controller='agentaction', action='dumpMemory',
                   conditions=dict(method=['POST']))
    
    mapObj.connect(prefix + '/sizeofmgrs',
                   controller='agentaction', action='getSizeOfMgrs',
                   conditions=dict(method=['GET']))

    mapObj.connect(prefix + '/gc',
                   controller='agentaction', action='runAgentGc',
                   conditions=dict(method=['POST']))

    mapObj.connect(prefix + '/servicesinfo', 
                   controller='service', action='getServicesSummary',
                   conditions=dict(method=['GET']))
    
    # plug-able modules
    mapObj.connect(prefix + '/modules', 
                   controller='module', action='listModules',
                   conditions=dict(method=['GET']))
    
    mapObj.connect(prefix + '/modules/{module}', 
                   controller='module', action='get',
                   conditions=dict(method=['GET']))
    
    mapObj.connect(prefix + '/modules/{module}', 
                   controller='module', action='post',
                   conditions=dict(method=['POST']))
    
    mapObj.connect(prefix + '/modules/{module}', 
                   controller='module', action='delete',
                   conditions=dict(method=['DELETE']))

    
    # command and control
    mapObj.connect('/admin/executeScript',
                   controller='admin', action='executeScript',
                   conditions=dict(method=['POST']))

    mapObj.connect('/admin/executeCmd',
                   controller='admin', action='executeCmd',
                   conditions=dict(method=['POST']))

    # security
    mapObj.connect('/security/listkeys',
                   controller='admin', action='listKeys',
                   conditions=dict(method=['GET']))
    
    mapObj.connect('/security/key/{key}',
                   controller='admin', action='addKey',
                   conditions=dict(method=['POST']))
    
    mapObj.connect('/security/key/{key}',
                   controller='admin', action='removeKey',
                   conditions=dict(method=['DELETE']))
    
    mapObj.connect('security/validatetoken',
                   controller='admin', action='validateToken',
                   conditions=dict(method=['POST']))

    mapObj.connect('/security/validatetoken',
                   controller='admin', action='validateToken',
                   conditions=dict(method=['POST']))
    
    mapObj.connect('/security/updateAgentCert',
                   controller='admin', action='updateAgentCert',
                   conditions=dict(method=['POST']))

    mapObj.connect('/security/updateAgentPwd',
                   controller='admin', action='updateAgentPwd',
                   conditions=dict(method=['POST']))

    mapObj.connect('/{controller}/{action}')
    mapObj.connect('/{controller}/{action}/{id}')

    return mapObj
