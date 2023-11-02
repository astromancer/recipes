from recipes.sets import OrderedSet


s = OrderedSet('abracadaba')
t = OrderedSet('simsalabim')
print(s | t)
print(s & t)
print(s - t)
