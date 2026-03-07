"""Tests for email extraction logic."""


from itselectric.extract import extract_parsed

SAMPLE_BODY = (
    "it's electric John Smith "
    "The user has an address of 123 Main St, Seattle WA 98101 "
    "and has an email of\n john@example.com\n"
    "Email address submitted in form\n john2@example.com"
)


def test_extract_parsed_match():
    result = extract_parsed(SAMPLE_BODY)
    assert result is not None
    assert result["name"] == "John Smith"
    assert result["address"] == "123 Main St, Seattle WA 98101"
    assert result["email_1"] == "john@example.com"
    assert result["email_2"] == "john2@example.com"


def test_extract_parsed_no_match():
    assert extract_parsed("Hello, just a regular email.") is None


def test_extract_parsed_empty():
    assert extract_parsed("") is None


def test_extract_parsed_none():
    assert extract_parsed(None) is None
