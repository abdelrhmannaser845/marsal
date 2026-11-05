import pytest
from pathlib import Path
from src.utils.parser import ingest_records, _match_column


def test_match_column_aliases():
    assert _match_column("Student ID") == "student_id"
    assert _match_column("كود الطالب") == "student_id"
    assert _match_column("WhatsApp") == "phone"
    assert _match_column("الموبايل") == "phone"
    assert _match_column("البريد الإلكتروني") == "email"
    assert _match_column("midterm") == "midterm"
    assert _match_column("عملي") == "lab"
    assert _match_column("المجموع") == "total"


def test_ingest_sample_csv():
    csv_file = Path("data/students_sample.csv")
    records, errors = ingest_records(csv_file)
    assert len(records) >= 1
    assert len(errors) == 0

    first = records[0]
    assert first.student_id == "220769"
    assert first.phone == "+201120844781"
    assert first.midterm == 12.0
    assert first.lab == 15.0
    assert first.oral == 5.0
    assert first.total == 32.0


def test_ingest_sample_excel():
    xlsx_file = Path("data/students_sample.xlsx")
    records, errors = ingest_records(xlsx_file)
    assert len(records) >= 1
    assert len(errors) == 0
    assert records[0].student_id == "220769"
