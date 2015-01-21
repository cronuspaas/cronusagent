from agent.tests import *
import pylons
import os
import shutil
import logging
import time
import json
import platform
import socket

from agent.lib.agent_thread.threadmgr import ThreadMgr
from agent.lib.agent_globals import stopAgentGlobals
from agent.lib.agent_globals import startAgentGlobals
from agent.lib.errors import Errors
from agent.controllers.manifest import ManifestController
from agent.controllers.service import ServiceController
from agent.lib.utils import symlink
from agent.lib.utils import rchown

from agent.tests.unit.test_util import createManifest, activateManifest
from agent.tests.unit.test_util import commonSetup
from agent.tests.unit.test_util import commonTearDown
from agent.lib import manifestutil, configutil, utils

LOG = logging.getLogger(__name__)

class TestServiceController(TestController):

    def setUp(self):
        commonSetup()

    def tearDown(self):
        commonTearDown()

    def testPost(self):
        LOG.debug('config:' + str(pylons.config))

        LOG.debug('************ first post')
        response = self.app.post(url(controller='service', service='foo', action='post'))

        # make sure the responses are correct
        LOG.debug('status = ' + str(response.status_int))

        assert response.status_int == 200, "HTTP response != 200"
        path = os.path.join(pylons.config['agent_root'], 'service_nodes', 'foo')
        assert os.path.isdir(path), 'service foo does not exist or is not a directory'

        # test re-post
        LOG.debug('************ second post')
        response = self.app.post(url = url(controller='service', service='foo', action='post'), expect_errors = True)

        LOG.debug('status = ' + str(response.status_int))
        LOG.debug('body = ' + response.body)
        assert response.status_int == 201, "HTTP response != 201"

        assert os.path.isdir(path), 'service foo does not exist or is not a directory'
        assert os.path.isdir(os.path.join(path, 'manifests')), 'service foo does not exist or is not a directory'
        assert os.path.isdir(os.path.join(path, 'installed-packages')), 'service foo does not exist or is not a directory'

    def testList(self):
        LOG.debug('************ post foo')
        response = self.app.post(url(controller='service', service='foo', action='post'))
        assert response.status_int == 200, "HTTP response != 200"

        LOG.debug('************ post bar')
        response = self.app.post(url(controller='service', service='bar', action='post'))
        assert response.status_int == 200, "HTTP response != 200"

        LOG.debug('************ get services')
        response = self.app.get(url(controller='service', action='listServices'))
        assert response.status_int == 200, "HTTP response != 200"
        body = json.loads(response.body)
        LOG.debug('****** result = %s', str(body))
        assert body['result'] == ["bar", "foo"]

    def testGetNonExistent(self):
        response = self.app.get(url(controller='service', service='foo', action='delete'), expect_errors = True)

        body = json.loads(response.body)
        LOG.debug('error = %s' % str(body['error']))
        assert body['error'] == Errors.SERVICE_NOT_FOUND

    def testDelete(self):
        path = os.path.join(pylons.config['agent_root'], 'service_nodes', 'foo')

        LOG.debug('************ path = %s' % path)
        LOG.debug('************ first delete')
        response = self.app.delete(url(controller='service', service='foo', action='delete'), expect_errors = True)

        # make sure the responses are correct
        LOG.debug('status = ' + str(response.status_int))
        assert response.status_int == 500, "HTTP response != 500"

        os.makedirs(path)
        os.makedirs(os.path.join(path, 'manifest'))
        os.makedirs(os.path.join(path, 'installed-packages'))

        uname = configutil.getAgentUser()
        uid, gid = utils.getUidGid(uname)
        rchown(path, uid, gid)

        LOG.debug('************ second delete')
        response = self.app.delete(url(controller='service', service='foo', action='delete'))
        LOG.debug ('Delete response body = ' + response.body)
        body = json.loads(response.body)

        tm = time.time()
        while (tm + 5 > time.time()):
            response = self.app.get(body['status'], expect_errors = True)
            LOG.debug ('Status response body = ' + response.body)
            body = json.loads(response.body)
            if (body['progress'] == 100):
                break

        # make sure the responses are correct
        LOG.debug('status = ' + str(response.status_int))
        assert response.status_int == 200, "HTTP response != 200"

        assert not os.path.exists(path), 'service foo does exist or is not a directory'

    def testDelete2(self):
        createManifest(self)

        # need to change the owner of the service dir to be cronus

        servicePath = ServiceController.servicePath('foo')
        uname = configutil.getAgentUser()
        uid, gid = utils.getUidGid(uname)
        rchown(servicePath, uid, gid)


        response = self.app.delete(url(controller='service', service='foo', action='delete'))
        assert response.status_int == 200, "HTTP response != 200"

        body = json.loads(response.body)
        tm = time.time()
        while (tm + 5 > time.time()):
            response = self.app.get(body['status'], expect_errors = True)
            LOG.debug ('*************  Status response body = ' + response.body)
            body = json.loads(response.body)
            if (body['progress'] == 100):
                break

        assert not os.path.isdir(ServiceController.servicePath('foo'))

    def testGet(self):
        path = manifestutil.manifestPath('foo', 'bar')
        os.makedirs(path)

        path = manifestutil.manifestPath('foo', 'baz')
        os.makedirs(path)

        activePath = os.path.join(ServiceController.manifestPath('foo'), 'active')
        symlink('bar', activePath)

        response = self.app.get(url(controller='service', service='foo', action='get'), expect_errors = True)

        body = json.loads(response.body)
        print "************** response = %s" % body

        assert body['progress'] == 100
        assert body['result']['activemanifest'] == 'bar'
        assert body['result']['manifest'] == ['bar', 'baz']

    def testExpandService(self):
        createManifest(self, service='.fooenv.foopool.foo')
        response = self.app.get(url(controller='service', service='.fooenv.foopool', action='get'), expect_errors = True)

        body = json.loads(response.body)
        print "************** response = %s" % body

        assert body['progress'] == 100
        assert body['result']['manifest'] == ['bar']

        response = self.app.get(url(controller='service', service='.fooenv.foopool.foo', action='get'), expect_errors = True)

        body = json.loads(response.body)
        print "************** response = %s" % body

        assert body['progress'] == 100
        assert body['result']['manifest'] == ['bar']

        response = self.app.get(url(controller='service', service='.fooenv', action='get'), expect_errors = True)

        body = json.loads(response.body)
        print "************** response = %s" % body

        assert response.status_int == 500, "HTTP response != 500"

    def testServiceLog(self):
        createManifest(self, service='foo')
        activateManifest(self, service='foo')
        response = self.app.get('/services/foo/action/log', expect_errors = True)

        assert response.status_int == 200, "HTTP response != 200"

