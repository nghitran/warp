from __future__ import print_function
from warp.runtime import avatar_store, config

from schemup.orms import storm
from schemup import commands, validator

# NTA TODO: Maybe load once?

stormSchema = storm.StormSchema()

def getConnectionClassName(store):
    return store._connection.__class__.__name__

def getWarpMigrationsDir(store):
    return config["warpDir"].child("migrations").child({
        "PostgresConnection": "postgres",
        # NTA FIX XXX: schemup does not support sqlite yet
        "SQLiteConnection": "sqlite",
        "MySQLConnection": "mysql"
    }[getConnectionClassName(store)])

# NTA: This probably belongs in schemup
def makeSchema(store, dryRun=False):
    name = getConnectionClassName(store)
    if name == "PostgresConnection":
        from schemup.dbs.postgres import PostgresSchema
        schemaClass = PostgresSchema
    # elif name == "MySQLConnection":
    #     from schemup.dbs.mysql import MysqlSchema
    #     schemaClass = MysqlSchema
    else:
        return None

    return schemaClass(store._connection._raw_connection, dryRun=dryRun)

# NTA TODO: All DB-related config should be grouped together
def getConfig(config=config):
    schemaConfig = {
        # Directory storing site's DB migrations
        # (twisted.python.filepath.FilePath)
        "migrations_dir": config["siteDir"].child("migrations"),
        # Whether to check schema on startup
        "check": True,
    }
    schemaConfig.update(config.get("schema", {}))
    return schemaConfig



def loadWarpMigrations(store=avatar_store):
    print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    print("Loading warp migrations...")
    warpMigrationsDir = getWarpMigrationsDir(store)
    if not warpMigrationsDir.isdir():
        raise Exception("Warp migrations dir not found")
    commands.load(warpMigrationsDir.path)

def loadSiteMigrations(config=config):
    print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    print("Loading site migrations...")
    schemaConfig = getConfig(config)
    siteMigrationsDir = schemaConfig["migrations_dir"]
    # NTA TODO: Blow up otherwise?
    if siteMigrationsDir.isdir():
        commands.load(siteMigrationsDir.path)

def loadMigrations(store=avatar_store, config=config):
    loadWarpMigrations(avatar_store)
    loadSiteMigrations(config)


def snapshot(store=avatar_store, config=config, dryRun=False):
    schema = makeSchema(store, dryRun)
    if schema is None:
        print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
        print("Migrations not supported for", getConnectionClassName(store))
        return

    loadMigrations(store, config)

    schema.ensureSchemaTable()
    commands.snapshot(schema, stormSchema)

def migrate(store=avatar_store, config=config, dryRun=False):
    schema = makeSchema(store, dryRun)
    if schema is None:
        print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
        print("Migrations not supported for", getConnectionClassName(store))
        return

    schema.ensureSchemaTable()

    # Make sure the real schema is what schemup_tables says it is
    print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    print("Checking schema integrity...")
    mismatches = validator.findSchemaMismatches(schema)
    # NTA TODO: Pretty print
    if mismatches:
        print("Real schema and schemup_tables are out of sync (did you change the schema outside of schemup?):")
        for mismatch in mismatches:
            print(mismatch, "\n")
        raise Exception("Schema mismatches")

    loadMigrations(store, config)

    print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    print("Upgrading...")
    sqls = commands.upgrade(schema, stormSchema)

    # Sanity checking
    if not dryRun:
        commands.validate(schema, stormSchema)

    # This is needed because several schemup operations touch the DB
    # through queries, but only "ensureSchemaTable" and "upgrade" end
    # the transaction (when they need to persist data (committing)).
    # TODO: The correct fix would be putting transaction start/end in
    # single functions (either this or schemup's (both of which
    # requires changing schemup)). Preferrably we want to separate
    # actualy querying and transaction start/end management
    store.rollback()

    if not sqls:
        print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
        print("Schema up-to-date")
    elif dryRun:
        print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
        for sql in sqls:
            print("")
            print(sql)
    else:
        print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
        print("Migrated successfully")

    print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
