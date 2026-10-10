import pytest
import httpx
import pytest

from app.ingestion.open_meteo import OpenMeteoClient, OpenMeteoError


VALID_RESPONSE = {
    "hourly": {
        "time": [
            "2026-10-08T00:00",
            "2026-10-08T01:00",
        ],
        "precipitation": [
            0.0,
            0.5,
        ],
        "precipitation_probability": [
            0,
            40,
        ],
        "wind_speed_10m": [
            10.2,
            12.5,
        ],
        "wind_gusts_10m": [
            18.0,
            22.1,
        ],
        "weather_code": [
            0,
            61,
        ],
    }
}


class MockResponse:
    def __init__(self, data=None, status_code=200):
        self.data = data
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request(
                "GET",
                "https://api.open-meteo.com/v1/forecast",
            )
            response = httpx.Response(
                self.status_code,
                request=request,
            )
            raise httpx.HTTPStatusError(
                f"HTTP {self.status_code}",
                request=request,
                response=response,
            )

    def json(self):
        return self.data


class MockAsyncClient:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def get(self, *args, **kwargs):
        if self.error:
            raise self.error

        return self.response


@pytest.mark.asyncio
async def test_fetch_precipitation():
    client = OpenMeteoClient()

    records = await client.fetch_precipitation(
        lat=28.6139,
        lon=77.2090,
    )

    assert len(records) > 0

    record = records[0]

    assert record.data_type == "weather"
    assert record.source == "open_meteo"
    assert record.location.coordinates == [77.2090, 28.6139]
    assert 0 <= record.probability <= 100
    assert "precipitation_mm" in record.specific_data
    assert "wind_speed_kmh" in record.specific_data
    assert "wind_gusts_kmh" in record.specific_data
    assert "weather_code" in record.specific_data


@pytest.mark.asyncio
async def test_fetch_precipitation_success(monkeypatch):

    mock_response = MockResponse(VALID_RESPONSE)

    monkeypatch.setattr(
        "httpx.AsyncClient",
        lambda: MockAsyncClient(response=mock_response),
    )

    client = OpenMeteoClient()

    records = await client.fetch_precipitation(
        lat=12.9716,
        lon=77.5946,
    )

    assert len(records) == 2

    record = records[0]

    assert record.data_type == "weather"
    assert record.source == "open_meteo"
    assert record.magnitude == 0.0
    assert record.probability == 0
    assert record.specific_data["precipitation_mm"] == 0.0
    assert record.specific_data["wind_speed_kmh"] == 10.2
    assert record.specific_data["wind_gusts_kmh"] == 18.0
    assert record.specific_data["weather_code"] == 0

async def test_http_error(monkeypatch):
    mock_response = MockResponse(
        status_code=500,
    )

    monkeypatch.setattr(
        "httpx.AsyncClient",
        lambda: MockAsyncClient(response=mock_response),

    )

    client = OpenMeteoClient()
    with pytest.raises(OpenMeteoError, match="HTTP 500"):
        await client.fetch_precipitation(
            lat=12.9716,
            lon=77.5946,
        )

async def test_network_error(monkeypatch):

    request = httpx.Request(
        "GET",
        "https://api.open-meteo.com/v1/forecast",

    )

    network_error = httpx.ConnectError(
        "Connection failed",
        request=request,
    )

    monkeypatch.setattr(
        "httpx.AsyncClient",
        lambda: MockAsyncClient(error=network_error),
    )

    client = OpenMeteoClient()

    with pytest.raises(
        OpenMeteoError,
        match="Failed to connect to Open-Meteo",
    ):

        await client.fetch_precipitation(
            lat=12.9716,
            lon=77.5946,
        )


async def test_malformed_response(monkeypatch):
    malformed_response = MockResponse(
        {
            "something": "wrong",
        }
    )

    monkeypatch.setattr(
        "httpx.AsyncClient",
        lambda: MockAsyncClient(
            response=malformed_response,
        ),
    )

    client = OpenMeteoClient()

    with pytest.raises(
        OpenMeteoError,
        match="invalid response",
    ):
        await client.fetch_precipitation(
            lat=12.9716,
            lon=77.5946,
        )


async def test_mismatched_hourly_arrays(monkeypatch):
    bad_response = {
        "hourly": {
            "time": [
                "2026-10-08T00:00",
                "2026-10-08T01:00",
            ],
            "precipitation": [
                0.0,
            ],
            "precipitation_probability": [
                0,
                40,
            ],
        }
    }

    mock_response = MockResponse(bad_response)

    monkeypatch.setattr(
        "httpx.AsyncClient",
        lambda: MockAsyncClient(
            response=mock_response,
        ),
    )

    client = OpenMeteoClient()

    with pytest.raises(
        OpenMeteoError,
        match="hourly arrays with different lengths",
    ):
        await client.fetch_precipitation(
            lat=12.9716,
            lon=77.5946,
        )