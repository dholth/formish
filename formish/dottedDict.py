from webob import MultiDict


def isInt(v):
    try:
        int(v)
        return True
    except ValueError:
        return False
    
    
def tryInt(v):
    try:
        return int(v)
    except ValueError:
        return v
    
## 
# Given a dottedDict, sets a new value based on a list of keys
def _setDict(data, keys, value):
    if len(keys) == 1:
        key = tryInt(keys[0])
        if isInt(key):
            if isinstance(data, dict) and len(data.keys()) == 0 and key == 0:
                data = [value]
            elif isinstance(data, list) and key == len(data):
                data.append(value)
            elif isinstance(data, list) and key > len(data):
                for i in xrange(len(data), key):
                    if isinstance(value, dict):
                        data.append({})
                    elif isinstance(value, list):
                        data.append([])
                    else:
                        data.append(None)
                data.append(value)
            elif isinstance(data, list) and key < len(data):
                data[key] = value
            else:
                raise KeyError('Can\'t set using an integer key here')
        else:
            if isinstance(data, dict):
                data[keys[0]] = value
            else:
                raise KeyError('Already assigned data key %s value %s'%(keys[0], data))
    else:
        if isInt(keys[0]):
            if isinstance(data, list) or (isinstance(data, dict) and len(data.keys()) == 0):
                if (isinstance(data, dict) and len(data.keys()) == 0):
                    # if we're trying to set using an integer key and we currently have an empty dict then make it a list. 
                    data = []
                if tryInt(keys[0]) == 0:
                    # if we have a 0 as the first key, we need to make the data a list...
                    if len(data) == 0:
                        data = [{}]
                    d = _setDict(data[tryInt(keys[0])], keys[1:], value) 
                if len(data)>tryInt(keys[0]):
                    d = _setDict(data[tryInt(keys[0])], keys[1:], value) 
                elif len(data) == tryInt(keys[0]):
                    o = _setDict({}, keys[1:], value)
                    data.append( o )
                    d = o
                else:
                    raise KeyError
            else:
                raise KeyError
        else:
            d = _setDict(_setdefault(data,keys[0],{}), keys[1:], value)
        data[tryInt(keys[0])] = d
    return data

def copyMultiDict(original):
    copy = {}
    for key in original.keys():
        copy[key] = original.getall(key)
    return copy

def keysort(a,b):
    if len(a) != len(b):
        return cmp(len(a),len(b))
    for i in xrange(len(a)-1,-1,-1):
        if a[i] == b[i]:
            continue
        if isInt(a[i]):
            return cmp(int(a[i]), tryInt(b[i]))
        else:
            return cmp(a[i], b[i])
    return 0
                    

##
# Given a dictionary - creates a dotteddict
def _getDictFromDottedKeyDict(d):
    if isinstance(d, MultiDict):
        data = copyMultiDict(d)
    else:
        data = d
    if isinstance(d,list):
        return d
    keyslist=[key.split('.') for key in data.keys()]
    keyslist.sort(keysort)
    for keys in keyslist:
        if len(keys) > 1:
            dottedkey = '.'.join(keys)
            if not data.has_key(dottedkey):
                continue
            if hasattr(data,'getall'):
                value= data.getall(dottedkey)
            else:
                value = data[dottedkey]
            del data[dottedkey]
            data = _setDict(data, keys, value)
        else:
            if hasattr(data,'getall'):
                data[keys[0]] = data.getall(keys[0])
    return data

# Singleton used to represent no argument passed, for when None is a valid
# value for the arg.
NOARG = object()
NOVALUE = object()


##
# sets a value on a dict  based on a dottedKey - generates keys if not there already
def _setdefault(data, dottedkey, default=NOARG):
    # First of all check if we aleady have a value for this key and return it if so...
    try:
        return _get(data,dottedkey)
    except:
        pass
    # We don't have the value so lets build a list of keys that we need to work on
    keys = str(dottedkey).split('.')
    lastleaf = data
    K = None
    # Loop on the list of keys up to the next to last one (we already checked the last one at the start of the run)
    for n,key in enumerate(keys[:-1]):
        K = '.'.join(keys[0:n+1])
        # Check to see if the data has this key, if it doesn't then break; if it does then loop again
        if not _has_key(data, K):
            break
        lastkey ='.'.join(keys[0:n+1])
        restofkeys = keys[n+1:]
        lastleaf = _get(data, lastkey) 

    # We've drilled in as far as we can go.. 
    
    if K is None:
        # if we didn't find a K then we have a new var to set
        data = _setDict(data, keys, default)
    else:
        # We should have a K for which the last segment doesn't exist
        if isinstance(lastleaf, dict) and len(lastleaf.keys()) == 0 and isInt(keys[n]):
            _set(data,lastkey,[])
            lastleaf = _get(data, lastkey)
        if isinstance(lastleaf, list) and tryInt(keys[n]) == len(lastleaf):
            lastleaf.append(_setDict({}, keys[n+1:], default))
        else:
            if lastleaf == data:
                data = _setDict(data, keys, default)
            else:
                _setDict(lastleaf, restofkeys, default)

            
    return _get(data, dottedkey)
   
