from agent.tests import *
import pylons
import os
import time


from agent.tests.unit.test_util import createManifest
from agent.tests.unit.test_util import activateManifest
from agent.tests.unit.test_util import commonSetup
from agent.tests.unit.test_util import commonTearDown
from agent.lib.scheduler import ThreadedScheduler
from agent.lib.agent_globals import AGENT_HEALTH_VI_KEY
from agent.lib.agenthealth import AGENT_UNHEALTHY, AGENT_HEALTH_UNKNOWN, AGENT_HEALTHY


import logging
from agent.lib import agenthealth, utils
from agent.lib.agent_thread.activate_manifest import ActivateManifest
from agent.lib.agent_thread.threadmgr import NullThreadMgr
LOG = logging.getLogger(__name__)

def initMonitor():
    appGlobal = pylons.config['pylons.app_globals']
    appGlobal.agentMonitor._AgentMonitor__monitorTasks = {}
    appGlobal.agentMonitor._AgentMonitor__monitorValues = {}

def stopMonitor():
    appGlobal = pylons.config['pylons.app_globals']
    if (hasattr(appGlobal, 'monitorSch') and appGlobal.agentMonitor._AgentMonitor__monitorSch != None):
        appGlobal.agentMonitor._AgentMonitor__monitorSch.stop()

MONITOR_METRICS = {'cpuSystem': ['21', 1316595370.652194, 1316595370.652194], 'cpuUser' : ['17', 1316595370.651952, 1316595340.6134901], 'agentUsedFD' : ['13', 1316595208.1095159, 1316595208.1095159], 'usedFD' : ['1812', 1316595208.109374, 1316595208.109374], 'agentUsedMem' : ['1000', 1316595208.109374, 1316595208.109374]}

