#pylint: disable=E1101,W0105
""" system metrics """
import os
import platform
import subprocess

import logging
LOG = logging.getLogger(__name__)

class SystemMonitor():
    ''' monitor that gets system status '''
    def __init__(self):
        ''' constructor '''
        LOG.debug("creating %s" %(__name__))

    def getOSinfo(self):
        ''' get value os info '''
        return platform.uname()[0] + " " + platform.uname()[2] + " " + platform.uname()[3] + " " + platform.uname()[4]

    def getNodeName(self):
        ''' get node name '''
        return platform.uname()[1]

    def getPid(self):
        ''' get process pid'''
        return os.getpid()

    def getFreeMemory(self):
        ''' get free real memory in KB '''
        try:
            vmstat = subprocess.Popen("vmstat 1 2", shell = True, stdout=subprocess.PIPE)
            output = vmstat.communicate()[0].split('\n')
            fields = output[1].split()
            values = output[3].split()
            return int(values[fields.index('free')])
        except BaseException:
            return 0

    def getCpuUsage(self):
        ''' get cpu usage '''
        try:
            vmstat = subprocess.Popen("vmstat 1 2", shell = True, stdout=subprocess.PIPE)
            output = vmstat.communicate()[0].split('\n')
            fields = output[1].split()
            values = output[3].split()
            userTime = int(values[fields.index('us')])
            systemTime = int(values[fields.index('sy')])
            idleTime = int(values[fields.index('id')])
            return float(int(userTime) + int(systemTime)) / (int(userTime) + int(systemTime) + int(idleTime)) * 100
        except BaseException:
            return 0
