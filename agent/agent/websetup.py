#pylint: disable=W0105
"""Setup the agent application"""
import logging

import pylons.test

from agent.config.environment import load_environment

LOG = logging.getLogger(__name__)

def setup_app(command, conf, my_vars):
    """Place any commands to setup agent here"""
    # Don't reload the app if it was loaded under the testing environment
    if not pylons.test.pylonsapp:
        load_environment(conf.global_conf, conf.local_conf)

    LOG.debug('setup app with command:' + str(command))
    LOG.debug('setup app with vars:' + str(my_vars))
