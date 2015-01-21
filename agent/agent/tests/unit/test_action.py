from agent.tests import *
import json
import pylons
import os
import logging
import time


from agent.controllers.service import ServiceController
from agent.tests.unit.test_util import createManifest, checkStatus,\
    shutdownService, startService, deactivateManifest
from agent.tests.unit.test_util import activateManifest
from agent.tests.unit.test_util import restartService
from agent.tests.unit.test_util import commonSetup
from agent.tests.unit.test_util import commonTearDown
from webtest import AppError
from agent.lib.utils import islink
from agent.lib import manifestutil

LOG = logging.getLogger(__name__)

class TestActionController(TestController):


    def setUp(self):
        commonSetup()

    def tearDown(self):
        commonTearDown()


    def test_activateMissingManifest(self):
        body = json.dumps({'manifest':'bar'})
        response = self.app.post(url(controller='manifest', action='activate', service="foo", manifest="bar"),
                                     headers = {'Content-Type' : 'application/json'},
                                     params = body, expect_errors=True)
        assert response.status_int == 500
 
    def test_activateManifest(self):
 
        createManifest(self)
        activateManifest(self)
 
        # wait until the PORT files exists
        exists = False
        tm = time.time()
        while (tm + 10 > time.time()):
            if (os.path.exists(os.path.join(pylons.config['agent_root'], 'service_nodes/foo/installed-packages/perlserver/1.0.0.unix'))):
                exists = True
                break
            time.sleep(0.1)
        assert exists
 
    def test_activateManifest2(self):
        createManifest(self, packages = ["http://github.com/yubin154/cronusagent/blob/master/agent/agent/tests/unit/packages/pkgB-0.6.0.unix.cronus",
                                "http://github.com/yubin154/cronusagent/blob/master/agent/agent/tests/unit/packages/pkgA-1.2.0.unix.cronus"], manifest = "baz")
        activateManifest(self, manifest = "baz")
  
        createManifest(self, packages = ["http://github.com/yubin154/cronusagent/blob/master/agent/agent/tests/unit/packages/pkgB-0.6.0.unix.cronus",
                                "http://github.com/yubin154/cronusagent/blob/master/agent/agent/tests/unit/packages/pkgA-1.2.0.unix.cronus"], manifest = "biz")
        activateManifest(self, manifest = "biz")
  
        # wait until the PORT files exists
        exists = False
        tm = time.time()
        while (tm + 10 > time.time()):
            if (os.path.exists(os.path.join(pylons.config['agent_root'], 'service_nodes/foo/installed-packages/pkgA/1.2.0.unix')) and
                os.path.exists(os.path.join(pylons.config['agent_root'], 'service_nodes/foo/installed-packages/pkgB/0.6.0.unix'))):
                exists = True
                break
            time.sleep(0.1)
        assert exists
 
    def test_bad_shutdown(self):
        createManifest(self, ['http://github.com/yubin154/cronusagent/blob/master/agent/agent/tests/unit/packages/bad_shutdown_package-0.0.1.unix.cronus'], manifest = 'bar')
        createManifest(self, manifest = 'baz')
        activateManifest(self, manifest = 'bar')
 
        LOG.debug('**************** finished activating bar')
 
        body = json.dumps({'manifest':'baz'})
        response = self.app.post(url(controller='manifest', action='activate', service="foo", manifest="baz"),
                                 headers = {'Content-Type' : 'application/json'},
                                 params = body)
 
        assert response.status_int == 200
 
        body = json.loads(response.body)
 
        tm = time.time()
        while (tm + 20 > time.time()):
            response = self.app.get(body['status'], expect_errors = True)
            body = json.loads(response.body)
 
            print "activateManifest body = %s " % body
            if (response.status_int == 500):
                break
            time.sleep(0.1)
 
        # make sure this test failes out
        assert body['error'] != None
 
        # make sure the active link points to old manifest
        response = self.app.get(url(controller='service', service='foo', action='get'))
        body = json.loads(response.body)
        print "service get = %s" % body
 
        assert body['result']['activemanifest'] == 'bar'
 
    def test_bad_deactivate(self):
        createManifest(self, ['http://github.com/yubin154/cronusagent/blob/master/agent/agent/tests/unit/packages/bad_deactivate_package-0.0.1.unix.cronus'], manifest = 'bar')
        createManifest(self, manifest = 'baz')
        activateManifest(self, manifest = 'bar')
  
        LOG.debug('**************** finished activating bar')
  
        body = json.dumps({'manifest':'baz'})
        response = self.app.post(url(controller='manifest', action='activate', service="foo", manifest="baz"),
                                 headers = {'Content-Type' : 'application/json'},
                                 params = body)
  
        assert response.status_int == 200
  
        body = json.loads(response.body)
  
        tm = time.time()
        while (tm + 20 > time.time()):
            response = self.app.get(body['status'], expect_errors = True)
            body = json.loads(response.body)
  
            print "activateManifest body = %s " % body
            if (response.status_int == 500):
                break
            time.sleep(0.1)
  
        # make sure this test fails out
        assert body['error'] != None
  
        # make sure the active link points to old manifest
        response = self.app.get(url(controller='service', service='foo', action='get'))
        body = json.loads(response.body)
        print "service get = %s" % body
  
        assert body['result']['activemanifest'] == 'bar'
  
    def test_bad_deactivate2(self):
        createManifest(self, ['http://github.com/yubin154/cronusagent/blob/master/agent/agent/tests/unit/packages/bad_deactivate_package-0.0.1.unix.cronus'], manifest = 'bar')
        activateManifest(self, manifest = 'bar')
  
        LOG.debug('**************** finished activating bar')
  
        response = self.app.post(url(controller='action', action='deactivatemanifest', service='foo'),
                                headers = {'Content-Type' : 'application/json'},
                                expect_errors = True)
  
        body = json.loads(response.body)
  
        tm = time.time()
        while (tm + 20 > time.time()):
            response = self.app.get(body['status'], expect_errors = True)
            body = json.loads(response.body)
  
            print "activateManifest body = %s " % body
            if (response.status_int == 500):
                break
            time.sleep(0.1)
  
        # make sure this test failes out
        assert body['error'] != None
  
    def test_bad_install(self):
        createManifest(self, manifest = 'bar')
        createManifest(self, ['http://github.com/yubin154/cronusagent/blob/master/agent/agent/tests/unit/packages/bad_install_package-0.0.1.unix.cronus'], manifest = 'baz')
        activateManifest(self, manifest = 'bar')
  
        LOG.debug('**************** finished activating bar')
  
        body = json.dumps({'manifest':'baz'})
        response = self.app.post(url(controller='manifest', action='activate', service="foo", manifest='baz'),
                                 headers = {'Content-Type' : 'application/json'},
                                 params = body)
  
        assert response.status_int == 200
  
        body = json.loads(response.body)
  
        tm = time.time()
        LOG.debug("***************** tm = " + str(tm))
        while (tm + 60 > time.time()):
            response = self.app.get(body['status'], expect_errors = True)
            body = json.loads(response.body)
  
            LOG.debug("activateManifest body = %s " % body)
            if (response.status_int == 500):
                break
            time.sleep(0.1)
  
        # make sure this test failes out
        assert body['error'] != None
  
        # make sure the active link points to old manifest
        response = self.app.get(url(controller='service', service='foo', action='get'))
        body = json.loads(response.body)
        print "service get = %s" % body
  
        assert body['result']['activemanifest'] == 'bar'
  
    def test_bad_activate(self):
        createManifest(self, manifest = 'bar')
        createManifest(self, ['http://github.com/yubin154/cronusagent/blob/master/agent/agent/tests/unit/packages/bad_activate_package-0.0.1.unix.cronus'], manifest = 'baz')
        activateManifest(self, manifest = 'bar')
  
        LOG.debug('**************** finished activating bar')
  
        body = json.dumps({'manifest':'baz'})
        response = self.app.post(url(controller='manifest', action='activate', service="foo", manifest='baz'),
                                 headers = {'Content-Type' : 'application/json'},
                                 params = body)
  
        self.assertEquals(response.status_int, 200)
  
        body = json.loads(response.body)
  
        tm = time.time()
        while (tm + 20 > time.time()):
            response = self.app.get(body['status'], expect_errors = True)
            body = json.loads(response.body)
  
            print "activateManifest body = %s " % body
            if (response.status_int == 500):
                break
            time.sleep(0.1)
  
        # make sure this test failes out
        self.assertNotEquals(body['error'], None)
  
        # make sure the active link points to old manifest
        response = self.app.get(url(controller='service', service='foo', action='get'))
        body = json.loads(response.body)
        print "service get = %s" % body
  
        self.assertEquals(body['result']['activemanifest'], None)
  
    def test_bad_startup(self):
        createManifest(self, manifest = 'bar')
        createManifest(self, ['http://github.com/yubin154/cronusagent/blob/master/agent/agent/tests/unit/packages/bad_startup_package-0.0.1.unix.cronus'], manifest = 'baz')
        activateManifest(self, manifest = 'bar')
  
        LOG.debug('**************** finished activating bar')
  
        body = json.dumps({'manifest':'baz'})
        response = self.app.post(url(controller='manifest', action='activate', service="foo", manifest='baz'),
                                 headers = {'Content-Type' : 'application/json'},
                                 params = body)
  
        self.assertEquals(response.status_int, 200)
  
        body = json.loads(response.body)
  
        tm = time.time()
        while (tm + 20 > time.time()):
            response = self.app.get(body['status'], expect_errors = True)
            body = json.loads(response.body)
  
            print "activateManifest body = %s " % body
            if (response.status_int == 500):
                break
            time.sleep(0.1)
  
        # make sure this test fails out
        self.assertNotEquals(body['error'], None)
  
        # make sure the active link points to old manifest
        response = self.app.get(url(controller='service', service='foo', action='get'))
        body = json.loads(response.body)
        print "service get = %s" % body
  
        self.assertEquals(body['result']['activemanifest'], None)
  
    def test_restart_ok(self):
        createManifest(self, packages = ['http://github.com/yubin154/cronusagent/blob/master/agent/agent/tests/unit/packages/restart_package-0.0.1.unix.cronus'])
        activateManifest(self)
  
        # wait until the PORT files exists
        exists = False
        file_path = os.path.join(pylons.config['agent_root'], 'service_nodes/foo/installed-packages/restart_package/0.0.1.unix/cronus/scripts/myfile')
        tm = time.time()
        while (tm + 10 > time.time()):
            if (os.path.exists(file_path)):
                exists = True
                break
            time.sleep(0.1)
        assert exists
  
        # now read contents of file - which is timestamp and ensure it is not equal to timestamp after restart
        f = open(file_path, 'r')
        f_contents = f.readline()
        f.close()
        time.sleep(1)
        restartService(self)
        assert os.path.exists(file_path)
        f = open(file_path, 'r')
        f_new_contents = f.readline()
        f.close()
        LOG.debug('old file contents %s, new file contents %s' %(f_contents, f_new_contents))
        assert f_contents != f_new_contents
  
    def test_restart_no_active(self):
        createManifest(self)
        try:
            self.app.post(url(controller='action', action='restart', service='foo'),
                                       headers = {'Content-Type' : 'application/json'})
            raise
        except AppError:
            pass
  
    def test_startup_shutdown_ok(self):
        createManifest(self, packages = ['http://github.com/yubin154/cronusagent/blob/master/agent/agent/tests/unit/packages/restart_package-0.0.1.unix.cronus'])
        activateManifest(self)
  
        # wait until the PORT files exists
        exists = False
        file_path = os.path.join(pylons.config['agent_root'], 'service_nodes/foo/installed-packages/restart_package/0.0.1.unix/cronus/scripts/myfile')
        tm = time.time()
        while (tm + 10 > time.time()):
            if (os.path.exists(file_path)):
                exists = True
                break
            time.sleep(0.1)
        assert exists
  
        # now read contents of file - which is timestamp and ensure it is not equal to timestamp after restart
        f = open(file_path, 'r')
        f_contents = f.readline()
        f.close()
        time.sleep(5)
        shutdownService(self)
        assert not os.path.exists(file_path)
  
        startService(self)
        assert os.path.exists(file_path)
        f = open(file_path, 'r')
        f_new_contents = f.readline()
        f.close()
        LOG.debug('old file contents %s, new file contents %s' %(f_contents, f_new_contents))
        assert f_contents != f_new_contents
  
    def test_startup_shutdown_no_active(self):
        createManifest(self)
        try:
            self.app.post(url(controller='action', action='startupService', service='foo'),
                                       headers = {'Content-Type' : 'application/json'})
            raise
        except AppError:
            pass
  
        try:
            self.app.post(url(controller='action', action='shutdownService', service='foo'),
                                       headers = {'Content-Type' : 'application/json'})
            raise
        except AppError:
            pass
  
    def test_deactivate_ok(self):
        createManifest(self)
        activateManifest(self)
  
        # wait until the PORT files exists
        exists = False
        tm = time.time()
        while (tm + 10 > time.time()):
            if (os.path.exists(os.path.join(pylons.config['agent_root'], 'service_nodes/foo/installed-packages/perlserver/1.0.0.unix'))):
                exists = True
                break
            time.sleep(0.1)
        assert exists
  
        # now read contents of file - which is timestamp and ensure it is not equal to timestamp after restart
        time.sleep(10)
        deactivateManifest(self)
  
        exists = False
        activePath = os.path.join(ServiceController.manifestPath('foo'), 'active')
        tm = time.time()
        while (tm + 10 > time.time()):
            if (os.path.exists(activePath)):
                exists = True
                break
            time.sleep(0.1)
        assert not exists
  
    def test_deactivate_no_active(self):
        createManifest(self)
        try:
            self.app.post(url(controller='action', action='deactivatemanifest', service='foo'),
                                       headers = {'Content-Type' : 'application/json'})
            raise
        except AppError:
            pass
  
    def test_multiple_manifest_create_activate(self):
        ''' when a manifest activation is in progress for a service, another creation should block '''
        packages = ["http://github.com/yubin154/cronusagent/blob/master/agent/agent/tests/unit/packages/pkgB-0.6.0.unix.cronus",
                    "http://github.com/yubin154/cronusagent/blob/master/agent/agent/tests/unit/packages/pkgA-1.2.0.unix.cronus"]
        service = 'foo'
        manifest1 = 'bar'
        manifest2 = 'car'
        try:
            path = ServiceController.manifestPath(service)
            os.makedirs(path)
            path = ServiceController.installedPkgPath(service)
            os.makedirs(path)
        except Exception as excep:
            LOG.warning('got an OS Exception - %s' % str(excep))
  
  
        createManifest(self, packages, manifest1, service)
  
        body = json.dumps({'manifest':manifest1})
        response1 = self.app.post(url(controller='manifest', action='activate', service=service, manifest=manifest1),
                                       headers = {'Content-Type' : 'application/json'},
                                       params = body)
        self.assertEquals(response1.status_int, 200, 'Manifest1 Post assert - should go through')
  
        body = json.dumps({'package' : packages})
        try:
            response2 = self.app.post(url(controller='manifest', action='post', service=service, manifest=manifest2),
                                 headers = {'Content-Type' : 'application/json'},
                                 params = body)
            self.assertFalse(True, 'Expected an exception but did not get one!')
        except AppError:
            pass
  
        checkStatus(self, 'activate manifest bar', response1, timeout=25)
