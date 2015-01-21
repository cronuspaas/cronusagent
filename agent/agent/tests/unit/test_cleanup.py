from agent.tests import *
import pylons
import os
import logging
import time
import json
from pylons import config
from subprocess import Popen

from agent.controllers.service import ServiceController
from agent.lib.utils import rchown
from agent.lib.packagemgr import PackageMgr

from agent.tests.unit.test_util import commonSetup, checkStatus, mockDownloadPkg
from agent.tests.unit.test_util import commonTearDown
from agent.tests.unit.test_threadmgr import WaitThread
from agent.lib import utils, manifestutil


LOG = logging.getLogger(__name__)

class TestCleanupController(TestController):

    def setUp(self):
        commonSetup()

    def tearDown(self):
        commonTearDown()

    @staticmethod
    def rchown(path, uname):
        uid, gid = utils.getUidGid(uname)
        rchown(path, uid, gid)

    def testDelete(self):
        def deleteTestDir(service):
            LOG.debug('************ service = %s' % service)
            response = self.app.delete(url(controller='service', service=service, action='delete'), expect_errors = True)
            # make sure the responses are correct
            LOG.debug('status = ' + str(response.status_int))
#            assert response.status_int == 500, "HTTP response != 500"

        def makeTestDir(path):
            os.makedirs(path)
            os.makedirs(os.path.join(path, 'manifests'))
            os.makedirs(os.path.join(path, 'installed-packages'))

        def createManifests(mf_path):
            os.makedirs(os.path.join(mf_path, 'm1.0', 'dummy_dir1.0'))
            os.makedirs(os.path.join(mf_path, 'm2.0', 'dummy_dir2.0'))
            latest = os.path.join(mf_path, 'm3.0')
            os.makedirs(os.path.join(latest, 'dummy_dir3.0'))

            utils.symlink(latest, os.path.join(mf_path, 'active'))

            return (['m1.0', 'm2.0', 'm3.0'], 'm3.0')

        def makePackageContent(path, pkgPath, pkgPropPath):
            pkgFile = file(pkgPath, 'w')
            for index in range(10):
                pkgFile.write(('%s%s') % (index, index))
            pkgFile.close()

            pkgFile = file(pkgPropPath, 'w')
            for index in range(10):
                pkgFile.write(('%s%s') % (index, index))
            pkgFile.close()
            uname = pylons.config['agent_user_account']
            TestCleanupController.rchown(path, uname)

        def createTestThread(serviceName):
            appGlobal = config['pylons.app_globals']
            testTh = WaitThread(appGlobal.threadMgr, ServiceController.serviceCat(serviceName))
            testTh.start()
            return testTh

        def startTestProcess():
            cmd = utils.sudoCmd(["sleep", "5"], pylons.config['app_user_account'])
            return Popen(cmd)

        path1 = os.path.join(pylons.config['agent_root'], 'service_nodes', 'foo')
        path2 = os.path.join(pylons.config['agent_root'], 'service_nodes', 'bar')
        path3 = os.path.join(pylons.config['agent_root'], 'service_nodes', 'agent')

        deleteTestDir('foo')
        deleteTestDir('bar')
        deleteTestDir('agent')

        # make dirs
        makeTestDir(path1)
        makeTestDir(path2)
        makeTestDir(path3)
        all_mf, active_mf = createManifests(ServiceController.manifestPath('agent'))

        uname = pylons.config['agent_user_account']
        TestCleanupController.rchown(ServiceController.serviceRootPath(), uname)

        pkgDir = PackageMgr.packagePath()
        pkgPath = os.path.join(pkgDir, "foo.cronus")
        pkgPropPath = os.path.join(pkgDir, "foo.cronus.prop")
        makePackageContent(pkgDir, pkgPath, pkgPropPath)

        # create threads
        testThFoo = createTestThread('foo')
        testThBar = createTestThread('bar')
        testThAgent = createTestThread('agent')

        # start process
        process = startTestProcess()

        # start testing
        LOG.debug('************ start cleanup')
        response = self.app.post(url(controller='cleanup', action='post'))
        LOG.debug ('Delete response body = ' + response.body)
        body = json.loads(response.body)

        tm = time.time()
        while (tm + 10 > time.time()):
            response = self.app.get(body['status'], expect_errors = True)
            LOG.debug ('Status response body = ' + response.body)
            body = json.loads(response.body)
            print body
            if (body['progress'] == 100):
                break
            time.sleep(0.1)

        # make sure the responses are correct
        LOG.debug('status = ' + str(response.status_int))
        assert response.status_int == 200, "HTTP response != 200"

        time.sleep(0.1)
        assert not os.path.exists(path1), 'service foo does exist or is not a directory'
        assert not os.path.exists(path2), 'service bar does exist or is not a directory'
        assert os.path.exists(path3), 'service agent does NOT exist or is not a directory'
        assert not testThFoo.isAlive(), 'thread Foo is still alive'
        assert not testThBar.isAlive(), 'thread Bar is still alive'
        assert not testThAgent.isAlive(), 'thread Agent is still alive'
        assert not os.path.exists(pkgPath), 'package foo exists'
        assert not os.path.exists(pkgPropPath), 'package prop foo exists'
        assert os.path.exists(pkgDir), 'package directory does not exist'
        # ensure agent cleanup is proper
        active_mf_path = manifestutil.manifestPath('agent', active_mf)
        active_link = os.path.join(ServiceController.manifestPath('agent'), 'active')
        all_mf.remove(active_mf)
        actual_active_mf_path = utils.readlink(active_link)

        self.assertTrue(os.path.exists(active_mf_path), 'active agent manifest got deleted but shouldn\t have')
        self.assertTrue(os.path.exists(active_link), 'agent active link missing')
        self.assertEqual(active_mf_path, actual_active_mf_path, 'agent active link pointing to some wrong manifest; link broken?')
        for mf in all_mf:
            agnt_mf_path = manifestutil.manifestPath('agent', mf)
            self.assertFalse(os.path.exists(agnt_mf_path), 'non active agent mf %s should have been deleted' % mf)
#         self.assertNotEquals(process.poll(), None)


    def test_delete_cronus_package(self):
        package = "pkgA-1.2.0.unix"
        package_url = "http://www.stackscaling.com/agentrepo/pkgA-1.2.0.unix.cronus"
        package_path = os.path.join(PackageMgr.packagePath(), package + '.cronus')
        # case 1 - package is not present
        self.assertFalse(os.path.exists(package_path))
        response = self.app.delete(url(controller='cleanup', package=package, action='deleteCronusPackage'), expect_errors = True)
        self.assertEqual(response.status_int, 200)

        # case 2 - package is present
        mockDownloadPkg(package_url)
        body = json.dumps({'package': package_url, 'packageloc' : package + '.cronus'})
        response = self.app.post(url(controller = 'distribution', action = 'startdownload', service = "dist"),
                                 headers = {'Content-Type' : 'application/json'},
                                 params = body, expect_errors = True)

        self.assertEqual(response.status_int, 200)
        checkStatus(self, "http_download", response, 100)
        self.assertTrue(os.path.exists(package_path))
        response = self.app.delete(url(controller='cleanup', package=package, action='deleteCronusPackage'), expect_errors = True)
        self.assertEqual(response.status_int, 200)
        self.assertFalse(os.path.exists(package_path))
