"""Tests for the Click CLI interface."""

import pytest
from click.testing import CliRunner

from trip_cli.cli import cli, main
from trip_cli.core.search import HotelSearchRequest


@pytest.fixture
def runner():
    return CliRunner()


class TestCliBasics:
    def test_help(self, runner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Trip.com hotel search CLI" in result.output
        assert "hotel" in result.output

    def test_version(self, runner):
        result = runner.invoke(cli, ["version"])
        assert result.exit_code == 0
        assert "trip-cli" in result.output

    def test_url_command(self, runner):
        result = runner.invoke(cli, ["url", "--city", "Singapore", "--checkin", "2026-07-15", "--checkout", "2026-07-18"])
        assert result.exit_code == 0
        assert "trip.com" in result.output
        assert "/hotels/list" in result.output
        assert "city=" in result.output


class TestHotelSearchCli:
    def test_hotel_search_basic(self, runner, monkeypatch, mock_search_result):
        def fake_run(req: HotelSearchRequest):
            return mock_search_result

        monkeypatch.setattr("trip_cli.cli.run_hotel_search", fake_run)

        result = runner.invoke(
            cli,
            [
                "hotel",
                "search",
                "--city",
                "Singapore",
                "--checkin",
                "2026-07-15",
                "--checkout",
                "2026-07-18",
                "--max-results",
                "2",
            ],
        )
        assert result.exit_code == 0
        assert "Trip.com Hotel Search" in result.output
        assert "Singapore" in result.output
        assert "Raffles" in result.output

    def test_hotel_search_json(self, runner, monkeypatch, mock_search_result):
        def fake_run(req):
            return mock_search_result

        monkeypatch.setattr("trip_cli.cli.run_hotel_search", fake_run)

        result = runner.invoke(
            cli,
            [
                "--json",
                "hotel",
                "search",
                "--city",
                "Singapore",
                "--checkin",
                "2026-07-15",
                "--checkout",
                "2026-07-18",
            ],
        )
        assert result.exit_code == 0
        assert '"query"' in result.output
        assert "cheapest_usd" in result.output or "280" in result.output
        assert "Raffles Singapore" in result.output

    def test_invalid_input_shows_error(self, runner):
        result = runner.invoke(cli, ["hotel", "search", "--city", "A", "--checkin", "bad-date"])
        assert result.exit_code != 0
        assert "Error" in result.output or "city" in result.output.lower()


class TestErrorHandling:
    def test_json_error_output(self, runner, monkeypatch):
        def fake_run(req):
            raise ValueError("Bad city")

        monkeypatch.setattr("trip_cli.cli.run_hotel_search", fake_run)

        result = runner.invoke(
            cli, ["--json", "hotel", "search", "--city", "X", "--checkin", "2026-07-01", "--checkout", "2026-07-04"]
        )
        assert result.exit_code == 1
        assert '"error"' in result.output
        assert "Bad city" in result.output


def test_main_entrypoint(runner):
    """Sanity check that the CLI can be invoked."""
    result = runner.invoke(cli, ["--help"])
    assert "hotel" in result.output or "Trip.com" in result.output


class TestConfigCli:
    def test_config_set_get_list_unset(self, runner, mock_config):
        # Set
        result = runner.invoke(cli, ["config", "set", "currency", "SGD"])
        assert result.exit_code == 0
        assert "Set currency = SGD" in result.output

        # Get
        result = runner.invoke(cli, ["config", "get", "currency"])
        assert result.exit_code == 0
        assert "currency = SGD" in result.output

        # List
        result = runner.invoke(cli, ["config", "list"])
        assert result.exit_code == 0
        assert "currency = SGD" in result.output

        # Unset
        result = runner.invoke(cli, ["config", "unset", "currency"])
        assert result.exit_code == 0
        assert "Unset currency" in result.output

        # After unset, should fall back to default
        result = runner.invoke(cli, ["config", "get", "currency"])
        assert result.exit_code == 0
        assert "currency = USD" in result.output  # from DEFAULTS in the mock


class TestCurrencyFromConfig:
    def test_search_uses_config_currency_when_not_provided(self, runner, monkeypatch, mock_search_result, mock_config):
        captured_currency = {}

        def fake_run(req: HotelSearchRequest):
            captured_currency["value"] = req.currency
            return mock_search_result

        monkeypatch.setattr("trip_cli.cli.run_hotel_search", fake_run)

        # Set config
        mock_config["currency"] = "EUR"

        result = runner.invoke(
            cli,
            [
                "hotel",
                "search",
                "--city",
                "Singapore",
                "--checkin",
                "2026-07-15",
                "--checkout",
                "2026-07-18",
            ],
        )
        assert result.exit_code == 0
        assert captured_currency["value"] == "EUR"

    def test_details_uses_config_currency_when_not_provided(self, runner, monkeypatch, mock_config):
        captured = {}

        def fake_get_details(hid, cur, city=None):
            captured["currency"] = cur
            return {"name": "Test Hotel", "hotel_id": hid, "currency": cur}

        monkeypatch.setattr("trip_cli.cli.get_hotel_details", fake_get_details)

        mock_config["currency"] = "JPY"

        result = runner.invoke(cli, ["hotel", "details", "12345"])
        assert result.exit_code == 0
        assert captured["currency"] == "JPY"

    def test_search_overrides_config_with_flag(self, runner, monkeypatch, mock_search_result, mock_config):
        captured = {}

        def fake_run(req: HotelSearchRequest):
            captured["currency"] = req.currency
            return mock_search_result

        monkeypatch.setattr("trip_cli.cli.run_hotel_search", fake_run)
        mock_config["currency"] = "EUR"

        result = runner.invoke(
            cli,
            [
                "hotel",
                "search",
                "--city",
                "Singapore",
                "--checkin",
                "2026-07-15",
                "--checkout",
                "2026-07-18",
                "--currency",
                "HKD",
            ],
        )
        assert result.exit_code == 0
        assert captured["currency"] == "HKD"
