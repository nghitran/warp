"""
Logging functions with caller info
"""

from twisted.python import log

def msg(message):
    "Automatically log the current function details."
    import inspect
    # Get the previous frame in the stack, otherwise it would
    # be this function!!!
    func = inspect.currentframe().f_back.f_code
    # Dump the message + the name of this function to the log.
    log.msg("%s (%s %s:%i)" % (message, func.co_name, func.co_filename, func.co_firstlineno))

def err(*args, **kwargs):
    log.err(args, kwargs)
