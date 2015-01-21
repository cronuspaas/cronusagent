from agent.tests import *
from agent.lib.packagemgr import PackageMgr
from agent.lib.package import PackageUtil, PackageControl
from agent.lib.errors import AgentException, PackageScriptNotFound
import logging
import pylons
import time
import os

from agent.lib.agent_globals import stopAgentGlobals
from agent.lib.agent_globals import startAgentGlobals
from agent.tests.unit.test_util import commonSetup
from agent.tests.unit.test_util import commonTearDown

import urlgrabber
from agent.lib import configutil, utils, manifestutil

LOG = logging.getLogger(__name__)

class TestPackage(TestController):

    def setUp(self):
        commonSetup()

        self.testPkgUri = 'http://github.com/yubin154/cronusagent/blob/master/agent/agent/tests/unit/packages/perlserver-1.1.0.unix.cronus'
        self.localPkgName = os.path.join(PackageMgr.packagePath(), 'perlserver-1.1.0.unix.cronus')
        self.threadMgr = pylons.config['pylons.app_globals'].threadMgr
        appGlobals = pylons.config['pylons.app_globals']
        appGlobals.packageMgr.stop()

    def tearDown(self):
        commonTearDown()

    def test_parsing_garbage(self):
        # test the url parsing

        try:
            PackageUtil.parseUri('asdfawert892375[jrgjhnjbuy43w5897t^!R$#W_R(@$^(_#$(', PackageMgr.packagePath())
            assert False, 'parse garbage'
        except AgentException:
            pass

    def test_parsing_good_url(self):
        # test good url
        uri = 'http://me:password@foo.com:8080/repo/agent-0.1.2.unix.cronus?query=blah#foo'
        uriDict = PackageUtil.parseUri(uri, PackageMgr.packagePath())
        assert uriDict['uri'] == uri
        assert uriDict['scheme'] == 'http'
        assert uriDict['uripath'] == '/repo/agent-0.1.2.unix.cronus'
        assert uriDict['package'] == 'agent-0.1.2.unix.cronus'
        assert uriDict['packageNameVersion'] == 'agent-0.1.2.unix'
        assert uriDict['packageName'] == 'agent'
        assert uriDict['packageVersion'] == '0.1.2.unix'
        assert uriDict['packageVersionMajor'] == '0'
        assert uriDict['packageVersionMinor'] == '1'
        assert uriDict['packageVersionBuild'] == '2'
        assert uriDict['packagePlat'] == 'unix'
        assert uriDict['propName'] == 'agent-0.1.2.unix.cronus.prop'
        assert uriDict['propUri'] == 'http://me:password@foo.com:8080/repo/agent-0.1.2.unix.cronus.prop?query=blah#foo'
        assert uriDict['packagePath'] == os.path.join(PackageMgr.packagePath(), 'agent-0.1.2.unix.cronus')
        assert uriDict['inProgressPackagePath'] == os.path.join(PackageMgr.packagePath(), 'agent-0.1.2.unix.cronus.inprogress')
        assert uriDict['propPath'] == os.path.join(PackageMgr.packagePath(), 'agent-0.1.2.unix.cronus.prop')
