"""
Test authentication.
"""
from twisted.trial import unittest
# from twisted.internet.defer import inlineCallbacks
# from twisted.internet import task
from twisted.web import server, resource

# from twisted.web.test.requesthelper import DummyChannel, DummyRequest
# from twisted_web_test_utils import DummySite

# from webserver.auth import LoginBase
import common.avatar
from common.avatar import Session, SessionManagerBase, DEFAULT_LANG

class DummyAvatar:
    id = 123
    email = "testuser"
    password = "topsecret"
    roles = []

class SessionTest(unittest.TestCase):
    """
    Test L{common.avatar.Session}.
    """
    def setUp(self):
        self.uid = b'unique'
        self.site = server.Site(resource.Resource())
        self.session = Session(self.uid)
        self.avatar = DummyAvatar()

    def test_uid(self):
        self.assertEqual(self.session.uid, b'unique')

    def test_lang(self):
        # Language is default for new sessions
        self.assertEqual(self.session.language, DEFAULT_LANG)
        # Session can be set
        self.session.language = 'es_MX'
        # Session is the new value
        self.assertEqual(self.session.language, 'es_MX')

    def test_avatar_id(self):
        """
        Get and set avatar_id.
        """
        # Avatar id is initially unset
        self.assertFalse(self.session.hasAvatar())
        # Avatar id can be set
        self.session.setAvatarID(self.avatar.id)
        # hasAvatar is true after being set
        self.assertTrue(self.session.hasAvatar())
        # hasAvatar returns the value we set
        self.assertEqual(self.session.avatar_id, self.avatar.id)
        # Avatar id can be set to None
        self.session.setAvatarID(None)
        # hasAvatar returns false after session has been cleared
        self.assertFalse(self.session.hasAvatar())

    def test_flash_messages(self):
        """
        Set and read flash messages.
        """
        # Flash messages are initially empty
        messages = self.session.getFlashMessages(False)
        self.assertListEqual(messages, [])

        # Can add a flash message
        self.session.addFlashMessage("Hello")

        # Can view flash messages without deleting
        messages = self.session.getFlashMessages(False)
        self.assertListEqual(messages, [('Hello', (), {})])

        messages = self.session.getFlashMessages(False)
        self.assertListEqual(messages, [('Hello', (), {})])

        # Can add a second message
        self.session.addFlashMessage("World")

        messages2 = self.session.getFlashMessages()
        self.assertListEqual(messages2, [('Hello', (), {}), ('World', (), {})])

        # Messages are now empty because clear defaults to True
        messages3 = self.session.getFlashMessages()
        self.assertListEqual(messages3, [])

class SessionManagerBaseTest(unittest.TestCase):
    """
    Test L{common.avatar.SessionManagerBase}.
    """
    def setUp(self):
        self.sessionManager = SessionManagerBase()

    def test_create_get(self):
        """
        Create sessions and get by uid.
        """
        session = self.sessionManager.createSession()
        uid = session.uid
        session2 = self.sessionManager.getSession(uid)
        self.assertEqual(session2.uid, uid)


# class TestLoginBase(unittest.TestCase):
#     def setUp(self):
#         # self.web = request.WarpRequest(DummyChannel(), 1)
#         self.web = DummySite(LoginBase())

#     @inlineCallbacks
#     def test_get(self):
#         response = yield self.web.get('childpage')
#         self.assertEqual(response.value(), 'hello')

#         # base = LoginBase()
#         # self.assertEqual(self.request.getLanguage(), 'english')
