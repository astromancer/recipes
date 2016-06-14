
import collections as coll

from .iter import flatiter


#====================================================================================================
class Invertible():
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def is_invertible(self):
        '''check whether dict can be inverted'''
        #TODO
        return True
    
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def inverse(self):
        if self.is_invertible():
            return self.__class__.__bases__[1](zip(self.values(), self.keys()))

class InvertibleDict(Invertible, dict):
    pass


#****************************************************************************************************
class AutoVivification(dict):
    """Implement autovivification feature for dict."""
    def __missing__(self, key):
        value = self[key] = type(self)()
        return value
    
#class AutoVivification(dict):
    ##
    #"""Implementation of perl's autovivification feature."""
    #def __getitem__(self, item):
        #try:
            #return dict.__getitem__(self, item)
        #except KeyError:
            #value = self[item] = type(self)()
            #return value


#****************************************************************************************************
class TransDict(coll.UserDict):
    '''Provides a way of mapping shortend versions of keywords to their proper value'''
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __init__(self, dic=None, **kwargs):
        super().__init__(dic, **kwargs)
        self._translations = {}
    
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def add_translations(self, dic=None, **kwargs): #add_vocab??
        '''enable on-the-fly shorthand translation'''
        dic = dic or {}
        self._translations.update( dic, **kwargs )
    
    #alias
    add_vocab = add_translations 
    
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __contains__(self, key):
        return super().__contains__(self._translations.get(key, key))
    
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __missing__(self, key):
        '''if key not in keywords, try translate'''
        return self[ self._translations[key] ]
 
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def allkeys(self):
        #TODO: Keysview**
        return flatiter( self.keys(), self._translations.keys() )
    
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def many2one(self, many2one):
        #self[one]       #error check
        for many, one in many2one.items():
            for key in many:
                self._translations[key] = one
                

#****************************************************************************************************
class SuperDict(TransDict):
    def __init__(self, dic=None, **kwargs):
        super().__init__(dic, **kwargs)
        self._equivalence_maps = []

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def add_map(self, func):
        self._equivalence_maps.append( func )

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __missing__(self, key):
        try:
            #try translate with vocab
            return super().__missing__(key)
        except KeyError as err:
            #try translate with equivalence maps
            for emap in self._equivalence_maps:
                if super().__contains__(emap(key)):
                    return self[emap(key)]
            raise err

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __contains__(self, key):
        if super().__contains__(key):
            return True #no translation needed

        for emap in self._equivalence_maps:
            try:
                return super().__contains__(emap(key))
            except:
                pass

        return False
            

#****************************************************************************************************
class DefaultOrderedDict(coll.OrderedDict):
    # Source: http://stackoverflow.com/a/6190500/562769
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __init__(self, default_factory=None, *a, **kw):
        if (default_factory is not None and
           not isinstance(default_factory, coll.Callable)):
            raise TypeError('first argument must be callable')
        
        coll.OrderedDict.__init__(self, *a, **kw)
        self.default_factory = default_factory

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __getitem__(self, key):
        try:
            return coll.OrderedDict.__getitem__(self, key)
        except KeyError:
            return self.__missing__(key)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __missing__(self, key):
        if self.default_factory is None:
            raise KeyError(key)
        self[key] = value = self.default_factory()
        return value

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __reduce__(self):
        if self.default_factory is None:
            args = tuple()
        else:
            args = self.default_factory,
        return type(self), args, None, None, self.items()

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def copy(self):
        return self.__copy__()

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __copy__(self):
        return type(self)(self.default_factory, self)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __deepcopy__(self, memo):
        import copy
        return type(self)(self.default_factory,
                          copy.deepcopy(self.items()))

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __repr__(self):
        return 'OrderedDefaultDict(%s, %s)' % (self.default_factory,
                                               coll.OrderedDict.__repr__(self))
    
    
#====================================================================================================
def invertdict(d):
    return dict( zip(d.values(), d.keys()) )    
#====================================================================================================    
    