#         assert uriDict['torrentUri'] == 'http://me:password@foo.com:8080/repo/agent-0.1.2.unix.cronus.torrent?query=blah#foo'
#         assert uriDict['torrentPath'] == os.path.join(PackageMgr.packagePath(), 'agent-0.1.2.unix.cronus.torrent')
#         assert uriDict['torrentName'] == 'agent-0.1.2.unix.cronus.torrent'

    def test_parsing_bad_scheme(self):
        # test bad scheme
        try:
            PackageUtil.parseUri('asdfe://foo.com/repo/agent-0.1.1.unix.cronus', PackageMgr.packagePath())
            assert False, 'bad scheme'
        except AgentException:
            pass

    def test_parsing_bad_name(self):
        # test bad name
        try:
            PackageUtil.parseUri('http://foo.com/repo/a?gent-0.1.1.unix.cronus', PackageMgr.packagePath())
            assert False, 'bad name'
        except AgentException:
            pass

    def test_parsing_bad_version(self):
        # test bad version
        try:
            PackageUtil.parseUri('http://foo.com/repo/agent-0.1.1a.cronus', PackageMgr.packagePath())
            assert False, 'bad name'
        except AgentException:
            pass

    def test_parsing_bad_extension(self):
        # test bad extension
        try:
            PackageUtil.parseUri('http://foo.com/repo/agent-0.1.1a.cronus2', PackageMgr.packagePath())
            assert False, 'bad extension'
        except AgentException:
            pass


    def downloadPackage(self):

        # download the package
        urlgrabber.urlgrab(self.testPkgUri, self.localPkgName)
        urlgrabber.urlgrab(self.testPkgUri + '.prop', self.localPkgName + '.prop')

        LOG.debug('localpackagename = %s', self.localPkgName)
        assert os.path.exists(self.localPkgName + '.prop')
        assert os.path.exists(self.localPkgName)

    def test_packageRun3(self):
        # test large package
        pass

    def test_multiplePackages(self):
        # test downloading multiple package
        pass


    def test_cleanupPackages(self):
        stopAgentGlobals()

        # ok now let's create the directory structure of a bad service and packages
        packagePath = PackageMgr.packagePath()
        inProgPackage2 = os.path.join(packagePath, 'bar.inprogress')
        inProgPackage1 = os.path.join(packagePath, 'foo.inprogress')
        goodPackage1 = os.path.join(packagePath, 'baz')
        goodPackage2 = os.path.join(packagePath, 'baz')

        open(inProgPackage1, 'w').close()
        open(inProgPackage2, 'w').close()
        open(goodPackage1, 'w').close()
        open(goodPackage2, 'w').close()

        startAgentGlobals()
        # we remove logic of inprogress file cleanup from packagemgr
