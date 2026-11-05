import os
import psycopg
from dotenv import load_dotenv
load_dotenv()
database_url = os.getenv("DATABASE_URL")


def search(term):
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            interm = f"%{term}%"
            cur.execute("SELECT * FROM alumni WHERE (first_name ILIKE %s) OR (last_name ILIKE %s) OR (city ILIKE %s) OR (industry ILIKE %s)ORDER BY grad_year DESC LIMIT 5", (interm,interm,interm,interm))
            return cur.fetchall()
s = input("Search: ")
r = search(s)
for i in range (0,len(r)):
    print(r[i])