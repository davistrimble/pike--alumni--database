"""Tests for scripts/import_alumni.py. All names and emails are made up."""

import pathlib
import sys

from conftest import query

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))

import import_alumni as imp  # noqa: E402

CSV = """﻿First Name,Last Name,Email Address,LinkedIn URL,Class,Company,Industry,City,State
  sam ,  TESTER ,Sam.Tester@Example.COM ,linkedin.com/in/SamTester/?trk=x,'19,Acme Co,Finance,  Nashville ,Tennessee
Sam,Tester,,https://www.linkedin.com/in/samtester,2019,,,,
Pat,McTest,pat@example,https://example.com/pat,Class of 2010,,Law,Austin,tx
,NoFirst,nofirst@example.com,,,,,,
Michael,Smith,MSMITH@gmail.com,,2012,Goldman Sachs,Finance,Charlotte,NC
"""


def write_csv(tmp_path):
    path = tmp_path / "alumni.csv"
    path.write_text(CSV, encoding="utf-8")
    return path


def test_cleaners():
    assert imp.clean_text("  a   b  ") == "a b"
    assert imp.clean_text("   ") is None
    assert imp.clean_name("o'BRIEN".upper()) == "O'Brien"
    assert imp.clean_name("McDonald") == "McDonald"
    assert imp.clean_email(" Mailto:A@B.COM ") == "a@b.com"
    assert imp.clean_email("not-an-email") is None
    assert imp.clean_linkedin("http://linkedin.com/in/Foo-Bar/") == "https://www.linkedin.com/in/foo-bar"
    assert imp.clean_linkedin("https://www.linkedin.com/company/acme") is None
    assert imp.clean_year("2019.0") == 2019
    assert imp.clean_year("'05") == 2005
    assert imp.clean_year("'85") == 1985
    assert imp.clean_year("soon") is None
    assert imp.clean_state("tennessee") == "TN"
    assert imp.clean_state("tn") == "TN"
    assert imp.clean_state("London") == "London"


def test_prepare_cleans_merges_and_reports(tmp_path):
    rows, report = imp.prepare(imp.read_csv(write_csv(tmp_path)))
    assert report["read"] == 5
    assert report["merged"] == 1
    assert any("missing first or last name" in s for s in report["skipped"])
    assert any("invalid email" in w for w in report["warnings"])
    assert any("non-profile LinkedIn" in w for w in report["warnings"])

    sam = next(r for r in rows if r["last_name"] == "Tester")
    assert sam == {
        "first_name": "Sam",
        "last_name": "Tester",
        "email": "sam.tester@example.com",
        "linkedin": "https://www.linkedin.com/in/samtester",
        "grad_year": 2019,
        "industry": "Finance",
        "company_name": "Acme Co",
        "city": "Nashville",
        "state_name": "TN",
    }
    pat = next(r for r in rows if r["last_name"] == "McTest")
    assert pat["email"] is None and pat["linkedin"] is None
    assert pat["grad_year"] == 2010 and pat["state_name"] == "TX"


def test_dedupe_warns_on_conflicting_values():
    a = imp.clean_row({"first_name": "Al", "last_name": "Dup", "grad_year": "2000", "city": "Austin"})
    b = imp.clean_row({"first_name": "al", "last_name": "dup", "grad_year": "2000", "city": "Dallas"})
    rows, merged, warnings = imp.dedupe([a, b])
    assert merged == 1 and rows[0]["city"] == "Austin"
    assert any("Dallas" in w for w in warnings)


def test_dry_run_writes_nothing(tmp_path, capsys):
    before = query("SELECT count(*) AS n FROM alumni")[0]["n"]
    imp.main([str(write_csv(tmp_path))])
    assert query("SELECT count(*) AS n FROM alumni")[0]["n"] == before
    assert "Dry run" in capsys.readouterr().out


def test_commit_inserts_updates_and_is_idempotent(tmp_path, capsys):
    path = write_csv(tmp_path)
    before = query("SELECT count(*) AS n FROM alumni")[0]["n"]

    imp.main([str(path), "--commit"])
    out = capsys.readouterr().out
    assert "2 inserted, 1 updated, 0 unchanged" in out
    assert query("SELECT count(*) AS n FROM alumni")[0]["n"] == before + 2

    # Michael Smith already existed (seed data): matched by email, city updated,
    # and his LinkedIn (blank in the CSV) was not erased.
    smith = query("SELECT * FROM alumni WHERE lower(email) = 'msmith@gmail.com'")
    assert len(smith) == 1
    assert smith[0]["city"] == "Charlotte"
    assert smith[0]["linkedin"] == "https://www.linkedin.com/in/michaelsmith"

    imp.main([str(path), "--commit"])
    assert "0 inserted, 0 updated, 3 unchanged" in capsys.readouterr().out
    assert query("SELECT count(*) AS n FROM alumni")[0]["n"] == before + 2
