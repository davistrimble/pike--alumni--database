import os

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

load_dotenv()


def connect():
    """Open a connection whose cursors return rows as dictionaries.

    Use it as `with connect() as conn:`. psycopg commits when the block
    finishes normally and rolls back if an exception escapes it.
    """
    return psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row)
