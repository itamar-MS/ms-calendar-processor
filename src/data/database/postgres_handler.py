import pandas as pd
import sqlalchemy
import sys
import os
from pathlib import Path

# Add the src directory to the path so we can import from core
sys.path.append(str(Path(__file__).parent.parent))
from core.config import Config

# Use the Config class to get connection strings
CONNECTION_STRINGS = {
    'CampusDB': Config.CAMPUS_DB_CONN or 'postgresql://user:password@host:port/campusdb',
    'LMSDB': Config.LMS_DB_CONN or 'postgresql://user:password@host:port/lmsdb',
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