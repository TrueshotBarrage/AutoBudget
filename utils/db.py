import logging
import psycopg2
from psycopg2.extras import LoggingConnection


class DatabaseConnector:
    """Database connection module for Postgres database instances."""

    def __init__(self, db_name, host, user, password, port):
        # SQL init file path
        self.seed_sql_path = "db_init.sql"

        self.db_name = db_name
        self.host = host
        self.user = user
        self.password = password
        self.port = int(port)

        # Establish standard (verbose) logging output
        logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger(__name__)

        self.conn = self._init_db()

    def _init_db(self):
        # Establish a connection to the database
        conn = psycopg2.connect(
            connection_factory=LoggingConnection,
            database=self.db_name,
            host=self.host,
            user=self.user,
            password=self.password,
            port=self.port,
        )

        # Initialize logger for SQL queries
        conn.initialize(self.logger)

        # Automatically commit without transactions
        conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

        # Execute the SQL seed file
        if self.seed_sql_path:
            cursor = conn.cursor()
            with open(self.seed_sql_path, "r") as seed_sql:
                cursor.execute(seed_sql.read())

        return conn
