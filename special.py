import numpy as np

#====================================================================================================
def Gaussian(p, x):
    '''Gaussian function'''
    #kw.get('sigma')
    #kw.get('mean')
    #kw.get('amplitude')
    
    A, b, mx = p
    return A * np.exp(-b * (x-mx)**2)

def Gaussian2D(p, x, y):
    '''Elliptical Gaussian function for fitting star profiles'''
    A, a, b, c, x0, y0 = p
    ym = y - y0
    xm = x - x0
    return A * np.exp(-(a*xm**2 + 2*b*xm*ym + c*ym**2))

def symmetrize(a):
    return a + a.T - numpy.diag(a.diagonal())

class SymNDArray(numpy.ndarray):
    def __setitem__(self, (i, j), value):
        super(SymNDArray, self).__setitem__((i, j), value)                    
        super(SymNDArray, self).__setitem__((j, i), value)                    

def symarray(input_array):
    """
    Returns a symmetrized version of the array-like input_array.
    Further assignments to the array are automatically symmetrized.
    """
    return symmetrize(numpy.asarray(input_array)).view(SymNDArray)


class G2D():
    #TODO: Non-sym case: can still be viable ?
    #TODO: specify by: flux, rotation etc
    def __init__(self, amp, mu, cov):
        self.amp = amp
        self.mu = mu = np.asarray(mu)
        self.cov = cov = np.asarray(cov)
        self.dim = mu.size
        
        if not np.allclose(cov.shape[0], cov.shape):
            raise ValueError('Covariance matrix should be square.')
        if not np.allclose(cov, cov.T):
            raise ValueError('Covariance matrix should be symmetric.')
        #TODO:
            #raise ValueError('Covariance matrix should be positive definite')
        
        if self.dim != cov.shape[0]:
            raise ValueError('Mean vector dimensionality must equal the rank of the covariance matrix')
        
        self.prec = la.inv(cov)
       
    def __call__(self, grid):
        
        mu = np.array(self.mu, ndmin=grid.ndim).T
        gm = grid - mu
        
        e = np.sum(gm * np.tensordot(self.prec, gm, 1), axis=0)
        return self.amp * np.exp(-0.5*e)
    
    @staticmethod
    def _to_cov_matrix(var, cov):       #correlation=None
        '''compose symmetric covariance tensor'''
        #2D case
        return np.eye(2)*var + np.eye(2)[::-1] * cov #len(var)
    
#     @staticmethod
#     def _to_cov_matrix(var, corr):       #correlation=None
#         '''compose symmetric covariance tensor'''
#         #2D case
#         return np.eye(2)*var + np.eye(2)[::-1] * corr * np.prod(var) #len(var)
    
    def integrate(self):
        detSig = la.det(self.prec)
        k = self.dim
        return self.amp / np.sqrt(detSig * (2*np.pi)**k)
        
    flux = property(integrate)