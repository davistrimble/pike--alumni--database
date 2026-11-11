import os
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

def search(term):
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    with psycopg.connect(database_url) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            if (term == ""):
                return ()
            interm = f"%{term}%"
            cur.execute("SELECT * FROM alumni WHERE (first_name ILIKE %s) OR (last_name ILIKE %s) OR (city ILIKE %s) OR (industry ILIKE %s)ORDER BY grad_year DESC LIMIT 5", (interm,interm,interm,interm))
            return cur.fetchall()