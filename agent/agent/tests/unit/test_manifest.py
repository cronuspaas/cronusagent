from agent.tests import *
import json
import logging
from agent.lib.agent_thread.manifest_create import ManifestCreate
from agent.lib.packagemgr import PackageMgr
from agent.controllers.service import ServiceController
from agent.lib.errors import Errors
from agent.lib.utils import symlink, islink
from agent.lib import manifestutil
import shutil
import os

from agent.tests.unit.test_util import createManifest, checkStatus,\
    mockDownloadPkg
from agent.tests.unit.test_util import commonSetup
from agent.tests.unit.test_util import commonTearDown
from webtest import AppError
import time


LOG = logging.getLogger(__name__)

class TestManifestController(TestController):

    def setUp(self):
        commonSetup()

    def tearDown(self):
        commonTearDown()

    def test_package_reuse(self):
        createManifest(self)
        body = json.dumps({'package' : ['/packages/perlserver']})
        body = self.app.post(url(controller = 'manifest', action = 'post', service = "foo", manifest = "baz"),
                                 headers = {'Content-Type' : 'application/json'},
                                 params = body, expect_errors = True)

        self.assertTrue(os.path.exists(os.path.join(PackageMgr.packagePath(), 'perlserver-1.0.0.unix.cronus')))
        self.assertTrue(os.path.exists(os.path.join(ServiceController.installedPkgPath('foo'), 'perlserver', '1.0.0.unix',
                                           'cronus', 'scripts', 'activate')))
        self.assertTrue(islink(os.path.join(manifestutil.manifestPath('foo', 'bar'), 'perlserver')))

        for _ in range(10):
            if islink(os.path.join(manifestutil.manifestPath('foo', 'baz'), 'perlserver')):
                break
            time.sleep(1)

        self.assertTrue(islink(os.path.join(manifestutil.manifestPath('foo', 'baz'), 'perlserver')))

    def test_post_without_service(self):

        body = json.dumps({'package' : ['http://github.com/yubin154/cronusagent/blob/master/agent/agent/tests/unit/packages/perlserver-1.0.0.unix.cronus']})
        response = self.app.post(url(controller = 'manifest', action = 'post', service = "foo", manifest = "bar"),
                                 headers = {'Content-Type' : 'application/json'},
                                 params = body)

        assert response.status_int == 200, 'Manifest Post assert'
        time.sleep(1)
        self.assertFalse(os.path.exists(manifestutil.manifestPath('foo', 'bar')))



    def test_post2(self):
        # successful post
        createManifest(self)

        self.assertTrue(os.path.exists(os.path.join(PackageMgr.packagePath(), 'perlserver-1.0.0.unix.cronus')))
        self.assertTrue(os.path.exists(os.path.join(manifestutil.installedPkgRootPath('foo'), 'perlserver', '1.0.0.unix',
                                           'cronus', 'scripts', 'activate')))
        self.assertTrue(islink(os.path.join(manifestutil.manifestPath('foo', 'bar'), 'perlserver')))
        self.assertTrue(islink(os.path.join(manifestutil.installedPkgRootPath('foo'), 'perlserver', '1.0.0.unix', '.appdata')))

    def test_post2_success(self):
        createManifest(self)
        

    def test_post3_pkg_already_installed(self):
        createManifest(self)

        # now lets remove the manifest path
        path = os.path.join(manifestutil.manifestPath('foo', 'bar'))
        shutil.rmtree(path)

        # now create the manifest again
        createManifest(self)

        self.assertTrue(os.path.exists(os.path.join(PackageMgr.packagePath(), 'perlserver-1.0.0.unix.cronus')))
        self.assertTrue(os.path.exists(os.path.join(ServiceController.installedPkgPath('foo'), 'perlserver', '1.0.0.unix',
                                           'cronus', 'scripts', 'activate')))
        self.assertTrue(islink(os.path.join(manifestutil.manifestPath('foo', 'bar'), 'perlserver')))


    def test_post3_already_installed_manifest(self):
        createManifest(self)

        self.assertTrue(os.path.exists(os.path.join(PackageMgr.packagePath(), 'perlserver-1.0.0.unix.cronus')))
        self.assertTrue(os.path.exists(os.path.join(ServiceController.installedPkgPath('foo'), 'perlserver', '1.0.0.unix',
                                           'cronus', 'scripts', 'activate')))
        self.assertTrue(islink(os.path.join(manifestutil.manifestPath('foo', 'bar'), 'perlserver')))


        body = json.dumps({'package' : ['http://github.com/yubin154/cronusagent/blob/master/agent/agent/tests/unit/packages/perlserver-1.0.0.unix.cronus']})
        response = self.app.post(url(controller = 'manifest', action = 'post', service = "foo", manifest = "bar"),
                                 headers = {'Content-Type' : 'application/json'},
                                 params = body, expect_errors = True)
        self.assertEquals(201, response.status_int, 'Manifest Post assert')
        body = json.loads(response.body)
        assert response.status_int == 201, 'Manifest Post assert'
