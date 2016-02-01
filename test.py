from decor.profile import profile
from recipes.array import neighbours

import numpy as np

neighbours = profile(neighbours)

a = np.arange(12).reshape(4,3)
neighbours(a, (1,2), 4)