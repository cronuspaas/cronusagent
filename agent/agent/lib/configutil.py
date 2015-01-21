#pylint: disable=W0703,W0621,C0103,W0105
""" util for configurations """
from agent.lib import manifestutil
import logging
from beaker.converters import asbool
import pylons
import copy
import json

CONFIG = {}
CONFIGOR = {}
SCONFIGOR = {}

LOG = logging.getLogger(__name__)

def loadPylonConfig(pylonconfigs):
    """ load pylon config with overrides """
    CONFIG.update(pylonconfigs)
    
def loadConfigOverrides():
    """ load config override from .metadata """
    try:
        configsMeta = manifestutil.readJsonServiceMeta('agent', ['configs'])
        CONFIGOR.clear()
        if 'configs' in configsMeta:
            CONFIGOR.update(configsMeta['configs'])

        # apply to pylon configs
        pylons_config = pylons.config.current_conf()
        if pylons_config and CONFIGOR:
            pylons_config.update(copy.deepcopy(CONFIGOR))
            pylons.config.pop_process_config()
            pylons.config.push_process_config(pylons_config)

    except BaseException as exc:
        LOG.error(str(exc))
        
def loadSecureConfigOverrides():
    """ load secure config overrides from ./appdata/secure/.metadata.json """
    try:
        from agent.lib.security import authutil
        configsMeta = authutil.readSecureMeta()
        SCONFIGOR.clear()
        SCONFIGOR.update(configsMeta)

        # apply to pylon configs
        pylons_config = pylons.config.current_conf()
        if pylons_config and SCONFIGOR:
            pylons_config.update(copy.deepcopy(SCONFIGOR))
            pylons.config.pop_process_config()
            pylons.config.push_process_config(pylons_config)

    except BaseException as exc:
        LOG.error(str(exc))
    
    
def getConfig(key):
    """ getting pylon config with overrides """
    return SCONFIGOR[key] if key in SCONFIGOR else \
            (CONFIGOR[key] if key in CONFIGOR else \
                (CONFIG[key] if key in CONFIG else None))
    
def getConfigAsBool(key):
    """ get config as bool """
    value = getConfig(key)
    return asbool(value) if value else False

def getConfigAsInt(key):
    """ get config as int """
    value = getConfig(key)
    return int(value) if value else 0

def getConfigAsJson(key):
    """ get config as json """
    value = getConfig(key)
    return json.loads(value) if value else None
    
def getConfigOverrides():
    """
    load configuration overrides from agent .metadata.json
    """
    configsOR = {}
    try:
        configsMeta = manifestutil.readJsonServiceMeta('agent', ['configs'])
        configsOR = configsMeta['configs'] if 'configs' in configsMeta else {}
    except Exception as exc:
        LOG.error(str(exc))
        
    return configsOR 

def getAppUser():
    """ get application user, this we don't allow to override """
    useAppUser = asbool(pylons.config['use_app_user'])
    return pylons.config['app_user_account'] if useAppUser else pylons.config['agent_user_account']

def getAgentUser():
    """ agent user """
    return pylons.config['agent_user_account']

def hasSecurePassword():
    """ there exist a password in secure metadata """
    return 'password.local' in SCONFIGOR
