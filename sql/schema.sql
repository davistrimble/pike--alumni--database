DROP TABLE IF EXISTS alumni;

CREATE TABLE alumni (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT UNIQUE,
    linkedin TEXT,
    grad_year INTEGER CHECK (grad_year < 3000 and grad_year > 1900),
    industry TEXT, 
    company_name TEXT,
    city TEXT,
    state_name TEXT
);

INSERT INTO alumni (first_name, last_name, email, linkedin, grad_year, industry, company_name, city, state_name)
VALUES ('john', 'doe', 'johndoe@gmail.com', NULL, 2005, 'IB', NULL, 'Atlanta', 'GA');

INSERT INTO alumni (first_name, last_name, email, linkedin, grad_year, industry, company_name, city, state_name)
VALUES
    ('Michael', 'Smith',      'msmith@gmail.com',        'linkedin.com/in/michaelsmith',           2012, 'Finance',            'Goldman Sachs',        'Nashville',  'TN'),        
    ('Ryan',    'O''Brien',   'ryan.obrien@outlook.com', 'linkedin.com/in/ryanobrien',             2016, 'Technology',         'Nike',                 'Portland',   'OR'),      
    ('Tyler',   'Nguyen',     'tnguyen@yahoo.com',       NULL,                                     2021, 'Healthcare',         'Maine Medical Center', 'Portland',   'ME'),        
    ('Robert',  'Hayes',      NULL,                      NULL,                                     1978, 'Real Estate',        NULL,                   'Birmingham', 'AL'),        
    ('Carlos',  'De La Cruz', 'cdelacruz@gmail.com',     'linkedin.com/in/carlosdelacruz',         2019, 'finance',            'Fidelity',             'Nashville ', 'Tennessee'),
    ('Will',    'Patel',      'wpatel@gmail.com',        'https://www.linkedin.com/in/willpatel/', 2024, 'Investment Banking', 'J.P. Morgan',          'New York',   'NY'),        
    ('Jake',    'Miller',     'jake.miller@gmail.com',   NULL,                                     2015, 'Consulting',         'Deloitte',             'Atlanta',    'GA'),        
    ('Jake',    'Miller',     'Jake.Miller@gmail.com',   'linkedin.com/in/jakemiller',             2015, 'Consulting',         'Deloitte',             'Atlanta',    'GA');       


