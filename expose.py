import sys
import functools
import numpy as np

from io import StringIO


#****************************************************************************************************
class expose():
    #TODO: OO
    #TODO: check Ipython traceback formatter?
    #TODO: Use superstring!!
    '''
    class that contains decorators for printing function arguments / content / returns
    '''
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~    
    @staticmethod
    def args( pre='', post='\n', verbosity=1 ):
        '''
        Decorator to print function call details - parameters names and effective values
        optional arguments specify stuff to print before and after, as well as verbosity level.
        
        Example
        -------
        In [43]: @expose.args()
            ...: def foo(a, b, c, **kw):
            ...:     return a
            ...: 
            ...: foo('aaa', 42, id, gr=8, bar=...)
        
        prints:
        foo( a       = aaa,
             b       = 42,
             c       = <built-in function id>,
             kwargs  = {'bar': Ellipsis, 'gr': 8} )

        Out[43]: 'aaa'
        '''
        #====================================================================================================    
        def actualDecorator(func):
            
            @functools.wraps(func)
            def wrapper(*fargs, **fkw):
                
                fname = func.__name__       #FIXME:  does not work with classmethods
                code = func.__code__
                
                #Create a list of function argument strings
                arg_names = code.co_varnames[:code.co_argcount]
                args = fargs[:len(arg_names)]
                defaults = func.__defaults__ or ()
                args = args + defaults[len(defaults) - (code.co_argcount - len(args)):]
                
                params = list(zip(arg_names, args))
                args = fargs[len(arg_names):]
                
                if args: 
                    params.append( ('args', args) )
                if fkw:
                    params.append( ('kwargs', fkw) )
                
                if verbosity==0:
                    j = ', '
                elif verbosity==1:
                    j = ',\n'
                
                #Adjust leading whitespace for pretty formatting
                lead_white = [0] + [len(fname)+2] * (len(params)-1)
                trail_white = int(np.ceil(max(len(p[0]) for p in params)/8)*8)
                pars = j.join(' '*lead_white[i] + \
                              '{0[0]:<{1}}= {0[1]}'.format(p, trail_white)
                                for i,p in enumerate(params))
                pr = '{fname}({pars})'.format(fname=fname, pars=pars)
                
                print(pre)
                print(pr)
                print(post)
                sys.stdout.flush()
                
                return func(*fargs, **fkw)
                
            return wrapper
            
        return actualDecorator  

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~    
    @staticmethod
    def returns():
        '''Decorator to print function return details'''
        def actualDecorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kw):
                r = func(*args, **kw)
                print( 'RETURNING!' )
                print( r )
                return r
            return wrapper
        return actualDecorator
    
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~    
    @staticmethod
    def suppress(func):
        '''Suppress all print statements in a function call'''
        @functools.wraps(func)
        def wrapper(*args, **kws):
            #shadow stdout temporarily
            actualstdout = sys.stdout
            sys.stdout = StringIO()
            
            #call the actual function
            r = func(*args, **kws)
            
            #restore stdout
            sys.stdout = actualstdout
            sys.stdout.flush()
            
            return r
        
        return wrapper

#alias
suppress_print = expose.suppress
    

    
    