class TestMonitor(TestController):

    def setUp(self):
        commonSetup()
        path = os.path.realpath(__file__)
        self.scriptDir = os.path.join(os.path.dirname(path), 'scripts')

        appGlobal = pylons.config['pylons.app_globals']
        appGlobal.agentHealth = None

    def tearDown(self):
        commonTearDown()
        
    def testAgentThreadName(self):
        activateManifest = ActivateManifest(NullThreadMgr(), 'foo', 'bar')
        assert activateManifest.getName() == 'activate_manifest'

    def testEncryptKey(self):
        encryptedKey = utils.encrpyKey(os.path.join(self.scriptDir, 'encryptkey'), os.path.join(self.scriptDir, 'agent.pub'), 'test')
        print encryptedKey
        assert encryptedKey is not None

    def test_executeCommand_normal(self):
        appGlobal = pylons.config['pylons.app_globals']
        cmd = os.path.join(self.scriptDir, 'demoMonitor.sh')
        LOG.debug('cmd = %s' % cmd)

        result = appGlobal.agentMonitor._executeCommand(cmd)

        assert  {"key":"cpu", "value":"10%"}== result


    def test_executeCommand_error(self):
        appGlobal = pylons.config['pylons.app_globals']
        cmd = os.path.join(self.scriptDir, 'demoMonitor_error.sh')
        LOG.debug('cmd = %s' % cmd)

        result = appGlobal.agentMonitor._executeCommand(cmd)
        assert result is None

    def test_runMonitor_dummyservice(self):
        appGlobal = pylons.config['pylons.app_globals']
        service = 'dummy_service'
        monitorkey = (service, 'default')
        appGlobal.agentMonitor._AgentMonitor__monitorValues = {monitorkey: {}}

        try:
            cmd = os.path.join(self.scriptDir, 'demoMonitor.sh')
            appGlobal.agentMonitor._AgentMonitor__monitorMessages = {monitorkey: {cmd: []}}
            LOG.debug('cmd = %s' % cmd)

            appGlobal.agentMonitor._runMonitor('script', cmd, service, 'default', 10, ('10', {}, {}, None, None, None))

            assert 'cpu' in appGlobal.agentMonitor._AgentMonitor__monitorValues[monitorkey]
            assert '10%' == appGlobal.agentMonitor._AgentMonitor__monitorValues[monitorkey]['cpu'][0]
        finally:
            appGlobal.agentMonitor._AgentMonitor__monitorValues = {}

    def test_runMonitor_agentservice(self):
        appGlobal = pylons.config['pylons.app_globals']
        service = 'agent'
        monitorkey = ('agent', 'default')
        appGlobal.agentMonitor._AgentMonitor__monitorValues = {monitorkey: {}}

        try:
            cmd = os.path.join(self.scriptDir, 'demoMonitor.sh')
            appGlobal.agentMonitor._AgentMonitor__monitorMessages = {monitorkey: {cmd: []}}
            LOG.debug('cmd = %s' % cmd)

            appGlobal.agentMonitor._runMonitor('script', cmd, service, 'default', 10, ('10', {}, {}, None, None, None))

            assert 'cpu' in appGlobal.agentMonitor._AgentMonitor__monitorValues[monitorkey]
            assert '10%' == appGlobal.agentMonitor._AgentMonitor__monitorValues[monitorkey]['cpu'][0]
        finally:
            appGlobal.agentMonitor._AgentMonitor__monitorValues = {}


    def test_runMonitor_realappservice(self):
        appGlobal = pylons.config['pylons.app_globals']
        service = '.env.appservice.serviceinstancename'
        monitorkey = (service, 'default')
        appGlobal.agentMonitor._AgentMonitor__monitorValues = {monitorkey: {}}

        try:
            cmd = os.path.join(self.scriptDir, 'demoMonitor.sh')
            appGlobal.agentMonitor._AgentMonitor__monitorMessages = {monitorkey: {cmd: []}}
            LOG.debug('cmd = %s' % cmd)

            appGlobal.agentMonitor._runMonitor('script', cmd, service, 'default', 10, ('10', {}, {}, None, None, None))

            assert 'cpu' in appGlobal.agentMonitor._AgentMonitor__monitorValues[monitorkey]
            assert '10%' == appGlobal.agentMonitor._AgentMonitor__monitorValues[monitorkey]['cpu'][0]
        finally:
            appGlobal.agentMonitor._AgentMonitor__monitorValues = {}

    def test_runMonitor_error(self):
        appGlobal = pylons.config['pylons.app_globals']
        appGlobal.agentMonitor._AgentMonitor__monitorValues = {"service1": {}}

        try:
            cmd = os.path.join(self.scriptDir, 'demoMonitor_badkey.sh')
            LOG.debug('cmd = %s' % cmd)

            appGlobal.agentMonitor._runMonitor('script', cmd, 'service1', 'default', 10, ('10', {}, {}, None, None, None))

            assert 'cpu' not in appGlobal.agentMonitor._AgentMonitor__monitorValues['service1']
        finally:
            appGlobal.agentMonitor._AgentMonitor__monitorValues = {}

    def test_runMonitor_with_scheduler(self):
        appGlobal = pylons.config['pylons.app_globals']
        monitorkey = ('service1', 'default')
        appGlobal.agentMonitor._AgentMonitor__monitorValues = {monitorkey: {}}

        try:
            cmd = os.path.join(self.scriptDir, 'demoMonitor.sh')
            appGlobal.agentMonitor._AgentMonitor__monitorMessages = {monitorkey: {cmd: []}}
            LOG.debug('cmd = %s' % cmd)

            sheduler = ThreadedScheduler()
            sheduler.add_interval_task(appGlobal.agentMonitor._runMonitor, cmd, 0, 1, ['script', cmd, 'service1', 'default', 10, ('10', {}, {}, None, None, None)], None)
            sheduler.start()

            tm = time.time()
            while (tm + 3 > time.time()):
                if 'cpu' in appGlobal.agentMonitor._AgentMonitor__monitorValues[monitorkey]:
                    break
                time.sleep(0.1)

            assert 'cpu' in appGlobal.agentMonitor._AgentMonitor__monitorValues[monitorkey]
            assert '10%' == appGlobal.agentMonitor._AgentMonitor__monitorValues[monitorkey]['cpu'][0]
        finally:
            sheduler.stop()
            appGlobal.agentMonitor._AgentMonitor__monitorValues = {}

    def test_checkMonitorChanges_nochanges(self):

        appGlobal = pylons.config['pylons.app_globals']

        appGlobal.agentMonitor._AgentMonitor__monitorSch.stop()
        createManifest(self)
        activateManifest(self)

        appGlobal.agentMonitor._AgentMonitor__monitorValues = {'foo': {}}
        appGlobal.agentMonitor._AgentMonitor__monitorTasks = {'foo': ['bar', []]}
        appGlobal.agentMonitor.checkMonitorChanges()

        assert {'foo': {}} == appGlobal.agentMonitor._AgentMonitor__monitorValues
        assert {'foo': ['bar', []]} == appGlobal.agentMonitor._AgentMonitor__monitorTasks

    def test_checkMonitorChanges_delete(self):

        appGlobal = pylons.config['pylons.app_globals']

        stopMonitor()

        initMonitor()
        createManifest(self)
        activateManifest(self)

        appGlobal.agentMonitor._AgentMonitor__monitorValues = {('foo', 'default'): {}, ('zoo', 'default'): {}}
        appGlobal.agentMonitor._AgentMonitor__monitorTasks = {('foo', 'bar'): [], ('zoo', 'bar'): []}
        print '%s' % appGlobal.agentMonitor._AgentMonitor__monitorTasks.keys()
        appGlobal.agentMonitor.checkMonitorChanges()

        assert ('foo', 'default') in appGlobal.agentMonitor._AgentMonitor__monitorValues
        assert ('zoo', 'default') in appGlobal.agentMonitor._AgentMonitor__monitorValues
        LOG.debug('%s' % appGlobal.agentMonitor._AgentMonitor__monitorTasks.keys())
        assert ('foo', 'bar') in appGlobal.agentMonitor._AgentMonitor__monitorTasks
        assert ('zoo', 'default') not in appGlobal.agentMonitor._AgentMonitor__monitorTasks

    def test_agent_highDiskUsage_when_diskusage_exceeds_threshold(self):
        #import pdb; pdb.set_trace();
        disk_threshold = pylons.config['health_disk_usage_gc_threshold']
        if os.name == 'posix' :
            mount = pylons.config['agent_root']
            pylons.config['health_disk_usage_gc_threshold'] = 1

            isHighDiskUsage = agenthealth.needAggressiveGC(mount)
            self.assertEquals(isHighDiskUsage, True)
        pylons.config['health_disk_usage_gc_threshold'] = disk_threshold

    def test_agent_highDiskUsage_when_diskusage_not_exceeds_threshold(self):
        #import pdb; pdb.set_trace();
        disk_threshold = pylons.config['health_disk_usage_gc_threshold']
        if os.name == 'posix' :
            mount = pylons.config['agent_root']
            pylons.config['health_disk_usage_gc_threshold'] = 99

            isHighDiskUsage = agenthealth.needAggressiveGC(mount)
            self.assertEquals(isHighDiskUsage, False)
        pylons.config['health_disk_usage_gc_threshold'] = disk_threshold

    def healthfactor(self, total_disk, used_disk, fd_usage, mem_usage):
        disk_usage = agenthealth.getDiskUsagePercent(total_disk, used_disk)
        return {'disk-usage' : '%s / 90' % str(disk_usage), 'FD-usage' : '%s / 500' % str(fd_usage), 'mem-usage(KB)' : '%s / 200000' % str(mem_usage)}

    def mockGetDiskUsage(self, a, b):
        def mock(path):
            return a, b
        return mock

    def test_agent_healthy_when_under_threshold(self):
        appGlobal = pylons.config['pylons.app_globals']
