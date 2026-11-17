"""Clean an alumni CSV and load it into the alumni table.

Dry run (default, changes nothing, prints a report):
    python scripts/import_alumni.py data/alumni.csv
Actually write to the database:
    python scripts/import_alumni.py data/alumni.csv --commit

Expected header (order doesn't matter, extra columns are ignored, and common
variants like "First Name", "Grad Year", "Company", "State" are recognized):
    first_name,last_name,email,linkedin,grad_year,industry,company_name,city,state_name

Keep real CSVs in data/ (git-ignored). Never commit them.

What it does:
- trims and collapses spaces, turns blank cells into NULL
- lowercases emails, drops ones that don't look like emails
- normalizes LinkedIn URLs to https://www.linkedin.com/in/<handle>
- turns state names into 2-letter codes ("Tennessee" -> "TN")
- merges duplicate rows (same email, or same name + grad year if no email)
- matches existing alumni the same way and only fills in / updates fields,
  so running it twice is safe
"""

import argparse
import csv
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

FIELDS = [
    "first_name",
    "last_name",
    "email",
    "linkedin",
    "grad_year",
    "industry",
    "company_name",
    "city",
    "state_name",
]

# Header variants people actually use -> our column name.
HEADER_ALIASES = {
    "first": "first_name",
    "firstname": "first_name",
    "last": "last_name",
    "lastname": "last_name",
    "surname": "last_name",
    "emailaddress": "email",
    "linkedinurl": "linkedin",
    "linkedinprofile": "linkedin",
    "gradyear": "grad_year",
    "graduationyear": "grad_year",
    "class": "grad_year",
    "classyear": "grad_year",
    "year": "grad_year",
    "company": "company_name",
    "employer": "company_name",
    "state": "state_name",
}