#        self.assertTrue(islink(os.path.join(ManifestController.manifestPath('foo', 'bar'), 'pkgA')))
#        self.assertFalse(islink(os.path.join(ManifestController.manifestPath('foo', 'car'), 'pkgA')))
  
    def test_multiple_manifest_activate(self):
        ''' when a manifest activation is in progress for a service, another activation should block '''
        packages = ["http://github.com/yubin154/cronusagent/blob/master/agent/agent/tests/unit/packages/pkgA-1.2.0.unix.cronus"]
        service = 'foo'
        manifest1 = 'bar'
        manifest2 = 'car'
        try:
            path = ServiceController.manifestPath(service)
            os.makedirs(path)
            path = ServiceController.installedPkgPath(service)
            os.makedirs(path)
        except Exception as excep:
            LOG.warning('got an OS Exception - %s' % str(excep))
  
  
        createManifest(self, packages, manifest1, service)
        createManifest(self, packages, manifest2, service)
  
        body = json.dumps({'manifest':manifest1})
        response1 = self.app.post(url(controller='manifest', action='activate', service=service, manifest=manifest1),
                                       headers = {'Content-Type' : 'application/json'},
                                       params = body)
        self.assertEquals(response1.status_int, 200, 'Manifest1 Post assert - should go through')
  
        body = json.dumps({'manifest':manifest2})
        try:
            response2 = self.app.post(url(controller='manifest', action='activate', service=service, manifest=manifest2),
                                       headers = {'Content-Type' : 'application/json'},
                                       params = body)
            self.assertFalse(True, 'Expected an exception but did not get one!')
        except AppError:
            pass
  
        checkStatus(self, 'activate manifest bar', response1, timeout=25)
        self.assertTrue(islink(os.path.join(manifestutil.manifestPath('foo', 'bar'), 'pkgA')))