#        appGlobal.agentMonitor._AgentMonitor__monitorValues[('agent', 'agentmon')] = {'cpuSystem': ['21', 1316595370.652194, 1316595370.652194], 'agentUsedFD' : ['13', 1316595208.1095159, 1316595208.1095159], 'usedFD' : ['1812', 1316595208.109374, 1316595208.109374], 'agentUsedMem' : ['1000', 1316595208.109374, 1316595208.109374]}
        metrics = {}
        metrics.update(MONITOR_METRICS)
        appGlobal.agentMonitor._AgentMonitor__monitorValues[('agent', 'agentmon')] = metrics
        agenthealth.getDiskUsage = self.mockGetDiskUsage(10286376, 8476612)

        appGlobal.agentMonitor.checkAgentHealth()

        self.assertAgentHealthiness(AGENT_HEALTHY, self.healthfactor(10286376, 8476612, 13, 1000), 'Agent should be healthy as values are under threshold')

    def test_agent_healthy_when_diskusage_exceeds_threshold(self):
        appGlobal = pylons.config['pylons.app_globals']
#        appGlobal.agentMonitor._AgentMonitor__monitorValues[('agent', 'agentmon')] = {'cpuSystem': ['21', 1316595370.652194, 1316595370.652194], 'cpuUser' : ['17', 1316595370.651952, 1316595340.6134901], 'agentUsedFD' : ['13', 1316595208.1095159, 1316595208.1095159], 'usedFD' : ['1812', 1316595208.109374, 1316595208.109374], 'agentUsedMem' : ['1000', 1316595208.109374, 1316595208.109374]}
        metrics = {}
        metrics.update(MONITOR_METRICS)
        appGlobal.agentMonitor._AgentMonitor__monitorValues[('agent', 'agentmon')] = metrics
        agenthealth.getDiskUsage = self.mockGetDiskUsage(10286376, 9976612)

        appGlobal.agentMonitor.checkAgentHealth()

        self.assertAgentHealthiness(AGENT_HEALTHY, self.healthfactor(10286376, 9976612, 13, 1000), 'Agent should be healthy as disk usage is beyond threshold')

    def test_agent_unhealthy_when_fdusage_exceeds_threshold(self):
        appGlobal = pylons.config['pylons.app_globals']
