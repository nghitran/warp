from twisted.python import log

import storm.database
import storm.uri
# from storm.locals import *

from warp.runtime import avatar_store, sql

def setup_store(db_uri):
    """
    Connect to database
    """
    uri = storm.uri.URI(db_uri)
    log.msg("Connecting to database {} as user {}".format(uri.database, uri.username))
    database = storm.database.create_database(uri)

    # Single db connection
    avatar_store.__init__(database)

    # Only sqlite uses this now
    sql_bundle = _get_creation_sql(avatar_store, db_uri)
    if not sql_bundle:
        return database

    table_exists = sql['table_exists'] = sql_bundle['table_exists']

    for (table, creation_sql) in sql_bundle['creations']:
        if not table_exists(avatar_store, table):
            # Unlike log.message, this works during startup
            log.msg("~~~ Creating Warp table '%s'" % table)

            if not isinstance(creation_sql, tuple):
                creation_sql = [creation_sql]
            for sql_cmd in creation_sql:
                avatar_store.execute(sql_cmd)
            avatar_store.commit()

    return database


def _get_creation_sql(store, db_uri):
    conn_type = store._connection.__class__.__name__
    return {
        'SQLiteConnection': {
            'table_exists': lambda s, t: bool(s.execute(
                """SELECT count(*) FROM sqlite_master where name = '%s'""" % t).get_one()[0]),
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
            'table_exists': lambda s, t: bool(s.execute(
                """SELECT count(*)
                   FROM information_schema.tables
                   WHERE table_schema = ? AND table_name=?
                """, (storm.uri.URI(db_uri).database, t)).get_one()[0]),
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
    }.get(conn_type)
