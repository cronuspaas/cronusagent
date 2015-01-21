from agent.lib import contextutils
import logging
from unittest import TestCase

LOG = logging.getLogger(__name__)

class TestContextUtils(TestCase):

    def testContextUtils(self):
        sc = SomeClass()
        contextutils.injectcontext(sc, {'guid':'test-guid'})
        assert contextutils.existcontext(sc, 'guid')
        assert not contextutils.existcontext(sc, 'guid1')
        assert contextutils.getcontext(sc, 'guid1', 'test-guid1') == 'test-guid1'
        assert contextutils.getcontext(sc, 'guid') == 'test-guid'
        contextutils.injectcontext(sc, {'guid':'new-guid'})
        assert contextutils.getcontext(sc, 'guid') == 'new-guid'
        assert contextutils.popcontext(sc, 'guid') == 'new-guid'
        assert not contextutils.existcontext(sc, 'guid')

class SomeClass():
    def __init__(self):
        pass
