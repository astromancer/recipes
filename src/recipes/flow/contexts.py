"""
Context Managers.
"""

import contextlib as ctx


# ---------------------------------------------------------------------------- #

class ContextStack(ctx.ExitStack):
    """
    Manage nested contexts.
    """

    def __init__(self, contexts=()):
        super().__init__()

        if isinstance(contexts, ctx.AbstractContextManager):
            contexts = [contexts]

        self.contexts = list(contexts)

    def __enter__(self):
        return next(filter(None, map(self.enter_context, self.contexts)), None)

    def add(self, context):
        # assert isinstance(context, ctx.AbstractContextManager)
        self.contexts.append(context)