#        appGlobal.agentMonitor._AgentMonitor__monitorValues[('agent', 'agentmon')] = {'cpuSystem': ['21', 1316595370.652194, 1316595370.652194], 'cpuUser' : ['17', 1316595370.651952, 1316595340.6134901], 'agentUsedFD' : ['513', 1316595208.1095159, 1316595208.1095159], 'usedFD' : ['1812', 1316595208.109374, 1316595208.109374]}
        metrics = {}
        metrics.update(MONITOR_METRICS)
        metrics['agentUsedFD'] = ['513', 1316595208.1095159, 1316595208.1095159]
        appGlobal.agentMonitor._AgentMonitor__monitorValues[('agent', 'agentmon')] = metrics
        agenthealth.getDiskUsage = self.mockGetDiskUsage(10286376, 8476612)

        appGlobal.agentMonitor.checkAgentHealth()

        self.assertAgentHealthiness(AGENT_UNHEALTHY, self.healthfactor(10286376, 8476612, 513, 1000), 'Agent should be unhealthy as FD usage is beyond threshold')

    def test_agent_unhealthy_when_memusage_exceeds_threshold(self):
        appGlobal = pylons.config['pylons.app_globals']
#        appGlobal.agentMonitor._AgentMonitor__monitorValues[('agent', 'agentmon')] = {'cpuSystem': ['21', 1316595370.652194, 1316595370.652194], 'cpuUser' : ['17', 1316595370.651952, 1316595340.6134901], 'agentUsedFD' : ['513', 1316595208.1095159, 1316595208.1095159], 'usedFD' : ['1812', 1316595208.109374, 1316595208.109374]}
        metrics = {}
        metrics.update(MONITOR_METRICS)
        metrics['agentUsedMem'] = ['1005000', 1316595208.1095159, 1316595208.1095159]
        appGlobal.agentMonitor._AgentMonitor__monitorValues[('agent', 'agentmon')] = metrics
        agenthealth.getDiskUsage = self.mockGetDiskUsage(10286376, 8476612)

        appGlobal.agentMonitor.checkAgentHealth()

        self.assertAgentHealthiness(AGENT_UNHEALTHY, self.healthfactor(10286376, 8476612, 13, 1005000), 'Agent should be unhealthy as Mem usage is beyond threshold')

    def test_agent_health_unknown_upon_one_diskusage_metric_unavailablity(self):
        appGlobal = pylons.config['pylons.app_globals']
#        appGlobal.agentMonitor._AgentMonitor__monitorValues[('agent', 'agentmon')] = {'cpuSystem': ['21', 1316595370.652194, 1316595370.652194], 'cpuUser' : ['17', 1316595370.651952, 1316595340.6134901], 'agentUsedFD' : ['13', 1316595208.1095159, 1316595208.1095159], 'usedFD' : ['1812', 1316595208.109374, 1316595208.109374]}
        metrics = {}
        metrics.update(MONITOR_METRICS)
        appGlobal.agentMonitor._AgentMonitor__monitorValues[('agent', 'agentmon')] = metrics
        agenthealth.getDiskUsage = self.mockGetDiskUsage(10286376, None)

        appGlobal.agentMonitor.checkAgentHealth()

        self.assertAgentHealthiness(AGENT_HEALTH_UNKNOWN, {}, 'Agent health should be unknown as a required disk metric is missing')

    def test_agent_health_unknown_upon_another_diskusage_metric_unavailablity(self):
        appGlobal = pylons.config['pylons.app_globals']
