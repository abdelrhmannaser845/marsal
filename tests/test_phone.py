import pytest
from src.utils.phone import normalize_phone, is_valid_phone


def test_normalize_egyptian_local_formats():
    assert normalize_phone("01120844781") == "+201120844781"
    assert normalize_phone("01012345678") == "+201012345678"
    assert normalize_phone("01234567890") == "+201234567890"
    assert normalize_phone("01555554321") == "+201555554321"


def test_normalize_already_international():
    assert normalize_phone("+201120844781") == "+201120844781"
    assert normalize_phone("201120844781") == "+201120844781"


def test_normalize_with_formatting_and_excel_floats():
    assert normalize_phone(" 011 2084 4781 ") == "+201120844781"
    assert normalize_phone("011-2084-4781") == "+201120844781"
    assert normalize_phone("(011) 2084-4781") == "+201120844781"
    assert normalize_phone(201120844781) == "+201120844781"
    assert normalize_phone("201120844781.0") == "+201120844781"


def test_is_valid_phone():
    assert is_valid_phone("01120844781") is True
    assert is_valid_phone("+201012345678") is True
    assert is_valid_phone("abc12345") is False
    assert is_valid_phone("") is False
