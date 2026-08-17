"""Tests for HubSpot contact upsert."""

from unittest.mock import MagicMock, patch

from itselectric.hubspot import upsert_contact


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
        import requests as req  # type: ignore

        with patch("itselectric.hubspot.requests.post") as mock_post:
            mock_post.side_effect = req.RequestException("network error")

            result = upsert_contact(
                access_token="tok",
                name="Jane Smith",
                email="j@example.com",
                address="1 Place",
            )

        assert result is None

    def test_apartment_does_not_corrupt_city_via_geocodio(self):
        """With a Geocodio key, city comes from structured components, not the raw
        comma-split, so an apartment number never lands in the city field."""
        geo_loc = MagicMock()
        geo_loc.raw = {"address_components": {"city": "Brooklyn", "state": "NY", "zip": "11201"}}

        with (
            patch("itselectric.hubspot.requests.post") as mock_post,
            patch("itselectric.geo._geocodio") as mock_geocodio,
        ):
            mock_post.return_value = self._mock_upsert_response("55")
            mock_geocodio.return_value.geocode.return_value = geo_loc

            upsert_contact(
                access_token="tok",
                name="Jane Smith",
                email="j@example.com",
                address="123 Main St, Apt 4, Brooklyn, NY 11201",
                geocodio_api_key="key123",
            )

        props = mock_post.call_args.kwargs["json"]["inputs"][0]["properties"]
        assert props["city"] == "Brooklyn"
        assert props["state"] == "NY"
        assert props["zip"] == "11201"
        # Full mailing address preserved on the street line.
        assert props["address"] == "123 Main St, Apt 4, Brooklyn, NY 11201"

    def test_apartment_regex_fallback_without_key(self):
        """Without a key, regex fallback still keeps the apartment out of city."""
        with patch("itselectric.hubspot.requests.post") as mock_post:
            mock_post.return_value = self._mock_upsert_response("56")

            upsert_contact(
                access_token="tok",
                name="Jane Smith",
                email="j@example.com",
                address="123 Main St, Apt 4, Brooklyn, NY 11201",
            )

        props = mock_post.call_args.kwargs["json"]["inputs"][0]["properties"]
        assert props["city"] == "Brooklyn"
