'''
Created on Dec 22, 2011

@author: biyu
'''
import json
import os

from agent.lib import package, utils, manifestutil
from subprocess import Popen, PIPE
import sys
import re
from agent.lib.agent_thread.download_thread import DownloadThread
from agent.lib.agent_thread.download_helper import DownloadHelper
import socket
import urlparse
import ConfigParser
from agent.lib.agent_thread.exec_thread import ExecThread
from agent.lib.agent_thread.threadmgr import NullThreadMgr
from agent.lib.errors import AgentException
import time
#from stateserverclient.state_server_client import StateServerClient
import base64
import uuid

ERROR = '''{"errorMsg": "service.eba deployment failed!<br><br> "}'''


if __name__ == '__main__':
    
    apistr = """Route name Methods Path                                                          
                   /error/{action}                                               
                   /error/{action}/{id}                                          
           GET     /services/                                                    
           GET     /services                 """
    
    import re
    apis = apistr.splitlines()
    result = map(lambda x: x.strip(), apis)
    print json.dumps(result) 

    dictstr = '{}'
    dictstr = '{"http": "slcgpaas3002a.com:8080"}'
    proxies = json.loads(dictstr)
    print proxies
    
    
    userInput = raw_input("Enter something: ")
    print userInput
    
    print base64.encodestring('96084a36-37a3-4c64-a048-b5eb7be7ed59')
    
    pubKeyFiles = [f for f in os.listdir('.') if re.match(r'.*\.pyc', f)]
    print pubKeyFiles
    
    map = json.loads('{"errorMsg": "Apache startup failed: -1 No such file or directory"}')
    
    authztoken = str(uuid.uuid5(uuid.NAMESPACE_X500, 'agent'))
    print authztoken
    
    authztoken = str(uuid.uuid4())
    print authztoken

    base64string = base64.encodestring('%s:%s' % ('agent', 'toyagent'))[:-1]
    print base64string
    
    path = '/ENVhro7bjz48qu4b' 
    propSet = ['odbMoName', 'cronusType', 'label', 'classOfService']
    prefix = ''
    result = {}
    
    monitorTags = {}
    monitorTags['agent'] = {'default' : (1,2,3,4,5)}
    print "agent" in monitorTags and "default" in monitorTags['agent']
    
    print 'default' == "default"
    pkgName = 'test'
    forcePackages = None
    exist = ((forcePackages is not None) and (pkgName in forcePackages))
    print exist
    
    import re
    pkgSuffix = re.sub(r"\W", "", "mymanifest-1.0.0")
    print pkgSuffix

    for _ in range(3):
        print 3 ** (1+_)
    
    print int(time.time()) % 2
    
    response = json.loads(ERROR)
    isValid = ExecThread.validateResponse(response)
    
    errorMsgRe = re.compile('.*errorMsg\".*:.*\"(.*)\"}')
    match = errorMsgRe.match(ERROR)
    if (match != None):
        errorMsg = match.group(1)
    
    errorlines = ERROR.split('\n')
    errorjoin = None
    ethread = ExecThread(NullThreadMgr, 'agent')
    for line in errorlines:
        ethread.processExecResponse(line)
        line = line.rstrip('\n')
        errorjoin = line if not errorjoin else (errorjoin + '\\n' + line)
    threadjson = ethread.getResponse()
    
    exc = AgentException('1', 'test');
    errorMsg = exc.getMsg()
    
    
    config = ConfigParser.RawConfigParser()
    config.read('fact.prop')
    
    env_vs = 'CRONUSAPP_HOME=%s LCM_CORRELATIONID=%s'.split(' ')
    text = 'some'
    text1 = text.split()
    
    lines = ['line1', 'line2', 'line3']
    for line in lines:
        print line
    arch = 'r1'.split(',')
    print 'r1' in arch
    headers = {"Authorization": "Basic YWdlbnQ6dG95YWdlbnQ=", "content-type": "application/json"}
    
    cmdlock = {}
    cmdlock.pop('nothere', None)
    cmdlock['test'] = None
    del cmdlock['test']
    print os.path.join('service', 'stream', '0006698_120816234927213_oozie_oozi_W_cassini_full_index', '201208290600001002.0.0.0_8_unix')
    print socket.getfqdn()

    apps = 'r1'
    arch = None
    apps_need_cleanup = apps.split(',')
    print arch in apps_need_cleanup
    from agent.lib.agent_thread.agent_thread import AgentThread
    print issubclass(DownloadHelper, AgentThread)
    print True != False
    parts = '.ENV2bvkjbombf.glohdr-app__ENV2bvkjbombf.glohdr-app__ENV2bvkjbombf-PHX__PHX02-CLh3nf932l-00001'.split('.', 3)
    print parts
    print ('None<10? %s' % (None < 10))
    print ('print int as string? %s' % 10)
    
    pkg1, pkg2, pkg3 = 'test1', \
                        'test2', \
                        'test3'
    
    nameRe = re.compile('((([a-zA-Z0-9_]+)-(([0-9]+)\.([0-9]+)\.([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)))\.cronus)(\.torrent)?')
    match = nameRe.match('cassini_beta2_index-2012032000001002.0.0.0_39_unix.cronus.torrent')
    print (match == None or match.group(0) != 'python_package-1.0.0.ubuntu11.cronus')
    print match == None
    print match.group(0)
    
    
#    print os.getcwd()
#    print os.path.join(os.getcwd(), 'testdummy.py')
#    print os.path.dirname(os.path.join(os.getcwd(), 'testdummy.py'))
#    
#    ht.start()
#    ht.join(5)
#    status = ht.getStatus()
#    error = status['error']
#    result = status['result']
#    jresult = json.loads(status['result'])
#        
#    ini = helpers.loadData(os.path.abspath(os.path.join('../../../cronus', 'cronus.ini')))
#    cur_env = os.environ
#    cur_env['TEST_VAR'] = 'HELLO'
#    p = Popen('', env = cur_env, stdout=PIPE, stderr=PIPE)
#    stdout, stderr = p.communicate()
#    msg = ''
#    if(len(stdout) != 0):
#        msg += 'Standard o/p:\n' + stdout + '\n'
#    if(len(stderr) != 0):
#        msg += 'Err msg gotten:\n' + stderr
#    kvmaps = [{'cronusType':'environment','odbMoName':'ENVc9ybyuqndn','classOfService':'QA','label':'Fashion-QA2'},
#              {'cronusType':'applicationservice','odbMoName':'testcos'}]
#    print json.dumps(kvmaps)

