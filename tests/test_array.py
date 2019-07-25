#from decor.profiler import profile
from recipes.array import neighbours

import numpy as np


a = np.arange(12).reshape(4,3)
neighbours(a, (1,2), 4)

#neighbours0 = profile()(neighbours)
#neighbours0(a, (1,2), 4)

#print( ('~'*100 +'\n')*5 )
#neighbours1 = profile().histogram(neighbours)
#neighbours1(a, (1,2), 4)