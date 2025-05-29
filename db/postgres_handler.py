import pandas as pd
import sqlalchemy
import os

# You can set these via environment variables or hardcode for now
CONNECTION_STRINGS = {
    'CampusDB': os.getenv('CAMPUS_DB_CONN', 'postgresql://user:password@host:port/campusdb'),
    'LMSDB': os.getenv('LMS_DB_CONN', 'postgresql://user:password@host:port/lmsdb'),
}

class PostgresHandler:
    def __init__(self, connection_string):
        self.engine = sqlalchemy.create_engine(connection_string)

    @classmethod
    def for_db(cls, db_name):
        if db_name not in CONNECTION_STRINGS:
            raise ValueError(f"Unknown database name: {db_name}")
        return cls(CONNECTION_STRINGS[db_name])

    def query_to_df(self, query, params=None):
        """Run a SQL query and return a pandas DataFrame."""
        with self.engine.connect() as conn:
            df = pd.read_sql(query, conn, params=params)
        return df 