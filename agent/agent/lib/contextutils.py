#pylint: disable=W0105,W0212
'''
managing context in an object
'''

CTX_DICT = 'jobcontext'
CTX_NAMES = ['guid', 'service', 'thread_timeout', 'thread_progress_timeout', 'reqstr', 'requrl', 'authztoken']

def injectcontext(target, ctx):
    ''' dynamically add a property to a dict of properties
        @param target: target object where context to be injected
        @param dictname: name of the context dict
        @param ctx: values in the context as dict
    '''
    try:
        propDict = getattr(target, CTX_DICT)
        propDict.update(ctx)
    except AttributeError:
        # dict not exist, create one
        propDict = {}
        propDict.update(ctx)
        target._jobcontext = propDict
        # add to class if not exist
        if CTX_DICT not in target.__class__.__dict__:
            setattr(target.__class__, CTX_DICT, property(lambda self: self._jobcontext))
        
def copycontexts(source, target, names):
    """ copy context properties from source to target object """
    for name in names:
        copycontext(source, target, name)

def copycontext(source, target, name):
    ''' copy context property from source to target object
        @param source: source
        @param target: target
        @param dictname: name of the context
        @param name: key of property
    '''
    if existcontext(source, name):
        value = getcontext(source, name)
        injectcontext(target, {name:value})
        
def copyJobContexts(source, target):
    """ copy all jor context """
    copycontexts(source, target, CTX_NAMES)

def getcontext(source, name, defValue = None):
    ''' get property value from a dict of properties
        @param source: source
        @param dictname: name of the context
        @param name: key of the property
        @param defValue: default value if key not exist
        @return: value from context, or default value if key or context not exist
    '''
    try:
        propDict = getattr(source, CTX_DICT)
        return propDict.get(name, defValue)
    except AttributeError:
        return defValue

def popcontext(source, name, defValue = None):
    ''' on successfully get property from a dict of properties, remove the property from dict
        @param source: source
        @param dictname: name of the context
        @param name: key of the property
        @param defValue: default value if key not exist
        @return: value from context, or default value if key or context not exist
    '''
    try:
        propDict = getattr(source, CTX_DICT)
        return propDict.pop(name, defValue)
    except AttributeError:
        return defValue


def existcontext(source, name):
    ''' test if a property exist in context
        @param source: source
        @param dictname: name of the context
        @param name: key of the property
        @return: Boolean of key existence
    '''
    try:
        ctx = getattr(source, CTX_DICT)
        return ctx.has_key(name) and ctx[name] is not None
    except AttributeError:
        return False
    
def resetcontext(source):
    ''' reset all context on source '''
    try:
        ctx = getattr(source, CTX_DICT)
        ctx.clear()
    except AttributeError:
        pass
    


