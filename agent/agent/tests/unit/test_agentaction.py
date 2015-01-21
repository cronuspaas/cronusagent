from agent.lib import agenthealth, utils
from agent.tests import TestController
from agent.tests.unit.test_util import commonSetup, commonTearDown
import logging

LOG = logging.getLogger(__name__)

class TestActionController(TestController):


    def setUp(self):
        commonSetup()

    def tearDown(self):
        commonTearDown()
        
    def test_get_linux_distro(self):
        linux_distro = utils.get_linux_distro()
        assert linux_distro is not None

    def test_load_version(self):
        wiri = agenthealth.loadVersion()
        assert wiri is not None
        
    def test_check_agent_version_startup(self):
        agenthealth.checkAgentVersion(True)