#        appGlobal.agentMonitor._AgentMonitor__monitorValues[('agent', 'agentmon')] = {'cpuSystem': ['21', 1316595370.652194, 1316595370.652194], 'cpuUser' : ['17', 1316595370.651952, 1316595340.6134901], 'agentUsedFD' : ['13', 1316595208.1095159, 1316595208.1095159], 'usedFD' : ['1812', 1316595208.109374, 1316595208.109374]}
        metrics = {}
        metrics.update(MONITOR_METRICS)
        appGlobal.agentMonitor._AgentMonitor__monitorValues[('agent', 'agentmon')] = metrics
        agenthealth.getDiskUsage = self.mockGetDiskUsage(None, 8476612)

        appGlobal.agentMonitor.checkAgentHealth()

        self.assertAgentHealthiness(AGENT_HEALTH_UNKNOWN, {}, 'Agent health should be unknown as a required disk metric is missing')

    def test_agent_health_unknown_upon_invalid_diskusage_metric(self):
        appGlobal = pylons.config['pylons.app_globals']
#        appGlobal.agentMonitor._AgentMonitor__monitorValues[('agent', 'agentmon')] = {'cpuSystem': ['21', 1316595370.652194, 1316595370.652194], 'cpuUser' : ['17', 1316595370.651952, 1316595340.6134901], 'agentUsedFD' : ['13', 1316595208.1095159, 1316595208.1095159], 'usedFD' : ['1812', 1316595208.109374, 1316595208.109374]}
        metrics = {}
        metrics.update(MONITOR_METRICS)
        appGlobal.agentMonitor._AgentMonitor__monitorValues[('agent', 'agentmon')] = metrics
        agenthealth.getDiskUsage = self.mockGetDiskUsage(10286376, 'NA')

        appGlobal.agentMonitor.checkAgentHealth()

        self.assertAgentHealthiness(AGENT_HEALTH_UNKNOWN, {}, 'Agent health should be unknown as a required disk metric is invalid')

    def test_agent_health_unknown_upon_invalid_fdusage_metric(self):
        appGlobal = pylons.config['pylons.app_globals']
#        appGlobal.agentMonitor._AgentMonitor__monitorValues[('agent', 'agentmon')] = {'cpuSystem': ['21', 1316595370.652194, 1316595370.652194], 'agentUsedFD' : ['NA', 1316595208.1095159, 1316595208.1095159], 'usedFD' : ['1812', 1316595208.109374, 1316595208.109374], 'agentUsedMem' : ['1000', 1316595208.109374, 1316595208.109374]}
        metrics = {}
        metrics.update(MONITOR_METRICS)
        metrics['agentUsedFD'] = ['NA', 1316595208.1095159, 1316595208.1095159]
        appGlobal.agentMonitor._AgentMonitor__monitorValues[('agent', 'agentmon')] = metrics
        agenthealth.getDiskUsage = self.mockGetDiskUsage(10286376, 8476612)

        appGlobal.agentMonitor.checkAgentHealth()

        self.assertAgentHealthiness(AGENT_HEALTH_UNKNOWN, None, 'Agent health should be unknown as a required FD usage metric is invalid')

    def test_agent_health_unknown_upon_invalid_memusage_metric(self):
        appGlobal = pylons.config['pylons.app_globals']
