from agent.tests import *
import logging

from agent.tests.unit.test_util import commonSetup
from agent.tests.unit.test_util import commonTearDown
import re


LOG = logging.getLogger(__name__)

class TestValidateInternals(TestController):

    def setUp(self):
        commonSetup()

    def tearDown(self):
        commonTearDown()


    def test_password_masks(self):
        response = self.app.get(url('/agent/ValidateInternals.html'))
        assert response.status_int == 200, 'Agent validate internals pass'
        pattern = re.compile('.*password.*', re.MULTILINE|re.DOTALL)
        assert pattern.match(response.body) is None, 'Password is visible'

    def test_getlog(self):
        response = self.app.get(url('/agent/logs'))
        assert response.status_int == 200, 'Agent log page pass'
        response = self.app.get(url('/agent/logs/agent.log'))
        assert response.status_int == 200, 'Agent log detail page pass'

    def test_getagenthealth(self):
        response = self.app.get(url('/agent/agenthealth'))
        assert response.status_int == 200, 'Agent health page pass'

    def test_getmonitors(self):
        response = self.app.get(url('/agent/monitors'))
        assert response.status_int == 200, 'Agent monitors page pass'

    def test_getthreads(self):
        response = self.app.get(url('/agent/threads'))
        assert response.status_int == 200, 'Agent thread page pass'
