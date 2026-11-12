import os
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

def get_member(email):
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    with psycopg.connect(database_url) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT id, email, password_hash, is_admin FROM members WHERE email = %s", (email.strip().lower(),))
            return cur.fetchone()

def set_password(email, password_hash):
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    with psycopg.connect(database_url) as conn:
            with conn.cursor() as cur:
                 cur.execute("UPDATE members SET password_hash = %s WHERE email = %s", (password_hash, email))

if __name__ == "__main__":
    print(get_member(" john@gmail.com"))
    print (get_member(""))