from unittest import TestCase
from agent.lib.utils import synchronized, synchronizedInst,trackable
from threading import Lock, Thread
import threading
from agent.lib import contextutils, utils
import pylons
import os
from agent.tests.unit.test_util import commonTearDown, commonSetup

counter = 0

class TestAgentUtils(TestCase):

    def testNestedDictStr(self):
        data = {'key': 'value', 
                'key1': ['avalue1', 'avalue2'],
                'key2': {'key3': 'dvalue1',
                         'key4': ['avalue3', 'avalue4']}
                }
        result = utils.nestedDictStr(data)
        print result
    
    def testGetUserOfPath(self):
        basepath = pylons.config['agent_root']
        assert(utils.getuserofpath(basepath) is not None)

    def testValidateLink(self):
        commonTearDown()
        commonSetup()
        basepath = pylons.config['agent_root']
        badpath = os.path.join(basepath, 'not_exist')
        goodpath = os.path.join(basepath, 'packages')
        badlink = os.path.join(basepath, 'bad_link')
        goodlink = os.path.join(basepath, 'good_link')

        utils.symlink(badpath, badlink)
        assert(utils.validatelink(badlink) == False)
        utils.symlink(goodpath, goodlink)
        assert(utils.validatelink(goodlink) == True)


    def testSynchronizedFunc(self):
        global counter
        size = 10
        counter = 0
        threads = []
        for i in range(size):
            t = Thread(target=doSomething, args=['something %d' % i])
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
        assert counter == size

    def testSynchronizedInst(self):
        global counter
        size = 10
        counter = 0
        threads = []
        for j in range(size):
            sc = SomeClass('something else %d' % j)
            threads.append(sc)
            sc.start()
        for t in threads:
            t.join()
        assert counter == size

    def testtrackable(self):
        global counter
        counter = 0
        sc = SomeClass()
        contextutils.injectcontext(sc, {'guid':'test-guid'})
        evttrackerpath = 'test-path'
        contextutils.injectcontext(sc, {'evt_tracker_path':evttrackerpath+'.agent'})
        contextutils.injectcontext(sc, {'calbody':'more message'})
        sc.doSomething()
        assert counter == 1
        doSomething('something')
        assert counter == 2
        try:
            sc.doSomethingElse('somethingelse')
            assert False
        except Exception as ex:
            assert 'somethingelse' == str(ex)
        assert counter == 3

class SomeClass(threading.Thread):

    def __init__(self, someParam=None):
        Thread.__init__(self)
        self.__someParam = someParam

    def run(self):
        self.doSomething()

    @synchronizedInst
    @trackable()
    def doSomething(self):
        """This method can only be entered
            by one thread at a time"""
        global counter
        counter += 1

    @trackable()
    def doSomethingElse(self, value):
        global counter
        try:
            raise Exception(value)
        finally:
            counter += 1

__lock = Lock()

@synchronized(__lock)
@trackable()
def doSomething(someParam):
    """This method can only be entered
        by one thread at a time"""
    global counter
    counter = counter + 1
    return someParam
