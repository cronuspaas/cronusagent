from agent.tests import *
from agent.lib.packagemgr import PackageMgr
import logging
import pylons
import shutil
import os

from agent.lib.agent_globals import stopAgentGlobals
from agent.lib.agent_globals import startAgentGlobals
from agent.tests.unit.test_util import commonSetup
from agent.tests.unit.test_util import commonTearDown

LOG = logging.getLogger(__name__)

class TestPackageMgr(TestController):

    def setUp(self):
        commonSetup()

    def tearDown(self):
        commonTearDown()

    def test_init(self):
        # test the init routine

        # make sure that the initial path is cleared out of IN Progress nodes
        tmpFile = os.path.join(PackageMgr.packagePath(), 'foo.inprogress')
        open(tmpFile, 'w').close()

        tmpFile2 = os.path.join(PackageMgr.packagePath(), 'foo2.inprogress')
        open(tmpFile2, 'w').close()

        stopAgentGlobals()
        startAgentGlobals()

        # we removed logic of clean up inprogress file
#        assert not os.path.exists(tmpFile)
#        assert not os.path.exists(tmpFile2)
