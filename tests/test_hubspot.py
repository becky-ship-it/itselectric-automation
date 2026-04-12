"""Tests for HubSpot contact upsert and transactional email send."""

from unittest.mock import MagicMock, patch

import pytest

from itselectric.hubspot import send_email, upsert_contact


class TestUpsertContact:
    def _mock_upsert_response(self, contact_id: str) -> MagicMock:
        resp = MagicMock()
        resp.json.return_value = {"results": [{"id": contact_id}]}
        resp.raise_for_status = MagicMock()
        return resp

    def test_returns_contact_id_on_success(self):
        """A successful upsert returns the contact ID from the results array."""
        with patch("itselectric.hubspot.requests.post") as mock_post:
            mock_post.return_value = self._mock_upsert_response("101")

            contact_id = upsert_contact(
                access_token="test-token",
                name="Jane Smith",
                email="jane@example.com",
                address="123 Main St",
            )

        assert contact_id == "101"

    def test_calls_batch_upsert_endpoint(self):
        """Uses the batch upsert endpoint with email as the idProperty."""
        with patch("itselectric.hubspot.requests.post") as mock_post:
            mock_post.return_value = self._mock_upsert_response("101")

            upsert_contact(
                access_token="test-token",
                name="Jane Smith",
                email="jane@example.com",
                address="123 Main St",
            )

        call_args = mock_post.call_args
        assert call_args.args[0].endswith("/contacts/batch/upsert")
        body = call_args.kwargs["json"]
        assert body["inputs"][0]["idProperty"] == "email"
        assert body["inputs"][0]["id"] == "jane@example.com"

    def test_splits_name_into_first_and_last(self):
        """Full name is split on first space: 'Jane Smith' → firstname=Jane, lastname=Smith."""
        with patch("itselectric.hubspot.requests.post") as mock_post:
            mock_post.return_value = self._mock_upsert_response("7")

            upsert_contact(
                access_token="tok",
                name="Jane Smith",
                email="j@example.com",
                address="1 Place",
            )

        props = mock_post.call_args.kwargs["json"]["inputs"][0]["properties"]
        assert props["firstname"] == "Jane"
        assert props["lastname"] == "Smith"

    def test_single_word_name_uses_empty_lastname(self):
        """A name with no space sets lastname to empty string."""
        with patch("itselectric.hubspot.requests.post") as mock_post:
            mock_post.return_value = self._mock_upsert_response("8")

            upsert_contact(
                access_token="tok",
                name="Madonna",
                email="m@example.com",
                address="1 Place",
            )

        props = mock_post.call_args.kwargs["json"]["inputs"][0]["properties"]
        assert props["firstname"] == "Madonna"
        assert props["lastname"] == ""

    def test_returns_none_on_request_error(self):
        """If the API call raises an exception, return None (don't crash the pipeline)."""
        import requests as req

        with patch("itselectric.hubspot.requests.post") as mock_post:
            mock_post.side_effect = req.RequestException("network error")

            result = upsert_contact(
                access_token="tok",
                name="Jane Smith",
                email="j@example.com",
                address="1 Place",
            )

        assert result is None


class TestSendEmail:
    def _mock_response(self) -> MagicMock:
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        return resp

    def test_posts_to_transactional_endpoint(self):
        """Calls the correct HubSpot transactional send endpoint."""
        with patch("itselectric.hubspot.requests.post") as mock_post:
            mock_post.return_value = self._mock_response()
            send_email(access_token="tok", to_email="driver@example.com", email_id=12345)

        url = mock_post.call_args.args[0]
        assert "/marketing/v3/transactional/single-email/send" in url

    def test_sends_correct_body(self):
        """Request body contains emailId and message.to."""
        with patch("itselectric.hubspot.requests.post") as mock_post:
            mock_post.return_value = self._mock_response()
            send_email(access_token="tok", to_email="driver@example.com", email_id=12345)

        body = mock_post.call_args.kwargs["json"]
        assert body["emailId"] == 12345
        assert body["message"]["to"] == "driver@example.com"

    def test_returns_true_on_success(self):
        with patch("itselectric.hubspot.requests.post") as mock_post:
            mock_post.return_value = self._mock_response()
            result = send_email(access_token="tok", to_email="d@example.com", email_id=99)
        assert result is True

    def test_returns_false_on_request_error(self):
        import requests as req
        with patch("itselectric.hubspot.requests.post") as mock_post:
            mock_post.side_effect = req.RequestException("network error")
            result = send_email(access_token="tok", to_email="d@example.com", email_id=99)
        assert result is False
