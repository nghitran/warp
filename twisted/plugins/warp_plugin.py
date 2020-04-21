from zope.interface import implements

from twisted.application.service import IServiceMaker, MultiService
from twisted.application import internet
from twisted.plugin import IPlugin
from twisted.conch import manhole_tap

from twisted.web.server import Site
from twisted.web.resource import Resource

from prometheus_client.twisted import MetricsResource

from warp.iwarp import IWarpService
from warp import runtime, command

class WarpServiceMaker(object):
    implements(IServiceMaker, IPlugin, IWarpService)
    tapname = 'warp'
    description = "Warp webserver"
    options = command.Options

    def makeService(self, options):
        """
        Construct Warp service.
        """
        command.maybeRun(options)

        config_module = command.loadConfig(options)
        config = runtime.config

        port = options['port']
        factory = config['warpSite']

        if config.get('ssl'):
            from warp.webserver import sslcontext
            warp_service = internet.SSLServer(port, factory,
                                              sslcontext.ServerContextFactory())
        else:
            warp_service = internet.TCPServer(port, factory)

        svc = MultiService()

        console_config = config.get('console', {})
        console_service = manhole_tap.makeService({
            'telnetPort': options['telnetPort'],
            'sshPort': options['sshPort'],
            # 'sshPort': 'tcp:%s:interface=127.0.0.1' % port,
            'namespace': {'service': warp_service, 'store': runtime.store},
            'passwd': options['consolePasswd'] or console_config.get('passwd_file'),
            'sshKeyDir': options['sshKeyDir'],
            'sshKeyName': options['sshKeyName'],
            'sshKeySize': options['sshKeySize'],
        })


        metrics_root = Resource()
        metrics_root.putChild(b'metrics', MetricsResource())
        metrics_factory = Site(metrics_root)
        metrics_service = internet.TCPServer(options['metricsPort'], metrics_factory)

        warp_service.setServiceParent(svc)
        console_service.setServiceParent(svc)
        metrics_service.setServiceParent(svc)

        # if hasattr(config_module, 'mungeService'):
        #     warp_service = config_module.mungeService(warp_service)

        command.doStartup(options)

        return svc

serviceMaker = WarpServiceMaker()
