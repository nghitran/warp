from twisted.trial import unittest

from twisted.internet import defer, reactor
from twisted.internet.defer import inlineCallbacks
from twisted.test import proto_helpers
from twisted.web import resource
from twisted.web import server
from twisted.web.test.test_web import DummyRequest
from twisted.web.server import NOT_DONE_YET

from warp.common.avatar import SessionManagerBase
from warp.webserver.site import WarpSite

from twisted.protocols import loopback

# from twisted_web_test_utils import DummySite

# from twisted.internet.base import DelayedCall
# DelayedCall.debug = True

class SmartDummyRequest(DummyRequest):
    def __init__(self, method, url, args=None, headers=None):
        DummyRequest.__init__(self, url.split('/'))
        self.method = method
        self.headers.update(headers or {})

        # set args
        args = args or {}
        for k, v in args.items():
            self.addArg(k, v)

    def value(self):
        return "".join(self.written)

class DummySite(WarpSite):
    requestFactory = SmartDummyRequest
    sessionManager = SessionManagerBase()

    def get(self, url, args=None, headers=None):
        return self._request("GET", url, args, headers)

    def post(self, url, args=None, headers=None):
        return self._request("POST", url, args, headers)

    def _request(self, method, url, args, headers):
        request = SmartDummyRequest(method, url, args, headers)
        resource = self.getResourceFor(request)
        result = resource.render(request)
        return self._resolveResult(request, result)

    def _resolveResult(self, request, result):
        if isinstance(result, str):
            request.write(result)
            request.finish()
            return defer.succeed(request)
        elif result is server.NOT_DONE_YET:
            if request.finished:
                return defer.succeed(request)
            return request.notifyFinish().addCallback(lambda _: request)
        else:
            raise ValueError("Unexpected return value: %r" % (result,))

# from twisted.web import resource

class ChildPage(resource.Resource):
    def render(self, request):
        d = defer.Deferred()
        d.addCallback(self.renderResult, request)
        reactor.callLater(1, d.callback, "hello")
        return NOT_DONE_YET

    def renderResult(self, result, request):
        request.write(result)
        request.finish()

class MainPage(resource.Resource):
    def __init__(self):
        resource.Resource.__init__(self)
        self.putChild('childpage', ChildPage())


class WebTest(unittest.TestCase):
    def setUp(self):
        self.web = DummySite(MainPage())

    @inlineCallbacks
    def test_get(self):
        response = yield self.web.get("childpage")
        self.assertEqual(response.value(), "hello")


class HelloPage(resource.Resource):
    isLeaf = True
    def render_GET(self, request):
        return "Hello!"

class BasicRequestTest(unittest.TestCase):
    def setUp(self):
        # self.site = WarpSite(resource.Resource())
        # self.site = server.Site(resource.Resource())
        self.site = server.Site(HelloPage())
        self.channel = self.site.buildProtocol(('127.0.0.1', 0))
        self.tr = proto_helpers.StringTransport()
        self.channel.makeConnection(self.tr)

    def test_basic(self):
        # self.channel.dataReceived(b'GET / HTTP/1.0\r\nContent-Length: 2\r\n\r\n')
        self.channel.dataReceived(b'GET /childpage HTTP/1.0\r\n\r\n')
        self.channel.connectionLost(IOError("all one"))
        # self.assertEqual(self.tr.value(), "hi")

        # # if you have params / headers:
        # response = yield self.web.get("childpage", {'paramone': 'value'}, {'referer': "http://somesite.com"})

class RequestTest(unittest.TestCase):
    def setUp(self):
        # self.site = WarpSite(resource.Resource())
        # self.site = server.Site(resource.Resource())
        self.site = server.Site(HelloPage())
        self.channel = self.site.buildProtocol(('127.0.0.1', 0))
        self.request = server.Request(self.channel, 0)

    def test_basic(self):
        self.assertEqual(self.request.channel, self.channel)

# /Users/jake/.virtualenvs/click/lib/python2.7/site-packages/twisted/web/test/test_http.py
# class LoopbackHTTPClient(http.HTTPClient):
#     def connectionMade(self):
#         self.sendCommand(b"GET", b"/foo/bar")
#         self.sendHeader(b"Content-Length", 10)
#         self.endHeaders()
#         self.transport.write(b"0123456789")

# twisted/web/test/test_webclient.py
