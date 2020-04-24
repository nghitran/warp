"""
Resource customizations
"""
import warnings

from zope.interface import implements

from twisted.python.filepath import FilePath, InsecurePath
from twisted.web import static
from twisted.web.resource import IResource, NoResource

from warp import helpers
from warp.common import access, translate
from warp.runtime import avatar_store, pool, config, templateLookup
from warp.webserver import auth, comet

if '.ico' not in static.File.contentTypes:
    static.File.contentTypes['.ico'] = 'image/vnd.microsoft.icon'

class WarpResourceWrapper(object):
    """
    Root Resource for Site
    """
    implements(IResource)

    isLeaf = False

    def __init__(self):
        self.warpBasePath = config['warpDir']
        self.warpStaticPath = self.warpBasePath.child('static')
        self.warpTemplatePath = self.warpBasePath.child('templates')

        templateLookup.__init__(directories=[
            config['siteDir'].child('templates').path,
            self.warpTemplatePath.path,
            config['siteDir'].child('nodes').path
        ], output_encoding='utf-8')

        # Configure special URLs to point to handlers which may be overridden
        # by app
        self.dispatch = {
            '__login__': config.get('loginHandler', self.handleLogin),
            '__logout__': config.get('logoutHandler', self.handleLogout),
            '_comet': config.get('cometHandler', self.handleComet),
            '_warp': config.get('warpstaticHandler', self.handleWarpstatic),
            '': config.get('defaultHandler', self.handleDefault),
        }

        self.caseInsensitiveUrl = False
        self.store = None
        self.avatar = None

    def getChildWithDefault(self, first_segment, request):
        """
        Return a child with the given name for the given request.
        """
        # Serve request for static file
        if first_segment:
            fp = self.buildFilePath(request)
            if fp is not None:
                del request.postpath[:]
                return static.File(fp.path)

        # Init for everything except static files
        session = request.getSession()

        if request.store is None:
            get_request_store = config.get('getRequestStore')
            if get_request_store is not None:
                request.store = get_request_store(request)
            else:
                request.store = avatar_store

        if request.avatar is None:
            request.avatar = session.avatar

        if request.avatar is not None:
            get_user = config.get('getRequestUser')
            if get_user is not None:
                request.avatar.user = get_user(request)

        if config.get('reloadMessages'):
            translate.loadMessages()

        lang = getattr(session, 'language', None) or getattr(session, 'lang', None)
        request.translateTerm = translate.getTranslator(lang)

        segment = first_segment
        if self.caseInsensitiveUrl:
            segment = first_segment.lower()

        handler = self.dispatch.get(segment)
        if handler:
            return handler(request)

        node = helpers.getNode(first_segment)
        if node:
            return NodeResource(node)

        return NoResource()

    def putChild(self, path, child):
        if self.caseInsensitiveUrl:
            path = path.lower()
        self.dispatch[path] = lambda r: child

    def buildFilePath(self, request):
        """
        Get FilePath for request if static file exists and is valid
        """
        file_path = config['siteDir'].child('static')
        for segment in request.path.split('/'):
            try:
                file_path = file_path.child(segment)
            except InsecurePath:
                return None

        if file_path.exists() and file_path.isfile():
            return file_path

    def handleLogin(self, request):
        """
        Handler for login requests
        """
        return auth.LoginHandler()

    def handleLogout(self, request):
        """
        Handler for logout requests
        """
        return auth.LogoutHandler()

    def handleComet(self, request):
        """
        Handler for comet requests
        """
        return NodeResource(comet)

    def handleWarpstatic(self, request):
        """
        Handler for static files
        """
        file_path = self.warpStaticPath
        for segment in request.path.split('/')[2:]:
            try:
                file_path = file_path.child(segment)
            except InsecurePath:
                return None

        if file_path.exists() and file_path.isfile():
            del request.postpath[:]
            return static.File(file_path.path)

        return NoResource()

    def handleDefault(self, request):
        """
        Default Handler
        """
        return Redirect(config['default'])


class Redirect(object):
    implements(IResource)

    isLeaf = True

    def __init__(self, url):
        self.url = url

    def render(self, request):
        request.redirect(self.url)
        return "Redirecting..."


class AccessDenied(object):
    implements(IResource)

    isLeaf = True
    facetName = 'view'
    args = ()

    def render(self, request):
        request.node = None
        request.resource = self
        template = templateLookup.get_template('/accessdenied.mak')
        return helpers.renderTemplateObj(request, template)


class NodeResource(object):
    implements(IResource)

    # You can always add a slash
    isLeaf = False

    def __init__(self, node):
        self.node = node
        self.facetName = None
        self.response = None
        self.args = []

    def getChildWithDefault(self, segment, request):
        if not segment:
            return Redirect(request.childLink('index'))

        render_func = self.getRenderFunc(segment)
        if render_func is not None:
            self.facetName = segment
            self.renderFunc = render_func
            self.isLeaf = True
            self.args = [x for x in request.postpath if x]

            # Perform an additional check before rendering the response
            if not access.allowed(request.avatar, self.node, facetName=segment,
                                  resourceArgs=self.args):
                return AccessDenied()

            response = self.getResponse(request)

            # Int is for NOT_DONE_YET. Maybe we should
            # check for a resource, rather than this?
            if isinstance(response, (str, int)):
                self.response = response
                return self
            return response

        sub_node = self.getSubNode(segment)
        if sub_node:
            return NodeResource(sub_node)

        return NoResource()

    def getResponse(self, request):
        request.node = self.node
        request.resource = self
        return self.renderFunc(request)

    # def getResponse(self, request):
    #     request.node = self.node
    #     request.resource = self
    #
    #     def transaction(store):
    #         request.store = store
    #         # log.msg("request {} store {}".format(request, store))
    #         return self.renderFunc(request)
    #
    #     # return self.renderFunc(request)
    #     return pool.transact(transaction)

    def render(self, request):
        if not self.facetName:
            request.redirect(request.childLink('index'))
            return "Redirecting..."

        # Should be configurable somehow
        request.setHeader(b'Pragma', b'no-cache')
        request.setHeader(b'Expires', '-1')

        return self.response

    def getRenderFunc(self, facet_name):
        render_func = getattr(self.node, 'render_%s' % facet_name, None)
        if render_func:
            return render_func

        template_path = self.getTemplate(facet_name)
        if template_path:
            return lambda r: helpers.renderTemplate(r, template_path.path)

        renderer = getattr(self.node, 'renderer', None)
        if renderer:
            render_method = getattr(renderer, 'render_%s' % facet_name, None)
            if render_method:
                return render_method

        return None

    def getTemplate(self, facet_name):
        template_path = FilePath(self.node.__file__).sibling(facet_name + '.mak')
        if template_path.exists():
            return template_path

    def getSubNode(self, node_name):
        current_package = self.node.__name__.rsplit('.', 1)[0]
        try:
            return getattr(__import__("%s.%s" % (current_package, node_name),
                                      fromlist=[node_name]),
                           node_name, None)
        except ImportError:
            return None

    def __repr__(self):
        return "<NodeResource: %s::%s (%s)>" % (
            self.node.__name__, self.facetName, self.args)
