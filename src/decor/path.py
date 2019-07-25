import functools
from pathlib import Path

#====================================================================================================
#decorator to convert posix paths to strings
#TODO:  Make this decorator more general?  Type conversion
class path():
    '''class that contains decorators for operating on pathlib.Path objects'''
    class to_string():
        #def __call__(self):
            #return 
            
        @staticmethod
        def at(*where):
            '''
            Decorator (factory) to auto-convert arguments to strings.
            Intended to be used for converting pathlib.Path to strings
            Useful when (for example) a variable is expected to be a string by the function
            internals.  With this decorator they can now also be pathlib.Path objects.
            
            Example
            -------
            xpath = Path('/media/Oceanus/Observing/data/somefile.txt')
            path.to_string.at(0)(np.loadtxt)(xpath, delimiter=';')
            '''
            if not len(where):
                where = (0,)    #default to convert first argument
                
            def deco(func):

                @functools.wraps(func)
                def wrapper(*args, **kwargs):
                    nargs = tuple( str(arg)     if i in where       else arg
                                        for i,arg in enumerate(args) )  #convert the specified arg to string
                    return func(*nargs, **kwargs)       #return the function

                return wrapper

            return deco
        
        @staticmethod
        def auto( func ):
            '''
            Example
            -------
            @path.to_string.auto
            def foo(a, b, c, **kw):
                print(a)
            foo(Path('/home/hannes'), 2, 3)
            '''
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                nargs = tuple( str(a) if isinstance(a,Path) else a 
                                for a in args )
                nkws =  { key : str(val) if isinstance(val,Path) else val 
                            for key, val in kwargs.items() }
                return func(*nargs, **nkws)
            return wrapper