#        self.assertEquals(int(Errors.MANIFEST_ALREADY_EXISTS), int(body['error']))

    def test_post_manifest_inprogress_errorout(self):
        packages = ['http://github.com/yubin154/cronusagent/blob/master/agent/agent/tests/unit/packages/perlserver-1.0.0.unix.cronus']
        manifest = 'bar'
        service = 'foo'

        try:
            path = ServiceController.manifestPath(service)
            os.makedirs(path)
            path = ServiceController.installedPkgPath(service)
            os.makedirs(path)
            path = ServiceController.downloadedPkgPath(service)
            os.makedirs(path)
        except Exception as excep:
            LOG.warning('got an OS Exception - %s' % str(excep))


        body = json.dumps({'package' : packages})
        response = self.app.post(url(controller = 'manifest', action = 'post', service = service, manifest = manifest),
                                 headers = {'Content-Type' : 'application/json'},
                                 params = body)
        assert response.status_int == 200, 'Manifest Post assert'

        try:
            response = self.app.post(url(controller = 'manifest', action = 'post', service = service, manifest = manifest),
                                 headers = {'Content-Type' : 'application/json'},
                                 params = body)
            #should error out!
            raise Exception('Oops! Expected AppError but did not get any')
        except AppError:
            pass

    def test_post_manifest_inprogress_ok(self):
        service = 'foo'
        manifest = 'blahblah'
        try:
            path = ServiceController.servicePath(service)
            if os.path.exists(path):
                shutil.rmtree(path)
            path = ServiceController.manifestPath(service)
            os.makedirs(path)
            path = ServiceController.installedPkgPath(service)
            os.makedirs(path)
            inProgressPath = ManifestCreate.inProgress(manifestutil.manifestPath(service, manifest))
            os.makedirs(inProgressPath)
            path = ServiceController.downloadedPkgPath(service)
            os.makedirs(path)
        except Exception as excep:
            LOG.warning('got an OS Exception - %s' % str(excep))

        createManifest(self, ["http://github.com/yubin154/cronusagent/blob/master/agent/agent/tests/unit/packages/pkgA-1.2.0.unix.cronus"], manifest = 'blahblah', createDirs = False)
        self.assertTrue(islink(os.path.join(manifestutil.manifestPath('foo', 'blahblah'), 'pkgA')))


    def test_post5(self):

        createManifest(self, ["http://github.com/yubin154/cronusagent/blob/master/agent/agent/tests/unit/packages/pkgA-1.2.0.unix.cronus",
                              "http://github.com/yubin154/cronusagent/blob/master/agent/agent/tests/unit/packages/pkgB-0.6.0.unix.cronus"])

        self.assertTrue(os.path.exists(os.path.join(PackageMgr.packagePath(), 'pkgA-1.2.0.unix.cronus')))
        self.assertTrue(os.path.exists(os.path.join(PackageMgr.packagePath(), 'pkgB-0.6.0.unix.cronus')))

    def test_get(self):
        createManifest(self)

        response = self.app.get(url(controller = 'manifest', action = 'get', service = "foo", manifest = "bar"))
        body = json.loads(response.body)
        self.assertEquals(['perlserver-1.0.0.unix.cronus'], body['result'])

    def test_delete_active_manifest(self):
        createManifest(self)

        self.assertTrue(os.path.isdir(ServiceController.manifestPath('foo')))
        currentPath = os.getcwd()
        os.chdir(ServiceController.manifestPath('foo'))
        manifestPath = 'bar' #ManifestController.manifestPath('foo', 'bar'); use short manifest name instead of full path
        symlink(manifestPath, 'active')
        os.chdir(currentPath)

        response = self.app.delete(url(controller = 'manifest', action = 'delete', service = "foo", manifest = "bar"),
                                   expect_errors = True)
        self.assertEquals(500, response.status_int)

        body = json.loads(response.body)
        self.assertEquals(Errors.MANIFEST_DELETING_ACTIVE_MANIFEST, body['error'])

    def test_delete(self):
        createManifest(self)

        response = self.app.delete(url(controller = 'manifest', action = 'delete', service = "foo", manifest = "bar"),
                                   expect_errors = True)
        print '*************** = ' + response.body
        self.assertEquals(200, response.status_int)

        for _ in range(10):
            if not os.path.isdir(manifestutil.manifestPath('foo', 'bar')):
                break
            else:
                time.sleep(0.1)

        self.assertFalse(os.path.isdir(manifestutil.manifestPath('foo', 'bar')))


    def test_getPackagePaths(self):
        serviceName = 'service1'
        manifestName = 'manifestA'
        createManifest(self, packages = ["http://github.com/yubin154/cronusagent/blob/master/agent/agent/tests/unit/packages/pkgA-1.2.0.unix.cronus",
                              "http://github.com/yubin154/cronusagent/blob/master/agent/agent/tests/unit/packages/pkgB-0.6.0.unix.cronus"],
                              service = serviceName, manifest = manifestName)

        self.assertTrue(os.path.exists(os.path.join(PackageMgr.packagePath(), 'pkgA-1.2.0.unix.cronus')))

        packagePaths = manifestutil.packagePaths(serviceName, manifestName);
        print ">>>>>>>>>>>>" + str(packagePaths)
        self.assertTrue(len(packagePaths) >= 2)
        bitmap = 0
        for path in packagePaths:
            if path.find("pkgA") >= 0:
                self.assertTrue(os.path.isdir(path))
                bitmap |= 1
            elif path.find("pkgB") >= 0:
                self.assertTrue(os.path.isdir(path))
                bitmap |= 2
        self.assertEquals(3, bitmap)

    def test_inprogress_pkg_download(self):
        service = 'foo'
        try:
            path = ServiceController.manifestPath(service)
            os.makedirs(path)
            path = ServiceController.installedPkgPath(service)
            os.makedirs(path)
            path = ServiceController.downloadedPkgPath(service)
            os.makedirs(path)
            inprogressPath = os.path.join(PackageMgr.packagePath(), 'perlserver-1.0.0.unix.cronus.inprogress')
            inprogressFile = open(inprogressPath, 'w')
            inprogressFile.write('somegarbage')
            inprogressFile.close()
        except Exception as excep:
            LOG.warning('got an OS Exception - %s' % str(excep))

        createManifest(self)
        self.assertTrue(os.path.exists(os.path.join(PackageMgr.packagePath(), 'perlserver-1.0.0.unix.cronus')))
        self.assertTrue(islink(os.path.join(manifestutil.manifestPath('foo', 'bar'), 'perlserver')))

    def test_same_pkg_download_parallel(self):
        packages = ['http://www.stackscaling.com/agentrepo/pkgA-1.2.0.unix.cronus']
        manifest1 = 'bar'
        manifest2 = 'blah'
        service1 = 'foo'
        service2 = 'lah'
        try:
            for pkg in packages:
                mockDownloadPkg(pkg)
            
            path = ServiceController.manifestPath(service1)
            os.makedirs(path)
            path = ServiceController.installedPkgPath(service1)
            os.makedirs(path)
            path = ServiceController.downloadedPkgPath(service1)
            os.makedirs(path)
            path = ServiceController.manifestPath(service2)
            os.makedirs(path)
            path = ServiceController.installedPkgPath(service2)
            os.makedirs(path)
            path = ServiceController.downloadedPkgPath(service2)
            os.makedirs(path)
        except Exception as excep:
            LOG.warning('got an OS Exception - %s' % str(excep))

        body = json.dumps({'package' : packages})
        response1 = self.app.post(url(controller = 'manifest', action = 'post', service = service1, manifest = manifest1),
                                 headers = {'Content-Type' : 'application/json'},
                                 params = body)
        assert response1.status_int == 200, 'Manifest Post assert'

        response2 = self.app.post(url(controller = 'manifest', action = 'post', service = service2, manifest = manifest2),
                                 headers = {'Content-Type' : 'application/json'},
                                 params = body)
        assert response2.status_int == 200, 'Manifest Post assert'

        checkStatus(self, 'create manifest bar', response1, timeout = 25)
        checkStatus(self, 'create manifest baz', response2, timeout = 25)

        self.assertTrue(os.path.exists(os.path.join(PackageMgr.packagePath(), 'pkgA-1.2.0.unix.cronus')))
        self.assertTrue(islink(os.path.join(manifestutil.manifestPath('foo', 'bar'), 'pkgA')))
        self.assertTrue(islink(os.path.join(manifestutil.manifestPath('lah', 'blah'), 'pkgA')))

    def test_getAllSymLinks(self):
        #import pdb;
        #pdb.set_trace()
        serviceName = '.sbe.appService.SI1'
        manifestName = 'manifestA'
        try:
            createManifest(self, packages = ["http://github.com/yubin154/cronusagent/blob/master/agent/agent/tests/unit/packages/pkgA-1.2.0.unix.cronus",
                                  "http://github.com/yubin154/cronusagent/blob/master/agent/agent/tests/unit/packages/pkgB-0.6.0.unix.cronus"],
                                  service = serviceName, manifest = manifestName)
        except Exception as ex:
            print 'exception thrown during mf'

        symLinks = manifestutil.getAllSymLinks(serviceName)
        """ return all the symlinks from manifests to packages for a given service"""
        LOG.debug('calling getAllSymLinks')
        linkedPaths = []
        installedPkgPath = os.path.join(ServiceController.servicePath(serviceName), 'installed-packages')
        pathToPkgA = os.path.join(installedPkgPath, 'pkgA')
        pathToPkgA120 = os.path.join(pathToPkgA, '1.2.0.unix')
        pathToPkgB = os.path.join(installedPkgPath, 'pkgB')
        pathToPkgB060 = os.path.join(pathToPkgB, '0.6.0.unix')

        bitmap = 0
        for path in symLinks:
            if path.find(pathToPkgA120) >= 0:
                self.assertTrue(os.path.isdir(path))
                bitmap |= 1
            elif path.find(pathToPkgB060) >= 0:
                self.assertTrue(os.path.isdir(path))
                bitmap |= 2
        self.assertEquals(3, bitmap)

    def test_multiple_manifest_create(self):
        """ when a manifest creation is in progress for a service, another creation should block """
        packages = ["http://www.stackscaling.com/agentrepo/pkgA-1.2.0.unix.cronus"]
        service = 'foo'
        manifest1 = 'bar'
        manifest2 = 'car'
        try:
            for pkg in packages:
                mockDownloadPkg(pkg)
                
            path = ServiceController.manifestPath(service)
            os.makedirs(path)
            path = ServiceController.installedPkgPath(service)
            os.makedirs(path)
        except Exception as excep:
            LOG.warning('got an OS Exception - %s' % str(excep))

        body = json.dumps({'package' : packages})
        response1 = self.app.post(url(controller = 'manifest', action = 'post', service = service, manifest = manifest1),
                                 headers = {'Content-Type' : 'application/json'},
                                 params = body)
        self.assertEquals(response1.status_int, 200, 'Manifest1 Post assert - should go through')

        try:
            response2 = self.app.post(url(controller = 'manifest', action = 'post', service = service, manifest = manifest2),
                                 headers = {'Content-Type' : 'application/json'},
                                 params = body)
            self.assertFalse(True, 'Expected an exception but did not get one!')
        except AppError:
            pass

        checkStatus(self, 'create manifest bar', response1, timeout = 25)
        self.assertTrue(islink(os.path.join(manifestutil.manifestPath('foo', 'bar'), 'pkgA')))
        self.assertFalse(islink(os.path.join(manifestutil.manifestPath('foo', 'car'), 'pkgA')))

    def test_get_installed_pkgs_filter_inprogress(self):
        from agent.lib.package import PackageUtil
        serviceName = '.sbe.appService.SI1'
        manifestName = 'manifestA'
        try:
            createManifest(self, packages = ["http://github.com/yubin154/cronusagent/blob/master/agent/agent/tests/unit/packages/pkgA-1.2.0.unix.cronus",
                                  "http://github.com/yubin154/cronusagent/blob/master/agent/agent/tests/unit/packages/pkgB-0.6.0.unix.cronus"],
                                  service = serviceName, manifest = manifestName)
        except Exception as ex:
            print 'exception thrown during mf'
        installed_pkg_path = ServiceController.installedPkgPath(serviceName)
        installed_packages = PackageUtil.getAllInstalledPackages(installed_pkg_path)
        self.assertEquals(2, len(installed_packages))
        for path in installed_packages:
            os.mkdir(path + '.inprogress')
        installed_packages = PackageUtil.getAllInstalledPackages(installed_pkg_path)
        self.assertEquals(2, len(installed_packages))

