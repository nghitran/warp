"""
Globally-accessible stuff (like the store) initialised at runtime, not import-time
"""
import sys

from mako.lookup import TemplateLookup

from warp.common.events import CommitEventStore


log = sys.stdout

# __new__ creates an instance but does not initialize it
# The instance is initialized later when we have read the config
avatar_store = CommitEventStore.__new__(CommitEventStore)

# Default for app code only.
# Warp never uses this name, so it can be safely changed or removed.
store = avatar_store

# Storm db pool
pool = None

# txpostgres pool
tx_pool = None

templateLookup = TemplateLookup.__new__(TemplateLookup)

config = {}

sql = {}

internal = {
    'uploadCache': {}
}

exposedStormClasses = {}

# Translations of messages for internationalization
messages = {}

def expose(modelClass, crudClass):
    exposedStormClasses[unicode(modelClass.__name__)] = (modelClass, crudClass)

    # The problem with this is that in theory more than one model might use the
    # same crud class, but if that actually happens, trivially subclassing the
    # crud class will fix it.
    crudClass.__warp_model__ = modelClass
