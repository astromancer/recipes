import textwrap

property_mixin_template = \
    """
    class {class_name}Mixin(object):
        _{name} = None
    
        @property
        def {name}(self):
            return self._{name}
    
        @{name}.setter
        def {name}(self, value):
            self.set_{name}(value)
    
        def set_{name}(self, value):
            self._{name} = value
    
    """


def property_factory(name, class_name=None):
    if class_name is None:
        class_name = name.replace('_', ' ').title().replace(' ', '')

    src = property_mixin_template.format(name=name, class_name=class_name)
    exec(textwrap.dedent(src))
    return eval(name.title() + 'Mixin')
