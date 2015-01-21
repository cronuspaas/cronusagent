#pylint: disable=R0912,R0915,R0904,E1101,R0914,W0105
""" thread for task execution """
import subprocess
import json
import re
import time
import traceback
import os
import select

from agent.lib.agent_thread.agent_thread import AgentThread
from agent.lib.errors import Errors
from pylons import config

import logging
from agent.lib import manifestutil, contextutils, utils, serviceutil
OUTPUTLOG = logging.getLogger('execoutput')

class ExecThread(AgentThread):
    """ This thread will exec a script and track progress
    """

    outputRe = re.compile('.*\[AGENT_MESSAGE\](.*)')
    outputEndRe = re.compile('(.*)\[AGENT_MESSAGE_END\].*')
    errorMsgRe = re.compile('.*errorMsg\".*:.*\"(.*)\"}')
    progMsgRe = re.compile('^\s*(\+?)(\d+\.?\d*)\s*$')

    def __init__(self, threadMgr, cmd, cat = None, parentId = None):
        """ Constructor.
        @param threadMgr - the thread Mgr object
        @param cmd - cmd list
        @param timeout - amount of time we give to this thread
        """
        AgentThread.__init__(self, threadMgr, cat, name = 'exec_thread', parentId = parentId)

        self.__cmd = cmd
        
        # default timeouts configuration
        self._timeout = int(config['exec_thread_timeout'])
        self._progressTimeout = int(config['exec_thread_progress_timeout'])
        self.__service = None
        self.__cmdProcess = None
        self.__response = {}
        self.__partial_response = None
        self.__partial = ''
        self.__outputlines = []
        self.__injectctx = True
        self.__logLevel = 'info'
        self.__LOG = None

    def setLogLevel(self, level):
        """ change log level on the fly """
        self.__logLevel = level
        
    def setInjectctx(self, value):
        """ injectctx property """
        self.__injectctx = value
        
    def __needSudo(self):
        """ check if the script need sudo
            @return: (True|False, sudo target user|None)
        """
        cmd = str(self.__cmd).split(' ') if isinstance(self.__cmd, basestring) else self.__cmd
        cmd_0 = cmd[0]
        needSudo = (cmd_0 == 'sudo')
        user = None
        if needSudo:
            for idx, cmd_n in enumerate(cmd):
                if '-u' == cmd_n:
                    user = cmd[idx + 1]
                    break
        return (needSudo, user)

    def processExecResponse(self, line):
        """ take script output and map it to agent response, support script communication with agent """
        line = line.rstrip('\n')
        line = line.rstrip(' ')

        can_clear = False
        matched_sofar = None
        try:

            if not self.__partial_response:
                
                # match start of output pattern
                match = ExecThread.outputRe.match(line)
                if (match != None):
                    matched_sofar = match.group(1) if match.group(1) else ' '
                    
            # we have partial agent message response from previous lines
            if self.__partial_response or matched_sofar:
                # match end of output pattern
                match = ExecThread.outputEndRe.match(matched_sofar if matched_sofar else line)
                if match != None:
                    can_clear = True
                    matchStr = match.group(1) if match.group(1) else ''
                    if self.__partial_response:
                        self.__partial_response = self.__partial_response + matchStr 
                    else:
                        self.__partial_response = matchStr 

                elif matched_sofar:
                    if self.__partial_response:
                        self.__partial_response = self.__partial_response + matched_sofar 
                    else:
                        self.__partial_response = matched_sofar 
                    
                else:
                    self.__partial_response = self.__partial_response + line
                    

            if self.__partial_response and can_clear:

                response = {}
                
                # look for simple progress reporting pattern (+)00.0
                progMatch = ExecThread.progMsgRe.match(self.__partial_response) 
                if progMatch != None:
                    if progMatch.group(1):
                        # +x.y 
                        self._incProgress(float(progMatch.group(2)), 99)
                    else:
                        self._updateProgress(float(progMatch.group(2)), 99)
                # or full json type response {progress:.., result:...}
                else:
                    try:
                        response = json.loads(self.__partial_response)
                    except ValueError as excep:
                        self.__LOG.error('Invalid response(%s) %s - %s' % (self.__cmd, str(excep), traceback.format_exc(2)))
                        errorMatch = ExecThread.errorMsgRe.match(self.__partial_response)
                        if (errorMatch != None):
                            errorMsg = errorMatch.group(1)
                            response['errorMsg'] = errorMsg

                    if (not ExecThread.validateResponse(response)):
                        self.__LOG.warning('partial response not valid %s' % response)
                        return
                    
                # store away the response for later
                self.__response.update(response)

                # update the progress
                if 'progress' in self.__response:   
                    self._updateProgress(self.__response['progress'], 99)

        finally:
            if can_clear:
                self.__partial_response = None

    def getResponse(self):
        ''' get temp response '''
        return self.__response

    ##############################################################
    # Thread Running Methods
    ##############################################################

    def beforeRun(self):
        """ set external timeout values if any """
        # set timeout
        if contextutils.existcontext(self, 'thread_timeout'):
            self._timeout = contextutils.getcontext(self, 'thread_timeout', self._timeout)
        
        if contextutils.existcontext(self, 'thread_progress_timeout'):
            self._progressTimeout = contextutils.getcontext(self, 'thread_progress_timeout', self._progressTimeout)
        
    
    def doRun(self):
        """ run - exec the thread and parse the results """
        display_cmd = ''
        outputLogged = False
        try:
            serviceFromPath = manifestutil.serviceFromPath(self.__cmd, 'agent')
            self.__service = contextutils.getcontext(self, 'service', serviceFromPath)
            self.__LOG = manifestutil.getServiceLogger(self, logging.getLogger(__name__), self.__service)
            
            self.log("Exec Thread running, cmd=%s" % self.__cmd)
            closeFds = readall = True
            
            # context injection via environment variables
            if self.__injectctx:
                cronusapp_home = str(manifestutil.servicePath(self.__service))
                correlation_id = str(contextutils.getcontext(self, 'guid', ''))
                authz_token = str(contextutils.getcontext(self, 'authztoken', ''))
                env_variables = 'SERVICE_NAME=%s CRONUSAPP_HOME=%s CORRELATIONID=%s AUTHZTOKEN=%s' %  (
                                self.__service, cronusapp_home, correlation_id, authz_token)
                if self.__service:
                    lcmMetas = serviceutil.getLcmMetas(self.__service)
                    if lcmMetas:
                        for key, value in lcmMetas.items():
                            env_variables += (' %s=%s' % (key.upper(), value)) 
            
                if isinstance(self.__cmd, basestring):
                    cmd_0 = str(self.__cmd)
                    if (cmd_0.find('sudo -u') >= 0): # as we have problem setting environment variables for sudo as root
                        cmd_0 = cmd_0.replace("sudo", ("sudo %s" % env_variables), 1)
                        self.__cmd = cmd_0
                        display_cmd = cmd_0.split(os.path.sep)[-1]
                else:
                    cmd_0 = self.__cmd[0]
                    if (cmd_0 == 'sudo' and '-u' in self.__cmd): # as we have problem setting environment variables for sudo as root
                        for env_variable in env_variables.split(' ')[::-1]:
                            self.__cmd.insert(1, env_variable)
                    display_cmd = self.__cmd[-1].split(os.path.sep)[-1]

            threadName = 'exec_thread(%s)' % display_cmd

            # execute
            self.__cmdProcess = subprocess.Popen(self.__cmd, stdout = subprocess.PIPE, stderr = subprocess.PIPE, close_fds = closeFds)
            self.logExecOutput('%s uuid start ' % (self.getUuid()))
            outputLogged = True
            self.logExecOutput('cmd: %s' % (self.__cmd if isinstance(self.__cmd, basestring) 
                                            else (' '.join(self.__cmd))))

            # in case we don't get any results
            self.__response = {'progress': 0.0, 'result': None}
            self.log('cmd(%s) output:' % display_cmd)

            while True:
                self._checkStop(threadName = threadName)
                stopped = (self.__cmdProcess.poll() != None)
                # read from stdout, if process completes, read all from stdout
                lines = self.readStream(self.__cmdProcess.stdout, readall = readall)
                if (not lines and stopped):
                    break
                self.__outputlines.extend(lines)
                for line in lines:
                    self.processExecResponse(line)
                    self.log(line)

                if (not lines):
                    time.sleep(float(config['exec_thread_sleep_time']))
            
            if self.__outputlines:
                self.logExecOutput('\n'.join(self.__outputlines))
            

            # maybe the script just closed stdout
            # wait until the script finishes
            while (self.__cmdProcess.poll() == None):
                self._checkStop(threadName = threadName)
                time.sleep(float(config['exec_thread_sleep_time']))
                
            if self.__partial:
                self.processExecResponse(self.__partial)
                self.logExecOutput(self.__partial)
                self.log(self.__partial)

            self.log('cmd(%s) output done' % display_cmd)

            returnCode = self.__cmdProcess.poll()
            self.logExecOutput('exitcode: %s' % returnCode)

            # the error condition
            if (returnCode != 0):
                self._updateStatus(httpStatus = 500)

                # read from stderr and log
                if self.__cmdProcess.stderr is not None:
                    lines = self.readStream(self.__cmdProcess.stderr)
                    for line in lines:
                        self.processExecResponse(line)
                    
                    if lines:
                        self.logExecOutput('stderr: %s' % '\n'.join(lines))
                        self.log('cmd(%s) stderr: %s' % (display_cmd, '\n'.join(lines)))

                self.__LOG.warning(self.__response)
                errorCode = int(self.__response['error']) if 'error' in self.__response else returnCode
                msg = 'Application script error (%s) error code (%d) error msg (%s)' % (self.__cmd, errorCode,
                         (self.__response['errorMsg'] if 'errorMsg' in self.__response else ''))
                self.__LOG.warning(msg)
                # now add 16000 to the error code to indicate this is a client error
                clientErrorCode = Errors.CLIENT_SCRIPT_ERROR + abs(errorCode)
                self._updateStatus(error = clientErrorCode, errorMsg = msg)

            else:
                self._updateStatus(httpStatus = 200)
                if 'result' in self.__response:
                    self._updateStatus(result = self.__response['result'])
            
        except SystemExit as excep:
            # status already set in agent thread
            msg = "System Exception for cmd %s - %s" % (self.__cmd, self.getStatus()['errorMsg'])
            self.__LOG.warning("%s - %s" % (msg, str(excep)))
            raise excep
        
        except OSError as excep:
            if self.__cmdProcess is None:
                msg = 'Cannot create subprocess cmd(%s) %s - %s' % (self.__cmd, str(excep), traceback.format_exc(2))
            else:
                msg = 'Unknown OSError cmd(%s) %s - %s' % (self.__cmd, str(excep), traceback.format_exc(2))
            self.__LOG.warning(msg)
            self._updateStatus(httpStatus = 500, error = Errors.UNKNOWN_ERROR, errorMsg = msg)
            
        except Exception as excep:
            msg = 'Unknown error cmd(%s) %s - %s' % (self.__cmd, str(excep), traceback.format_exc(2))
            self.__LOG.warning(msg)
            self._updateStatus(httpStatus = 500, error = Errors.UNKNOWN_ERROR, errorMsg = msg)
            
        finally:
            self._updateStatus(progress = 100)
            if self.__cmdProcess:
                if (self.__cmdProcess.stdout != None):
                    self.__cmdProcess.stdout.close()
                if (self.__cmdProcess.stdin != None):
                    self.__cmdProcess.stdin.close()
                if (self.__cmdProcess.stderr != None):
                    self.__cmdProcess.stderr.close()
                self.kill(self.__cmdProcess, self.__cmd)
            if outputLogged:
                self.logExecOutput('%s uuid end' % (self.getUuid()))
            self.log("Exec Thread done, cmd=%s" % self.__cmd)

    def stopAll(self):
        ''' kill the thread and any internal process '''
        self.stop()
        self.kill(self.__cmdProcess, self.__cmd)

    def kill(self, cmdProcess, cmd):
        '''
        Kills the given process if its alive in os independent way (in *nix kills it as super user)
        '''
        if (self.__cmdProcess != None and self.__cmdProcess.poll() == None):
            needSudo, sudoTarget = self.__needSudo()
            killCmd = 'kill -9 %s' % cmdProcess.pid
            if needSudo:
                killCmd = utils.sudoCmd(killCmd, sudoTarget)
            self.__LOG.info('cleanup incomplete process by %s ' % killCmd)
            retcode = os.system(killCmd)

            if retcode != 0: # even if process had actually gotten killed at the time of us killing it, we should get 0
                self.__LOG.error('Unable to kill exec process (that ran cmd %s) at time of exit; return code %s' % (cmd, cmdProcess.pid))
            try:
                # if the killed process had become a zombie, then lets collect the exit status so that it can be removed from process table
                os.waitpid(cmdProcess.pid, os.WNOHANG) # in case if kill failed and if process is still active, lets not hanf forever
            except OSError:
                pass #ok, looks like the process had not become a zombie and hence not in process table

    def getCmd(self):
        """ return cmd command that is running """
        return self.__cmd

    def getExitCode(self):
        """ @return: process exit code or None if process is still running """
        return self.__cmdProcess.poll()


    def getCmdPid(self):
        """ returns the PID of the child process
        @return - PID of process or None if one does not exist
        """

        if (self.__cmdProcess != None):
            return self.__cmdProcess.pid

        return None

    @staticmethod
    def validateResponse(response):
        """ checks to see if a response object is valid
        @param response - dictionary with the response object
        @return boolean - result of validation
        """

        # make sure it has either and error code or progress
        if ('progress' in response and (int(response['progress']) >= 0 and int(response['progress']) <= 100)):
            return True
        if ('error' in response or 'errorMsg' in response):
            return True
        return False

    def readStream(self, stream, readall = True):
        """ readlines in non-blocking manner.  It returns 0, 1 or more lines (without '\n' termination) found
        If process completes, it returns the last portion data it has read.
        """
        full_data = ''

        #Read until there is no more data in the stream or if timeout happens
        while True:
            data = ''
            #using only read list
            streams = select.select([stream], [], [], 0)[0]
            if (streams):
                #read 128 byte if available.  As stream is available, we should be able to read available bytes
                data = os.read(stream.fileno(), 1024)
            full_data = full_data + data
            if data == '' or not readall:
                break
        
        try:
            if full_data: 
                full_data = str(full_data)
        except UnicodeDecodeError:
            pass # ignore
        
        if (not full_data == ''):
            total = self.__partial + full_data
            count = total.count('\n')
            if (count == 0):
                self.__partial = total
                return []
            #Splits one extra
            splitData = total.split('\n', count)
            #Last element is partial read
            self.__partial = splitData[count]
            #Return all but last element
            return splitData[:count]
        else:
            if self.__partial == '':
                return []
            line = self.__partial
            self.__partial = ''
            return [line]
        return []
    
    def log(self, msg):
        """ based on the log level, log msg """
        if msg:
            if 'info' == self.__logLevel:
                self.__LOG.info(msg)
            else:
                self.__LOG.debug(msg)
                
    def logExecOutput(self, msg):
        """ log to exec_output.log """
        if msg:
            if 'debug' == self.__logLevel:
                OUTPUTLOG.debug(msg)
            else:
                OUTPUTLOG.info(msg)
        
    def getExecOutput(self):
        """ get stdout and stderr """
        return '\n'.join(self.__outputlines) 
    
