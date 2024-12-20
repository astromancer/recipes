"""
A singleton class.
"""


class Singleton:

    # ------------------------------------------------------------------------ #
    class __Singleton:
        def __str__(self):
            return repr(self)

    # ------------------------------------------------------------------------ #
    _instance = None

    def __init__(self):
        if Singleton._instance is None:
            Singleton._instance = Singleton.__Singleton()

    def __getattr__(self, name):
        return getattr(self._instance, name)

    def __setattr__(self, name):
        return setattr(self._instance, name)

#
# Singleton/BorgSingleton.py
# Alex Martelli's 'Borg'

# class Borg:
#     _shared_state = {}
#
#     def __init__(self):
#         self.__dict__ = self._shared_state
#
#
# class Singleton(Borg):
#     def __init__(self, arg):
#         Borg.__init__(self)
#         self.val = arg
#
#     def __str__(self):
#         return self.val


# ---------------------------------------------------------------------------- #
