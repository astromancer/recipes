
class ForwardProperty:
    """
    Forward nested property to a parent class.
    """

    def __init__(self, name):
        self.parent_name = str(name).split('.', 1)
        self.property_name = str(name)

    def __get__(self, instance, kls=None):
        # sourcery skip: assign-if-exp, reintroduce-else
        # get parent object
        if instance is None:
            # lookup from class
            return self

        parent = getattr(instance, self.parent_name)
        return op.attrgetter(parent)(self.property_name)

    def __set__(self, instance, value):
        parent = getattr(instance, self.parent_name)
        setattr(parent, self.property_name, value)


# class ForwardProperty:
#     """
#     Forward nested property to a parent class.
#     """

#     def __init__(self, parent, name):
#         self.parent = parent
#         self.property_name = str(name)

#     def __get__(self, instance, kls=None):
#         # sourcery skip: assign-if-exp, reintroduce-else
#         # get parent object
#         if instance is None:
#             # lookup from class
#             return self

#         # parent = getattr(instance, self.parent_name)
#         return op.attrgetter(self.parent)(self.property_name)

#     def __set__(self, instance, value):
#         # parent = getattr(instance, self.parent_name)
#         setattr(self.parent, self.property_name, value)
