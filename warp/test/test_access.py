from twisted.trial import unittest

from warp.common import access as a

class AccessTest(unittest.TestCase):

    def test_allow_deny(self):
        self.assertEqual(a.Allow().allows(object()), True)
        self.assertEqual(a.Deny().allows(object()), False)

    def test_equals(self):
        obj = object()
        self.assertEqual(a.Equals(obj).allows(obj), True)
        self.assertEqual(a.Equals(obj).allows(object()), False)

    def test_callback(self):
        self.assertEqual(a.Callback(lambda _: True).allows(object()), True)
        self.assertEqual(a.Callback(lambda _: False).allows(object()), False)

    def test_combiners(self):
        self.assertEqual(a.All(a.Allow(), a.Allow()).allows(object()), True)
        self.assertEqual(a.All(a.Allow(), a.Deny()).allows(object()), False)
        self.assertEqual(a.Any(a.Deny(), a.Allow()).allows(object()), True)
        self.assertEqual(a.Any(a.Deny(), a.Deny()).allows(object()), False)

    def test_empty_role(self):
        self.assertEqual(a.Role({}).allows(object()), None)

    def test_empty_rule_list(self):
        obj = object()
        self.assertEqual(a.Role({obj: []}).allows(obj), None)

    def test_role_allows(self):
        obj = object()
        self.assertEqual(a.Role({obj: [a.Allow()]}).allows(obj), True)

    def test_role_denies(self):
        obj = object()
        self.assertEqual(a.Role({obj: [a.Deny()]}).allows(obj), False)

    def test_role_defaults(self):
        self.assertEqual(a.Role({}, default=[a.Allow()]).allows(object()), True)
        self.assertEqual(a.Role({}, default=[a.Deny()]).allows(object()), False)
        self.assertEqual(a.Role({}, default=[]).allows(object()), None)
