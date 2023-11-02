"""
Context Managers.
"""

import contextlib as ctx


# ---------------------------------------------------------------------------- #
class ContextStack(ctx.ExitStack):
    def __init__(self, context=None):
        super().__init__()
        self.contexts = []
        if context:
            self.add(context)

    def __enter__(self):
        return next(filter(None, map(self.enter_context, self.contexts)), None)

    def add(self, context):
        # assert isinstance(context, ctx.AbstractContextManager)
        self.contexts.append(context)