## 
# given a real dictionary, recursively sets a value based on a dottedkey
def _set(data, dottedkey, value):
    keys = str(dottedkey).split('.')
    d = data
    try:
        for n,key in enumerate(keys[:-1]):
            d = d[tryInt(key)]
    except KeyError, e:
        raise KeyError('Error accessing dotted key %s on %r. Only got to %s'%(dottedkey,data,'.'.join(keys[:n])))
    d[tryInt(keys[-1])] = value
    return data

def _get(d, dottedkey):
    keys = str(dottedkey).split('.')
    try:
        for n,key in enumerate(keys):
            d = d[tryInt(key)]
    except (KeyError, TypeError), e:
        raise KeyError('Error accessing dotted key %s - key %s does not exist'%(dottedkey, key))
    return d
    
def _has_key(d, dottedkey):
    try:
        out = _get(d, dottedkey)
        return True
    except:
        return False

class dottedDict(object):
    """A dictionary that can be accessed and written to in dotted notation"""
    
    def __init__(self, value=None):
        if value is None:
            self.data = {}
        else:
            if isinstance(value, dottedDict):
                self.data = value.data
            else:
                self.data = _getDictFromDottedKeyDict(value)
            
    def get(self, dottedkey, default=NOARG):
        try:
            d = _get(self.data, dottedkey)
        except KeyError, e:
            if default is not NOARG:
                return default
            raise KeyError(e.message)
        if isinstance(d, dict):
            return dottedDict(d)
        else:
            return d
        

        
        
    def __getitem__(self, item):
        return self.get(item)
        
    def __setitem__(self,dottedkey, value):
        _setdefault(self.data, dottedkey, value)
        _set(self.data, dottedkey, value)
        
    def keys(self):
        keys = []
        if isinstance(self.data, list):
            for n, v in enumerate(self.data):
                keys.append(n)
        else:
            keys = self.data.keys()
        return keys
    
    def items(self):
        items = []
        for key in self.keys():
            items.append( (key, self[key]) )
        return items
        
    
    def dotteditems(self):
        store = []
        for key in self.dottedkeys():
            store.append((key, self[key]))
        return store
    
    def dottedkeys(self, value=None, store=None, prefix=None):
        if store is None:
            store = []
        if value is None:
            value = self.data
        if not isinstance(value, list) and not isinstance(value,dict):
            store.append(prefix)
            return store
        if isinstance(value, dict):
            for k, v in value.items():
                if prefix:
                    dkey = '%s.%s'%(prefix,k)
                else:
                    dkey = k
                self.dottedkeys(value=v, store=store, prefix=dkey)
        elif isinstance(value, list):
            for n, v in enumerate(value):
                if prefix:
                    dkey = '%s.%s'%(prefix,n)
                else:
                    dkey = n
                self.dottedkeys(value=v, store=store, prefix=dkey)
        return store
                
            
    
    def __eq__(self, other):
        return self.data == dottedDict(other).data
    

    def setdefault(self, dottedkey, default=NOARG):
        # Check return value for list or dict - if dict, wrap in ddict
        return _setdefault(self.data, dottedkey, default=default)
            
    def __getattr__(self, key):
        try:
            value = self.get(key.split('.')[0], NOVALUE)
            if value is NOVALUE:
                raise KeyError('Dotted key \'%s\' does not exist'%key)
        except AttributeError, e:
            raise KeyError(e.message)
        
    def has_key(self, key):
        return key in self.keys()

    def has_dottedkey(self, dottedkey):
        try:
            temp = self[dottedkey]
        except KeyError:
            return False
        return True
    
    def __repr__(self):
        return '<dottedDict> %s'%self.data

