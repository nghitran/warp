from __future__ import print_function
from twisted.python import log

from storm.database import create_database
from storm.twisted.store import StorePool
from storm.uri import URI
from storm.locals import *
from storm.exceptions import DatabaseError

from warp.runtime import avatar_store, config, sql

from txpostgres import txpostgres
from txpostgres.reconnection import DeadConnectionDetector

def start_storm_pool(database, config):
    """
    Start Storm db pool
    """
    min_size = config.get('db_pool_min', 3)
    max_size = config.get('db_pool_max', 10)
    pool = StorePool(database, min_size, max_size)
    pool.start()
    runtime.pool = pool

def setupStore():
    uri = URI(config['db'])
    print("Connecting to database {} as user {}".format(uri.database, uri.username))
    database = create_database(uri)

    # Single db connection
    runtime.avatar_store.__init__(database)

    if config.get('trace'):
        import sys
        from storm.tracer import debug
        debug(True, stream=sys.stdout)

    # Conection pool
    # start_storm_pool(database, config)
    # print("Started storm pool")

    # Only sqlite uses this now
    sqlBundle = getCreationSQL(avatar_store)
    if not sqlBundle:
        return

    tableExists = sql['tableExists'] = sqlBundle['tableExists']

    for (table, creationSQL) in sqlBundle['creations']:
        if not tableExists(avatar_store, table):
            # Unlike log.message, this works during startup
            print("~~~ Creating Warp table '%s'" % table)

            if not isinstance(creationSQL, tuple): creationSQL = [creationSQL]
            for sqlCmd in creationSQL: avatar_store.execute(sqlCmd)
            avatar_store.commit()

def getCreationSQL(store):
    connType = store._connection.__class__.__name__
    return {
        'SQLiteConnection': {
            'tableExists': lambda s, t: bool(s.execute("SELECT count(*) FROM sqlite_master where name = '%s'" % t).get_one()[0]),
            'creations': [
                ('warp_avatar', """
                CREATE TABLE warp_avatar (
                    id INTEGER NOT NULL PRIMARY KEY,
                    email VARCHAR,
                    password VARCHAR,
                    UNIQUE(email))"""),
                ('warp_session', """
                CREATE TABLE warp_session (
                    uid BYTEA NOT NULL PRIMARY KEY,
                    avatar_id INTEGER REFERENCES warp_avatar(id) ON DELETE CASCADE)"""),
                ('warp_avatar_role', """
                CREATE TABLE warp_avatar_role (
                    id INTEGER NOT NULL PRIMARY KEY,
                    avatar_id INTEGER NOT NULL REFERENCES warp_avatar(id) ON DELETE CASCADE,
                    role_name BYTEA NOT NULL,
                    position INTEGER NOT NULL DEFAULT 0)"""),
                ],
            },
        'MySQLConnection': {
            'tableExists': lambda s, t: bool(s.execute("""
                   SELECT count(*) FROM information_schema.tables
                   WHERE table_schema = ? AND table_name=?""",
               (URI(config['db']).database, t)).get_one()[0]),
            'creations': [
                ('warp_avatar', """
                CREATE TABLE warp_avatar (
                    id INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY,
                    email VARCHAR(64),
                    password VARCHAR(32),
                    UNIQUE(email)
                  ) engine=InnoDB, charset=utf8"""),
                ('warp_session', """
                CREATE TABLE warp_session (
                    uid VARBINARY(32) NOT NULL PRIMARY KEY,
                    avatar_id INTEGER REFERENCES warp_avatar(id) ON DELETE CASCADE
                  ) engine=InnoDB, charset=utf8"""),
                ('warp_avatar_role', """
                CREATE TABLE warp_avatar_role (
                    id INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY,
                    avatar_id INTEGER NOT NULL REFERENCES warp_avatar(id) ON DELETE CASCADE,
                    role_name VARBINARY(32) NOT NULL,
                    position INTEGER NOT NULL
                  ) engine=InnoDB, charset=utf8"""),
                ],
            },
    }.get(connType)