STATES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "district of columbia": "DC", "washington dc": "DC", "washington d.c.": "DC",
    "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
    "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN",
    "mississippi": "MS", "missouri": "MO", "montana": "MT", "nebraska": "NE",
    "nevada": "NV", "new hampshire": "NH", "new jersey": "NJ",
    "new mexico": "NM", "new york": "NY", "north carolina": "NC",
    "north dakota": "ND", "ohio": "OH", "oklahoma": "OK", "oregon": "OR",
    "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
    "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT",
    "vermont": "VT", "virginia": "VA", "washington": "WA",
    "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY",
}
STATE_CODES = set(STATES.values())

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
LINKEDIN_RE = re.compile(r"linkedin\.com/in/([^/?#\s]+)", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Cleaning one value at a time
# ---------------------------------------------------------------------------


def clean_text(value):
    """Trim, collapse inner whitespace, and turn blanks into None."""
    if value is None:
        return None
    value = re.sub(r"\s+", " ", str(value)).strip()
    return value or None


def clean_name(value):
    """Fix ALL-CAPS or all-lowercase names; leave mixed case ("McDonald") alone."""
    value = clean_text(value)
    if value and (value.islower() or value.isupper()):
        value = value.title()
    return value


def clean_email(value):
    value = clean_text(value)
    if not value:
        return None
    value = value.lower().removeprefix("mailto:")
    return value if EMAIL_RE.match(value) else None


def clean_linkedin(value):
    """Return https://www.linkedin.com/in/<handle>, or None if it isn't a profile URL."""
    value = clean_text(value)
    if not value:
        return None
    match = LINKEDIN_RE.search(value)
    if not match:
        return None
    return f"https://www.linkedin.com/in/{match.group(1).lower()}"


def clean_year(value):
    value = clean_text(value)
    if not value:
        return None
    # Accept "2019", "2019.0" (Excel), "'19", "Class of 2019".
    match = re.search(r"(\d{4})", value)
    if match:
        year = int(match.group(1))
    else:
        match = re.fullmatch(r"'?(\d{2})", value)
        if not match:
            return None
        two = int(match.group(1))
        year = 2000 + two if two <= 40 else 1900 + two
    return year if 1900 < year < 3000 else None


def clean_state(value):
    value = clean_text(value)
    if not value:
        return None
    key = value.lower().rstrip(".")
    if key.upper() in STATE_CODES:
        return key.upper()
    return STATES.get(key, value)  # unknown (e.g. "London"): keep as typed


def normalize_header(name):
    key = re.sub(r"[^a-z]", "", (name or "").lower())
    if key in HEADER_ALIASES:
        return HEADER_ALIASES[key]
    snake = re.sub(r"[^a-z]+", "_", (name or "").lower()).strip("_")
    return snake if snake in FIELDS else None


def clean_row(raw):
    """Map a CSV dict to our columns and clean every value."""
    row = {field: None for field in FIELDS}
    for header, value in raw.items():
        field = normalize_header(header)
        if field and row[field] is None:
            row[field] = value
    return {
        "first_name": clean_name(row["first_name"]),
        "last_name": clean_name(row["last_name"]),
        "email": clean_email(row["email"]),
        "linkedin": clean_linkedin(row["linkedin"]),
        "grad_year": clean_year(row["grad_year"]),
        "industry": clean_text(row["industry"]),
        "company_name": clean_text(row["company_name"]),
        "city": clean_text(row["city"]),
        "state_name": clean_state(row["state_name"]),
    }


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------


def identity_keys(row):
    """Keys that mean "same person": email, and name + grad year."""
    keys = []
    if row["email"]:
        keys.append(("email", row["email"]))
    if row["first_name"] and row["last_name"] and row["grad_year"]:
        keys.append(
            ("name", row["first_name"].lower(), row["last_name"].lower(), row["grad_year"])
        )
    return keys


def merge(into, other):
    """Fill blanks in `into` with values from `other`.

    Returns the fields where both rows had different non-blank values
    (the first row's value is kept).
    """
    conflicts = []
    for field in FIELDS:
        if into[field] is None:
            into[field] = other[field]
        elif other[field] is not None and other[field] != into[field]:
            conflicts.append(field)
    return conflicts


def dedupe(rows):
    """Merge rows that share an email or name + grad year.

    Returns (rows, merged_count, warnings).
    """
    kept, index, merged, warnings = [], {}, 0, []
    for row in rows:
        existing = next((index[k] for k in identity_keys(row) if k in index), None)
        if existing is None:
            kept.append(row)
            existing = row
        else:
            for field in merge(existing, row):
                warnings.append(
                    f"{existing['first_name']} {existing['last_name']}: kept "
                    f"{field}={existing[field]!r}, ignored duplicate's {row[field]!r}"
                )
            merged += 1
        for key in identity_keys(existing):
            index.setdefault(key, existing)
    return kept, merged, warnings


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------


def find_existing(cur, row):
    if row["email"]:
        found = cur.execute(
            "SELECT * FROM alumni WHERE lower(email) = %s ORDER BY id LIMIT 1", (row["email"],)
        ).fetchone()
        if found:
            return found
    if row["first_name"] and row["last_name"] and row["grad_year"]:
        return cur.execute(
            """
            SELECT * FROM alumni
            WHERE lower(first_name) = lower(%s) AND lower(last_name) = lower(%s)
              AND grad_year = %s
            ORDER BY id LIMIT 1
            """,
            (row["first_name"], row["last_name"], row["grad_year"]),
        ).fetchone()
    return None


def load(rows, conn):
    """Insert new alumni and update changed fields on existing ones.

    New non-blank values win; blanks never erase what's already stored.
    Returns counts.
    """
    counts = {"inserted": 0, "updated": 0, "unchanged": 0}
    cur = conn.cursor()
    for row in rows:
        existing = find_existing(cur, row)
        if existing is None:
            cur.execute(
                f"INSERT INTO alumni ({', '.join(FIELDS)}) "
                f"VALUES ({', '.join(['%s'] * len(FIELDS))})",
                [row[f] for f in FIELDS],
            )
            counts["inserted"] += 1
            continue
        changes = {
            f: row[f] for f in FIELDS if row[f] is not None and row[f] != existing[f]
        }
        if not changes:
            counts["unchanged"] += 1
            continue
        assignments = ", ".join(f"{f} = %s" for f in changes)  # names from FIELDS only
        cur.execute(
            f"UPDATE alumni SET {assignments} WHERE id = %s",
            [*changes.values(), existing["id"]],
        )
        counts["updated"] += 1
    return counts


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------


def read_csv(path):
    # utf-8-sig strips the invisible BOM Excel adds to the first header.
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def prepare(raw_rows):
    """Clean + validate + dedupe. Returns (rows, report dict)."""
    report = {"read": len(raw_rows), "skipped": [], "warnings": []}
    cleaned = []
    for line_no, raw in enumerate(raw_rows, start=2):  # line 1 is the header
        row = clean_row(raw)
        if not row["first_name"] or not row["last_name"]:
            report["skipped"].append(f"line {line_no}: missing first or last name")
            continue
        raw_email = clean_text(next((v for k, v in raw.items() if normalize_header(k) == "email"), None))
        if raw_email and not row["email"]:
            report["warnings"].append(f"line {line_no}: dropped invalid email {raw_email!r}")
        raw_li = clean_text(next((v for k, v in raw.items() if normalize_header(k) == "linkedin"), None))
        if raw_li and not row["linkedin"]:
            report["warnings"].append(f"line {line_no}: dropped non-profile LinkedIn {raw_li!r}")
        cleaned.append(row)
    rows, report["merged"], conflicts = dedupe(cleaned)
    report["warnings"].extend(conflicts)
    return rows, report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("csv_path")
    parser.add_argument("--commit", action="store_true", help="write to the database (default: dry run)")
    args = parser.parse_args(argv)

    from db import connect

    rows, report = prepare(read_csv(args.csv_path))
    print(f"Read {report['read']} rows -> {len(rows)} alumni after merging {report['merged']} duplicate(s).")
    for message in report["skipped"]:
        print(f"  skipped  {message}")
    for message in report["warnings"]:
        print(f"  warning  {message}")

    with connect() as conn:
        counts = load(rows, conn)
        if not args.commit:
            conn.rollback()
    verb = "Wrote" if args.commit else "Dry run, nothing written. Would have"
    print(
        f"{verb}: {counts['inserted']} inserted, {counts['updated']} updated, "
        f"{counts['unchanged']} unchanged."
    )
    if not args.commit:
        print("Re-run with --commit to save.")


if __name__ == "__main__":
    main()