#        appGlobal.agentMonitor._AgentMonitor__monitorValues[('agent', 'agentmon')] = {'cpuSystem': ['21', 1316595370.652194, 1316595370.652194], 'agentUsedFD' : ['NA', 1316595208.1095159, 1316595208.1095159], 'usedFD' : ['1812', 1316595208.109374, 1316595208.109374], 'agentUsedMem' : ['1000', 1316595208.109374, 1316595208.109374]}
        metrics = {}
        metrics.update(MONITOR_METRICS)
        metrics['agentUsedMem'] = ['NA', 1316595208.1095159, 1316595208.1095159]
        appGlobal.agentMonitor._AgentMonitor__monitorValues[('agent', 'agentmon')] = metrics
        agenthealth.getDiskUsage = self.mockGetDiskUsage(10286376, 8476612)

        appGlobal.agentMonitor.checkAgentHealth()

        self.assertAgentHealthiness(AGENT_HEALTH_UNKNOWN, None, 'Agent health should be unknown as a required FD usage metric is invalid')

    def test_agent_health_unknown_upon_unexpected_exception(self):

        appGlobal = pylons.config['pylons.app_globals']
        appGlobal.agentMonitor._AgentMonitor__monitorValues = None # this will cause a abnormal exception
        agenthealth.getDiskUsage = self.mockGetDiskUsage(10286376, 8476612)

        appGlobal.agentMonitor.checkAgentHealth()

        self.assertAgentHealthiness(AGENT_HEALTH_UNKNOWN, {}, 'Agent health should be unknown bcz of unexpected exception')

    def assertAgentHealthiness(self, exp_health, exp_healthfactor, err_msg):
        appGlobal = pylons.config['pylons.app_globals']
        found = False

        self.assertEquals(exp_health, appGlobal.agentHealth, err_msg)
        if exp_healthfactor:
            self.assertEquals(exp_healthfactor, appGlobal.agentHealthFactor)
        stat = appGlobal.metrixManager.getStatus()
        for (key, value) in stat:
            if key == AGENT_HEALTH_VI_KEY:
                found = True
                self.assertEquals(exp_health, value, err_msg)
                break
        self.assertTrue(found, 'Agent health status attribute not even set/present in VI?')

class MockStateServerClient:
    def __init__(self):
        self.entities = None
        self.hostname = None

    def queryEntities(self, paths, properties=None, limit=-1, skip=0, sortOn=None,
                      sortOrder='asc', showMeta=False, explain=False):
        return self.entities

    def updateEntities(self, entities):
        if self.entities is None:
            self.entities = entities
        elif entities is not None:
            for idx, entity in enumerate(entities):
                for key, prop in entity.properties.items():
                    if prop is not None:
                        self.entities[idx].properties[key] = prop

    def setMockEntities(self, mockEntities):
        self.entities = mockEntities

    def isCurrentManifest(self, manifests):
        if (self.entities == None):
            return False

        for entity in self.entities:
            print "manifest:" + str(manifests)
            print "manifest prop:" + str(entity.properties['manifest-cur'])
            if (entity.properties['manifest-cur'].value == manifests):
                return True

        return False

    def isActiveManifest(self, manifest):
        if (self.entities == None):
            return False

        for entity in self.entities:
            if (entity.properties['active-manifest-cur'].value == manifest):
                return True

        return False

    def isActiveManifestWisb(self, manifest):
        if (self.entities == None):
            return False

        for entity in self.entities:
            if (entity.properties['active-manifest-ref'].value == manifest):
                return True

        return False

    def isCurrentManifestWisb(self, manifests):
        if (self.entities == None):
            return False

        for entity in self.entities:
            print "manifest:" + str(manifests)
            print "manifest prop:" + str(entity.properties['manifest-ref'])
            if (entity.properties['manifest-ref'].value == manifests):
                return True

        return False

    def hasProperty(self, propertyName):
        if self.entities == None:
            return False

        for entity in self.entities:
            if propertyName in entity.properties.keys():
                return True

        return False

    def isCurrentData(self, dataCur):
        return self.checkArrProp('dataCur', dataCur)

#    def isActiveData(self, dataActive):
#        return self.checkArrProp('dataActiveCur', dataActive)

    def isCurrentStream(self, streamCur):
        return self.checkArrProp('dataStreamCur', streamCur)

    def isCurrentDatagroup(self, datagroupCur):
        return self.checkArrProp('dataGroupCur', datagroupCur)

    def isActiveDatagroup(self, datagroupActive):
        return self.checkArrProp('dataGroupActiveCur', datagroupActive)

    def checkArrProp(self, propName, data):
        if (self.entities == None):
            return False

        for entity in self.entities:
            if self._checkArrayEquals(entity.properties[propName].value, data):
                return True

        return False

    def _checkArrayEquals(self, arr1, arr2):
        if len(arr1) != len(arr2):
            return False

        try:
            for one_element in arr1:
                if arr2.index(one_element) >= 0:
                    continue
        except ValueError:
            return False

        return True


