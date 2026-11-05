SELECT * FROM alumni 
WHERE (first_name ILIKE :'st') 
OR (last_name ILIKE :'st') 
OR (city ILIKE :'st') 
OR (industry ILIKE :'st') 
ORDER BY grad_year DESC 
LIMIT 5;