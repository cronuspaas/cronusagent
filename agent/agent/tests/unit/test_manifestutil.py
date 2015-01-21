'''
Created on Oct 9, 2011

@author: biyu
'''
from agent.lib import manifestutil, utils
from agent.tests import TestController
from agent.tests.unit.test_util import commonSetup, commonTearDown,\
    createManifest, activateManifest
import os
import pylons
import json
from agent.lib.manifestutil import packagePath

class TestManifest(TestController):
    """ test manifest """
    
    def setUp(self):
        commonSetup()

    def tearDown(self):
        commonTearDown()
        

    def testUpdateServiceMetaFileLocal(self):
        keys = ['hwPath', 'serverAddress']
        values = manifestutil.readJsonServiceMeta('foo', keys)
        assert values.get('hwPath') == values.get('serverAddress') == None
        createManifest(self, manifest = 'bar', service = 'foo')
        manifestutil.updateServiceMetaFile('foo', {'hwPath':'/env/pool/instance', 'serverAddress':'state.vip'})
        assert os.path.exists(manifestutil.serviceMetadataPath('foo'))
        values = manifestutil.readJsonServiceMeta('foo', keys)
        assert values.get('hwPath') == '/env/pool/instance'
        assert values.get('serverAddress') == 'state.vip'
        manifestutil.updateServiceMetaFile('foo', {'hwPath':None})
        values = manifestutil.readJsonServiceMeta('foo', keys)
        assert values.get('hwPath') is None
        assert values.get('serverAddress') == 'state.vip'

    def testServiceRootPath(self):
        print manifestutil.serviceRootPath()
        assert manifestutil.serviceRootPath() is not None
    
    def testGetServices(self):
        createManifest(self, manifest = 'bar', service = 'foo')
        assert 'foo' in manifestutil.getServices()
        assert manifestutil.servicePath('foo').endswith('foo')

    def testServiceFromPath(self):
        servicepath = manifestutil.servicePath('foo')
        print servicepath, manifestutil.serviceFromPath(servicepath)
        assert 'foo' == manifestutil.serviceFromPath(servicepath)
        servicepath = manifestutil.servicePath('.envfoo.poolbar.machinebaz')
        assert '.envfoo.poolbar.machinebaz' == manifestutil.serviceFromPath(servicepath)
        manifestpath = manifestutil.manifestPath('foo', 'bar')
        assert 'foo' == manifestutil.serviceFromPath(manifestpath)
        manifestpaths = ['somedummypath', manifestpath]
        assert 'foo' == manifestutil.serviceFromPath(manifestpaths)
        
    def testInstalledPkgRootPath(self):
        assert manifestutil.installedPkgRootPath('foo').endswith('foo' + os.path.sep + 'installed-packages')
        
    def testManifestRootPath(self):
        assert manifestutil.manifestRootPath('foo').endswith('foo' + os.path.sep + 'manifests')
        
    def testHasActiveManifest(self):
        createManifest(self, manifest = 'testmanifest', service = 'testservice')
        assert False == manifestutil.hasActiveManifest('testservice')
        activateManifest(self, manifest = 'testmanifest', service = 'testservice')
        assert True == manifestutil.hasActiveManifest('testservice')
        
    def testActiveManifestPath(self):
        createManifest(self)
        activateManifest(self)
        assert manifestutil.activeManifestPath('foo').endswith('bar')
        
    def testManifestPath(self):
        assert manifestutil.manifestPath('foo', 'bar').endswith('foo' + os.path.sep + 'manifests' + os.path.sep + 'bar')
        
    def testPackagesInManifest(self):
        createManifest(self, manifest = 'bar', service = 'foo')
        print manifestutil.packagesInManifest('foo', 'bar')
        assert len(manifestutil.packagesInManifest('foo', 'bar')) > 0
        
    def testPackagePath(self):
        pkgpath = 'foo' + os.path.sep + 'manifests' + os.path.sep + 'bar' + os.path.sep + 'perlserver'
        assert manifestutil.packagePath('foo', 'bar', 'perlserver').endswith(pkgpath)
        
    def testPkgInitConfig(self):
        createManifest(self, manifest = 'bar', service = 'foo')
        activateManifest(self, manifest = 'bar', service = 'foo')
        inifilepath = manifestutil.packagePath('foo', 'bar', 'perlserver') + os.path.sep + 'cronus'
        inifilename = os.path.join(inifilepath, 'cronus.ini')
        uname = pylons.config['app_user_account']
        utils.runsyscmd(utils.sudoCmd('chmod -R ga+w %s' % inifilepath, uname))
        data = {"key":"value","key2":"value2"}
        # test json format
        with open(inifilename, 'w') as propFile:
            json.dump(data, propFile)
        pkgPath = packagePath('foo', 'bar', 'perlserver')
        pkgInitConfig = manifestutil.PkgInitConfig(pkgPath)
        configs = pkgInitConfig.getConfigs()
        assert configs is not None
        assert isinstance(configs, dict)
        print configs
        assert configs['key'] == 'value'
        assert configs['key2'] == 'value2'
        # test eval() format
        with open(inifilename, 'wb+') as fp:
            jsonStr = json.dumps(data)
            fp.write(jsonStr)
            fp.write("\n")

        pkgInitConfig = manifestutil.PkgInitConfig(pkgPath)
        configs = pkgInitConfig.getConfigs()
        assert configs is not None
        assert isinstance(configs, dict)
        print configs
        assert configs['key'] == 'value'
        assert configs['key2'] == 'value2'
        
    def testServiceMetadataPath(self):
        service = '.env.service.instance'
        servicepath = manifestutil.servicePath(service)
        metadatapath = manifestutil.serviceMetadataPath(service)
        assert metadatapath == (servicepath + os.path.sep + '.metadata.json')
        
        