#        assert not os.path.exists(inProgPackage1)
#        assert not os.path.exists(inProgPackage2)

        assert os.path.exists(goodPackage1)
        assert os.path.exists(goodPackage2)

    def test_hasScript(self):
        package = PackageControl(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'packages', 'perlserver-1.0.0.unix'), self.threadMgr)

        self.assertTrue(package.hasScript('activate'))
        self.assertFalse(package.hasScript('install'))

    def test_packageControlRunScriptMissingScript(self):
        package = PackageControl(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'packages', 'running_package-0.0.1.unix'), self.threadMgr)
        try:
            package.runScript('foo', 10, 10)
        except PackageScriptNotFound:
            pass

    def test_getAllInstalledPackages(self):
        from agent.tests.unit.test_util import createManifest

        serviceName = 'service1'
        manifestName = 'manifestA'

        try:
            createManifest(self, packages = ["http://github.com/yubin154/cronusagent/blob/master/agent/agent/tests/unit/packages/pkgA-1.2.0.unix.cronus",
                                  "http://github.com/yubin154/cronusagent/blob/master/agent/agent/tests/unit/packages/pkgB-0.6.0.unix.cronus"],
                                  service = serviceName, manifest = manifestName)

        except Exception as ex:
            print 'exception thrown during mf %s' % str(ex)
        time.sleep(2)
        installedPkgPath = os.path.join(manifestutil.servicePath(serviceName), 'installed-packages')
        pkgs = PackageUtil.getAllInstalledPackages(installedPkgPath)
        self.assertEquals(pkgs.__len__(), 2)

    def test_getNoInstalledPackages(self):
        installedPkgPath = 'abcd'
        pkgs = PackageUtil.getAllInstalledPackages(installedPkgPath)
        self.assertEquals(pkgs.__len__(), 0)

    def test_cleanupOrphanedPackages(self):
        from agent.lib.utils import rchown
        from agent.tests.unit.test_util import createManifest
        serviceName = 'service2'
        manifestName = 'manifestA'
        try:
            createManifest(self, packages = ["http://github.com/yubin154/cronusagent/blob/master/agent/agent/tests/unit/packages/perlserver-1.0.0.unix.cronus"],
                                    service = serviceName, manifest = manifestName)
        except Exception as ex:
            print 'exception thrown during mf %s' % str(ex)
        installedPkgPath = os.path.realpath(os.path.join(manifestutil.serviceRootPath() , serviceName, 'installed-packages'))

        uname = configutil.getAppUser()
        uid, gid = utils.getUidGid(uname)
        rchown(installedPkgPath, uid, gid)

        self.assertEquals(len(os.listdir(installedPkgPath)) , 1)
        self.app.delete(url(controller = 'manifest', action = 'delete', service = serviceName, manifest = manifestName), expect_errors = True)
        pylons.config['packageMgr_install_package_age'] = 0
        pylons.config['packageMgr_install_package_min_age'] = 0.0
        time.sleep(1) 
        PackageMgr.cleanupOrphanedPackages()
        self.assertEquals(len(os.listdir(installedPkgPath)) , 0)

    def test_cleanupOrphanedPackages2(self):
        from agent.lib.utils import rchown
        from agent.tests.unit.test_util import createManifest
        serviceName = 'service2'
        manifestName = 'manifestA'
        serviceName1 = 'service3'
        try:
            createManifest(self, packages = ["http://github.com/yubin154/cronusagent/blob/master/agent/agent/tests/unit/packages/perlserver-1.0.0.unix.cronus"],
                                      service = serviceName, manifest = manifestName)
            createManifest(self, packages = ["http://github.com/yubin154/cronusagent/blob/master/agent/agent/tests/unit/packages/perlserver-1.0.0.unix.cronus"],
                                      service = serviceName1, manifest = manifestName)
        except Exception as ex:
            print 'exception thrown during mf %s' % str(ex)
        installedPkgPath = os.path.realpath(os.path.join(manifestutil.serviceRootPath() , serviceName, 'installed-packages'))
        installedPkgPath1 = os.path.realpath(os.path.join(manifestutil.serviceRootPath() , serviceName1, 'installed-packages'))
        uname = configutil.getAgentUser()
        uid, gid = utils.getUidGid(uname)
        rchown(installedPkgPath, uid, gid)
        rchown(installedPkgPath1, uid, gid)
        self.assertEquals(len(os.listdir(installedPkgPath)) , 1)
        self.assertEquals(len(os.listdir(installedPkgPath1)) , 1)
        self.app.delete(url(controller = 'manifest', action = 'delete', service = serviceName, manifest = manifestName), expect_errors = True)
        self.app.delete(url(controller = 'manifest', action = 'delete', service = serviceName1, manifest = manifestName), expect_errors = True)
        pylons.config['packageMgr_install_package_age'] = 0
        pylons.config['packageMgr_install_package_min_age'] = 0.0
        PackageMgr.cleanupOrphanedPackages()
        self.assertEquals(len(os.listdir(installedPkgPath)) , 0)
        self.assertEquals(len(os.listdir(installedPkgPath1)) , 0)

    def __test_cleanUpInstalledPackages(self):
        from agent.lib.utils import rchown
        from agent.tests.unit.test_util import createManifest
        serviceName = 'service2'
        manifestName = 'manifestA'
        try:
            createManifest(self, packages = ["http://github.com/yubin154/cronusagent/blob/master/agent/agent/tests/unit/packages/perlserver-1.0.0.unix.cronus"],
                                    service = serviceName, manifest = manifestName)
        except Exception as ex:
            print 'exception thrown during mf %s' % str(ex)
        installedPkgPath = os.path.realpath(os.path.join(manifestutil.serviceRootPath() , serviceName, 'installed-packages'))

        uname = configutil.getAgentUser()
        uid, gid = utils.getUidGid(uname)
        rchown(installedPkgPath, uid, gid)


        pkgs = []
        for pkg in os.listdir(installedPkgPath):
            pkgs.append(os.path.join(installedPkgPath, pkg))

        pkgVers = []
        for pkg in pkgs:
            for pkgVer in os.listdir(pkg):
                pkgVers.append(os.path.join(pkg, pkgVer))

        self.assertEquals(len(os.listdir(installedPkgPath)) , 1)

        self.app.delete(url(controller = 'manifest', action = 'delete', service = serviceName, manifest = manifestName), expect_errors = True)
        #import pdb; pdb.set_trace();
        symLinks = [] #ManifestController.getAllSymLinks(serviceName)
        orphans = set(pkgVers) - set(symLinks)
        age = pylons.config['packageMgr_install_package_age']
        pylons.config['packageMgr_install_package_age'] = 20
        #PackageUtil.cleanUpInstalledPkgs(installedPkgPath, orphans)
        self.assertEquals(len(os.listdir(installedPkgPath)) , 1)
        time.sleep(40)
        PackageUtil.cleanupInstalledPkgs(installedPkgPath, orphans)
        self.assertEquals(len(os.listdir(installedPkgPath)) , 0)
        pylons.config['packageMgr_install_package_age'] = age
        self.assertEquals(pylons.config['packageMgr_install_package_age'], age)

    def __test_garbageCollection(self):
        from agent.tests.unit.test_util import createManifest
        serviceName = 'service3'
        manifestName = 'manifestA'
        try:
            createManifest(self, packages = ["http://github.com/yubin154/cronusagent/blob/master/agent/agent/tests/unit/packages/pkgA-1.2.0.unix.cronus",
                                  "http://github.com/yubin154/cronusagent/blob/master/agent/agent/tests/unit/packages/pkgB-0.6.0.unix.cronus"],
                                  service = serviceName, manifest = manifestName)
        except Exception as ex:
            print 'exception thrown during mf %s' % str(ex)

        self.app.delete(url(controller = 'manifest', action = 'delete', service = serviceName, manifest = manifestName), expect_errors = True)


        age = pylons.config['packageMgr_package_age']
        pylons.config['packageMgr_package_age'] = 10
        pkgs = PackageMgr.packagePath()
        self.assertEquals(len(os.listdir(pkgs)), 2)
        appGlobal = pylons.config['pylons.app_globals']
        appGlobal.packageMgr.start()
        time.sleep(80)
        self.assertEquals(len(os.listdir(pkgs)), 0)
        pylons.config['packageMgr_package_age'] = age
        self.assertEquals(pylons.config['packageMgr_package_age'], age)
        appGlobal.packageMgr.stop()
        time.sleep(20)

    def test_cleanUpAllInstalledPackages(self):
        from agent.lib.utils import rchown
        from agent.tests.unit.test_util import createManifest
        #import pdb;pdb.set_trace();
        serviceName = 'service3'
        manifestName = 'manifestB'
        try:
            createManifest(self, packages = ["http://github.com/yubin154/cronusagent/blob/master/agent/agent/tests/unit/packages/perlserver-1.0.0.unix.cronus"],
                                  service = serviceName, manifest = manifestName)
        except Exception as ex:
            print 'exception thrown during mf %s' % str(ex)

        installedPkgPath = os.path.realpath(os.path.join(manifestutil.serviceRootPath() , serviceName, 'installed-packages'))

        uname = configutil.getAgentUser()
        uid, gid = utils.getUidGid(uname)
        rchown(installedPkgPath, uid, gid)


        pkgs = []
        for pkg in os.listdir(installedPkgPath):
            pkgs.append(os.path.join(installedPkgPath, pkg))

        pkgVers = []
        for pkg in pkgs:
            for pkgVer in os.listdir(pkg):
                pkgVers.append(os.path.join(pkg, pkgVer))

        self.assertEquals(len(os.listdir(installedPkgPath)) , 1)

        self.app.delete(url(controller = 'manifest', action = 'delete', service = serviceName, manifest = manifestName), expect_errors = True)
        #import pdb; pdb.set_trace();
        symLinks = [] #ManifestController.getAllSymLinks(serviceName)
        orphans = set(pkgVers) - set(symLinks)
        age = pylons.config['packageMgr_install_package_age']
        minage = pylons.config['packageMgr_install_package_min_age']
        pylons.config['packageMgr_install_package_age'] = 0
        pylons.config['packageMgr_install_package_min_age'] = 0.0
        self.assertEquals(len(os.listdir(installedPkgPath)) , 1)
        PackageUtil.cleanupInstalledPkgs(installedPkgPath, orphans)
        #PackageUtil.cleanUpInstalledPkgs(installedPkgPath, orphans)
        self.assertEquals(len(os.listdir(installedPkgPath)) , 0)
        pylons.config['packageMgr_install_package_age'] = age
        pylons.config['packageMgr_install_package_min_age'] = minage



    def test_noAgeGarbageCollection(self):
        #from agent.controllers.service import ServiceController
        from agent.tests.unit.test_util import createManifest
        serviceName = 'service4'
        manifestName = 'manifestb'
        try:
            createManifest(self, packages = ["http://github.com/yubin154/cronusagent/blob/master/agent/agent/tests/unit/packages/pkgA-1.2.0.unix.cronus",
                                  "http://github.com/yubin154/cronusagent/blob/master/agent/agent/tests/unit/packages/pkgB-0.6.0.unix.cronus"],
                                  service = serviceName, manifest = manifestName)
        except Exception as ex:
            print 'exception thrown during mf %s' % str(ex)

        self.app.delete(url(controller = 'manifest', action = 'delete', service = serviceName, manifest = manifestName), expect_errors = True)
        age = pylons.config['packageMgr_package_age']
        pylons.config['packageMgr_package_age'] = 86400
        pkgs = PackageMgr.packagePath()
        self.assertEquals(len(os.listdir(pkgs)), 2)
        time.sleep(40)
        self.assertEquals(len(os.listdir(pkgs)), 2)
        pylons.config['packageMgr_package_age'] = age

    def test_forceDeletePackages(self):
        #import pdb;pdb.set_trace();
        from agent.tests.unit.test_util import createManifest
        if os.name == 'posix':
            serviceName = 'service4'
            manifestName = 'manifestb'
            try:
                createManifest(self, packages = ["http://github.com/yubin154/cronusagent/blob/master/agent/agent/tests/unit/packages/pkgA-1.2.0.unix.cronus",
                                  "http://github.com/yubin154/cronusagent/blob/master/agent/agent/tests/unit/packages/pkgB-0.6.0.unix.cronus"],
                                  service = serviceName, manifest = manifestName)
            except Exception as ex:
                print 'exception thrown during mf %s' % str(ex)

            self.app.delete(url(controller = 'manifest', action = 'delete', service = serviceName, manifest = manifestName), expect_errors = True)
            age = pylons.config['packageMgr_package_age']
            pylons.config['packageMgr_package_age'] = 86400
            minage = pylons.config['packageMgr_package_min_age']
            pylons.config['packageMgr_package_min_age'] = 0.0
            #appGlobal = pylons.config['pylons.app_globals']
            #appGlobal.packageMgr.start()
            disk_threshold = pylons.config['health_disk_usage_percent_threshold']
            pylons.config['health_disk_usage_percent_threshold'] = 1
            pylons.config['health_disk_usage_gc_threshold'] = 1

            pkgs = PackageMgr.packagePath()
            self.assertEquals(len(os.listdir(pkgs)), 2)
            PackageMgr.forceCleanUpDownloadedPkgs()
            self.assertEquals(len(os.listdir(pkgs)), 0)
            pylons.config['packageMgr_package_age'] = age
            pylons.config['packageMgr_package_min_age'] = minage
            pylons.config['health_disk_usage_percent_threshold'] = disk_threshold

    def test_package_min_age_during_forceDelete(self):
        #import pdb;pdb.set_trace();
        from agent.tests.unit.test_util import createManifest
        serviceName = 'service5'
        manifestName = 'manifestb'
        try:
            createManifest(self, packages = ["http://github.com/yubin154/cronusagent/blob/master/agent/agent/tests/unit/packages/pkgA-1.2.0.unix.cronus",
                                  "http://github.com/yubin154/cronusagent/blob/master/agent/agent/tests/unit/packages/pkgB-0.6.0.unix.cronus"],
                                  service = serviceName, manifest = manifestName)
        except Exception as ex:
            print 'exception thrown during mf %s' % str(ex)

        self.app.delete(url(controller = 'manifest', action = 'delete', service = serviceName, manifest = manifestName), expect_errors = True)
        age = pylons.config['packageMgr_package_age']
        pylons.config['packageMgr_package_age'] = 86400
        minage = pylons.config['packageMgr_package_min_age']
        pylons.config['packageMgr_package_min_age'] = 86400

        disk_threshold = pylons.config['health_disk_usage_percent_threshold']
        pylons.config['health_disk_usage_percent_threshold'] = 1

        pkgs = PackageMgr.packagePath()
        self.assertEquals(len(os.listdir(pkgs)), 2)
        time.sleep(40)
        self.assertEquals(len(os.listdir(pkgs)), 2)
        pylons.config['packageMgr_package_age'] = age
        pylons.config['packageMgr_package_min_age'] = minage
        pylons.config['health_disk_usage_percent_threshold'] = disk_threshold

