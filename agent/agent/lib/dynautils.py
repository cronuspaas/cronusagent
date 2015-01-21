#pylint: disable=W0702,W0105
""" dynamically add packages to system path"""
import sys

def setuppath(path, modulename, classlist):
    ''' path '''
    if path not in sys.path:
        sys.path.append(path)

    moduleexist = (modulename in sys.modules)
    mod = __import__(modulename, fromlist=classlist)
    
    if moduleexist:
        # reload the same module
        mod = reload(mod)
        
    def getattrsafe(conf, key):
        ''' get attribute '''
        try:
            return getattr(conf, key)
        except:
            return None   
        
    return dict((k, getattrsafe(mod, k)) for k in classlist)        

def removepath(path, modulename, classlist):
    ''' remove path '''
    if path in sys.path:
        moduleexist = (modulename in sys.modules)
        mod = __import__(modulename, fromlist=classlist)
    
        if moduleexist:
            del sys.modules[modulename]

        if mod is not None:
            del mod

        sys.path.remove(path)
