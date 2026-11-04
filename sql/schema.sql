DROP TABLE IF EXISTS alumni;

CREATE TABLE alumni (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT UNIQUE,
    linkedin TEXT,
    grad_year INTEGER CHECK (grad_year < 3000 and grad_year > 1900)
    industry TEXT, 
    company_name TEXT
    city TEXT
    state_name TEXT
);


