import time
import random
from datetime import datetime

from storm.locals import *

from twisted.python.hashlib import md5
from twisted.python import components

from warp import runtime
from warp.common.schema import stormSchema

# Default session lang
DEFAULT_LANG = u'en_US'

@stormSchema.versioned
class Avatar(Storm):
    __version__ = "warp_1"
    __storm_table__ = "warp_avatar"

    id = Int(primary=True)
    email = Unicode()
    password = Unicode()

    _roles = None
    def _getRoles(self):
        if self._roles is None:
            roleLookup = runtime.config['roles']
            avatar_roles = runtime.avatar_store.find(
                AvatarRole, AvatarRole.avatar == self).order_by(AvatarRole.position)
            self._roles = tuple(
                [roleLookup[ar.role_name] for ar in avatar_roles if ar.role_name in roleLookup] +
                [roleLookup[r] for r in runtime.config['defaultRoles']]
            )

        return self._roles
    roles = property(_getRoles)

    def __repr__(self):
        return "<Avatar '%s'>" % self.email.encode("utf-8")


# Store flash messages
_MESSAGES = {}

def nowstamp():
    return int(time.mktime(datetime.utcnow().timetuple()))

class Session(components.Componentized):
    """
    Base interface for session.

    @ivar uid: A unique identifier for the session, C{bytes}.
    @ivar isPersistent: Whether session is persistent, i.e. not subject to session timeout
    @ivar touched: Last time when session was used

    @ivar language: ISO locale code

    @ivar avatar_id: Avatar id
    @ivar avatar: Avatar object instance

    This implements methods and properties from C{twisted.web.server.Session},
    and C{DBSession}. It doesn't implement session timeouts or require a database.
    """
    language = DEFAULT_LANG
    isPersistent = False

    # sessionTimeout = 900

    # Don't update session age if it is less than this
    # _touch_granularity = 10

    # Class variable which stores flash messages
    _MESSAGES = {}

    def __init__(self, uid):
        """
        Initialize a session with a unique ID.
        """
        components.Componentized.__init__(self)

        self.uid = uid
        self.touch()

        self.avatar_id = None
        self.avatar = None

    def addFlashMessage(self, msg, *args, **kwargs):
        """
        Add flash message to session.

        These are messages which should be displayed to the user for a single
        page load, e.g. to indicate that an action has succeeded.
        """
        if self.uid not in self._MESSAGES:
            self._MESSAGES[self.uid] = []
        self._MESSAGES[self.uid].append((msg, args, kwargs))

    def getFlashMessages(self, clear=True):
        """
        Get flash messages for session.

        @param clear: Whether to clear messages after reading, default True
        @type  clear: C{bool}
        """
        if self.uid not in self._MESSAGES:
            return []
        messages = self._MESSAGES[self.uid][:]
        if clear:
            del self._MESSAGES[self.uid]
        return messages


    def hasAvatar(self):
        return self.avatar_id is not None

    def setAvatarID(self, avatar_id):
        """
        Set avatar_id for session.

        Set to None when session is no longer valid.

        @param avatar_id: Integer id of avatar.
        @type avatar_id: C{integer}
        """
        self.avatar_id = avatar_id


    def setPersistent(self, is_persistent):
        """
        @param is_persistent: Set whether session is persistent.
        @type is_peristent: C{bool}
        """
        self.isPersistent = is_persistent


    def age(self):
        """
        @return Time since session was used in seconds.
        @rtype C{integer}
        """
        return nowstamp() - self.touched

    def touch(self):
        """
        Indicate that the session has been used.

        This is used to extend the session inactivity timeout.
        """
        self.touched = nowstamp()
        # Optimization to prevent multiple updates in a short period of time
        # if self.age() > self._touch_granularity:
        #     self.touched = nowstamp()

    def __repr__(self):
        return "<Session '%s'>" % self.uid


class SessionManagerBase(object):
    """
    Base interface for SessionManager implementations.
    """
    counter = 0
    sessions = {}

    def createSession(self):
        """
        Generate a new Session instance.

        @return:  Session object
        """
        uid = self._mkuid()
        session = self.sessions[uid] = Session(uid)
        return session

    def getSession(self, uid):
        """
        Get a previously generated session by its unique ID.

        This raises a KeyError if the session is not found.

        @type  uid: string
        @param uid: Unique id for session.

        @return:  Session object
        """
        return self.sessions[uid]

    def _mkuid(self):
        """
        Create uid.
        """
        self.counter = self.counter + 1
        return md5("%s_%s" % (str(random.random()), str(self.counter))).hexdigest()

class SessionManager(object):
    """
    Handle sessions using database.
    """
    counter = 0

    def createSession(self):
        """
        Create initial session.

        @return:  Session object
        """
        uid = self._create_uid()
        session = DBSession()
        session.uid = uid
        runtime.avatar_store.add(session)
        runtime.avatar_store.commit()
        return session

    def getSession(self, uid):
        """
        Get session matching uid.

        @type  uid: string
        @param uid: Unique id for session.

        @return:  Session object
        """
        return runtime.avatar_store.get(DBSession, uid)

    def _create_uid(self):
        """
        Create uid.
        """
        self.counter = self.counter + 1
        return md5("%s_%s" % (str(random.random()), str(self.counter))).hexdigest()


@stormSchema.versioned
class DBSession(Storm):
    # FIXME HXP: This breaks integration with MySQL and SQLite, but those are
    # not working anyway due to the missing touched column.
    __version__ = "hxp_2"
    __storm_table__ = "warp_session"

    uid = RawStr(primary=True)
    avatar_id = Int()
    avatar = Reference(avatar_id, Avatar.id)
    touched = Int(default_factory=nowstamp)

    isPersistent = Bool(default=False)

    language = u"en_US"
    messages = None
    afterLogin = None

    _touch_granularity = 10

    def __storm_loaded__(self):
        if self.language is None:
            self.language = u"en_US"
        if self.touched is None:
            self.touched = nowstamp()
            runtime.avatar_store.commit()


    def addFlashMessage(self, msg, *args, **kwargs):
        """
        Add flash message to session.

        These are messages which should be displayed to the user for a single
        page load, e.g. to indicate that an action has succeeded.
        """
        if self.uid not in _MESSAGES:
            _MESSAGES[self.uid] = []
        _MESSAGES[self.uid].append((msg, args, kwargs))

    def getFlashMessages(self, clear=True):
        """
        Get flash messages for session.

        @type  clear: C{boolean}
        @param clear: Whether to clear messages after reading, default True
        """
        if self.uid not in _MESSAGES:
            return []
        messages = _MESSAGES[self.uid][:]
        if clear:
            del _MESSAGES[self.uid]
        return messages


    def hasAvatar(self):
        return self.avatar_id is not None

    def setAvatarID(self, avatar_id):
        self.avatar_id = avatar_id
        runtime.avatar_store.commit()


    def setPersistent(self, is_persistent):
        self.isPersistent = is_persistent
        runtime.avatar_store.commit()

    def age(self):
        return nowstamp() - self.touched

    def touch(self):
        if self.age() > self._touch_granularity:
            self.touched = nowstamp()
            runtime.avatar_store.commit()

    def __repr__(self):
        return "<Session '%s'>" % self.uid

# ---------------------------

@stormSchema.versioned
class AvatarRole(Storm):
    __version__ = "warp_1"
    __storm_table__ = "warp_avatar_role"

    id = Int(primary=True)
    avatar_id = Int()
    avatar = Reference(avatar_id, "Avatar.id")
    role_name = RawStr()
    position = Int()
