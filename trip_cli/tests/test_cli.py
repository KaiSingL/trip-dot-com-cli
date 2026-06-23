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
        assert "sg.trip.com" in result.output
        assert "singapore-hotels-list" in result.output


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
