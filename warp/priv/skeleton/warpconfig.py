from warp.common import access as a
from warp.helpers import getNode

config = {
    'domain': 'localhost',
    'port': 8080,
    'db': "sqlite:warp.sqlite",
    # For posgres/mysql
    'schema': {
        # Whether to check schema on startup
        'check': False

        # By default migrations are read from "migrations" dir under the
        # project's root. Customize it with this key:
        # 'migrations_dir': a # twisted.python.filepath.FilePath
    },
    # Whether to trace SQL queries using storm tracer
    'trace': False,
    'default': 'home',
    "defaultRoles": ('anon',),

    'roles': {
        'anon': a.Role({
            getNode('home'): (a.Allow(),),
        }),
        'admin': a.Role({}, default=(a.Allow(),)),
    },
}
