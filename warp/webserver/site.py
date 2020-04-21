"""
Site customizations
"""
from twisted.web.server import Session, Site, Request
from twisted.python import log

from storm.locals import *

from warp.runtime import config, avatar_store
from warp.common.avatar import Avatar, SessionManager # DBSession

class WarpRequest(Request):
    def finish(self):
        rv = Request.finish(self)

        avatar_store.rollback()
        avatar_store.commit()

        # Some requests, like those for static files, don't have store
        store = getattr(self, 'store', None)
        if store:
            # Roll back and then commit, so no transaction is left open
            # between requests
            if store is not avatar_store:
                store.rollback()
                store.commit()

            # Some use cases involve setting store.request in getRequestStore,
            # so remove request.store here to avoid a circular reference GC.
            del self.store

        return rv


class WarpSite(Site):
    requestFactory = WarpRequest
    sessionManager = SessionManager()

    def makeSession(self):
        """
        Create new session.
        """
        return self.sessionManager.createSession()

    def getSession(self, uid):
        """
        Get session matching unique id.

        @type  uid: string
        @param uid: Unique id for session.
        """
        session = self.sessionManager.getSession(uid)

        if session is None:
            raise KeyError(uid)

        if session.isPersistent:
            return session

        if session.hasAvatar():
            max_age = config.get('sessionMaxAge')
            if max_age is not None and session.age() > max_age:
                session.addFlashMessage("You were logged out due to inactivity",
                                        _domain='_warp:login')
                session.setAvatarID(None)

        return session

    def _updateLogDateTime(self):
        """
        In superclass, updates log datetime periodically for performance.
        Here does nothing, assuming that it is handled at a higher level, e.g. journald.
        """
        pass

    def log(self, request):
        """
        Log the result of a request in combined log format.
        """
        # log.msg("request_headers: %r" % [[k, v] for k, v in request.requestHeaders.getAllRawHeaders()])
        line = '%s - - %s "%s" %d %s "%s" "%s"\n' % (
            request.getClientIP(),
            # request.getUser() or "-", # the remote user is almost never important
            self._logDateTime,
            '%s %s %s' % (self._escape(request.method),
                          self._escape(request.uri),
                          self._escape(request.clientproto)),
            request.code,
            request.sentLength or "-",
            self._escape(request.getHeader("referer") or "-"),
            self._escape(request.getHeader("user-agent") or "-"))
        log.msg(line)
