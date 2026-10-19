import pytest
import httpx
import pytest

from app.ingestion.open_meteo import (
    OpenMeteoClient,
    OpenMeteoError,
    split_grid_record_id,
)


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


# --- fetch_precipitation_many (grid batch path) ------------------------------


class GridMockClient:
    """
    Returns one fake result per requested coordinate, in request order, and
    records how many HTTP calls were made (so chunking is observable).
    """

    def __init__(self, hourly=None):
        self.calls = 0
        self.hourly = hourly if hourly is not None else VALID_RESPONSE["hourly"]
        self.last_params = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def get(self, url, params=None, **kwargs):
        self.calls += 1
        self.last_params = params
        latitudes = params["latitude"].split(",")
        longitudes = params["longitude"].split(",")
        assert len(latitudes) == len(longitudes)

        return MockResponse(
            [
                {"latitude": float(lat), "longitude": float(lon),
                 "hourly": self.hourly}
                for lat, lon in zip(latitudes, longitudes)
            ]
        )


class ShortGridMockClient(GridMockClient):
    """Always answers with a single result, whatever was requested."""

    async def get(self, url, params=None, **kwargs):
        self.calls += 1
        return MockResponse([{"hourly": self.hourly}])


class ObjectGridMockClient(GridMockClient):
    """Answers with a bare object instead of a list."""

    async def get(self, url, params=None, **kwargs):
        self.calls += 1
        return MockResponse({"hourly": self.hourly})


async def test_many_returns_one_record_per_cell_per_hour(monkeypatch):
    mock = GridMockClient()
    monkeypatch.setattr("httpx.AsyncClient", lambda: mock)

    coords = [
        ("grid:0.1:100:200", 15.0, 75.0),
        ("grid:0.1:101:200", 15.1, 75.0),
    ]

    records = await OpenMeteoClient().fetch_precipitation_many(coords)

    # 2 cells x 2 forecast hours in the canned payload
    assert len(records) == 4
    assert mock.calls == 1

    # Order follows `coords`, grouped cell by cell
    assert all(r.id.startswith("grid:0.1:100:200:") for r in records[:2])
    assert all(r.id.startswith("grid:0.1:101:200:") for r in records[2:])

    # Coordinates come back on each record as [lon, lat]
    assert records[0].location.coordinates == [75.0, 15.0]
    assert records[2].location.coordinates == [75.0, 15.1]

    assert records[0].data_type == "weather"
    assert records[0].source == "open_meteo"


async def test_many_id_round_trips_to_cell_id(monkeypatch):
    """P2 recovers cell_id + time from the id; the colon-rich cell_id must survive."""
    monkeypatch.setattr("httpx.AsyncClient", lambda: GridMockClient())

    records = await OpenMeteoClient().fetch_precipitation_many(
        [("grid:0.1:100:200", 15.0, 75.0)]
    )

    assert records[0].id == "grid:0.1:100:200:2026-10-08T00:00"

    cell_id, time = split_grid_record_id(records[0].id)
    assert cell_id == "grid:0.1:100:200"
    assert time == "2026-10-08T00:00"


async def test_split_grid_record_id_rejects_non_grid_ids():
    with pytest.raises(ValueError, match="Malformed grid record id"):
        split_grid_record_id("open-meteo:15.0:75.0:2026-10-08T00:00")


async def test_many_chunks_requests_at_the_location_cap(monkeypatch):
    mock = GridMockClient()
    monkeypatch.setattr("httpx.AsyncClient", lambda: mock)

    client = OpenMeteoClient()
    monkeypatch.setattr(client, "MAX_LOCATIONS_PER_REQUEST", 2)

    coords = [
        (f"grid:0.1:{row}:0", 15.0 + row * 0.1, 75.0) for row in range(5)
    ]

    records = await client.fetch_precipitation_many(coords)

    # 5 cells at 2 per call -> 2 + 2 + 1
    assert mock.calls == 3
    assert len(records) == 10


async def test_many_with_no_coords_makes_no_http_call(monkeypatch):
    mock = GridMockClient()
    monkeypatch.setattr("httpx.AsyncClient", lambda: mock)

    assert await OpenMeteoClient().fetch_precipitation_many([]) == []
    assert mock.calls == 0


async def test_many_accepts_a_bare_object_response(monkeypatch):
    monkeypatch.setattr("httpx.AsyncClient", lambda: ObjectGridMockClient())

    records = await OpenMeteoClient().fetch_precipitation_many(
        [("grid:0.1:1:1", 15.0, 75.0)]
    )

    assert len(records) == 2


async def test_many_forwards_forecast_days(monkeypatch):
    mock = GridMockClient()
    monkeypatch.setattr("httpx.AsyncClient", lambda: mock)

    await OpenMeteoClient().fetch_precipitation_many(
        [("grid:0.1:1:1", 15.0, 75.0)],
        forecast_days=2,
    )

    assert mock.last_params["forecast_days"] == 2


async def test_many_omits_forecast_days_by_default(monkeypatch):
    """No hidden magic: without the argument we keep Open-Meteo's own default."""
    mock = GridMockClient()
    monkeypatch.setattr("httpx.AsyncClient", lambda: mock)

    await OpenMeteoClient().fetch_precipitation_many([("grid:0.1:1:1", 15.0, 75.0)])

    assert "forecast_days" not in mock.last_params


async def test_many_sends_every_cell_coordinate(monkeypatch):
    mock = GridMockClient()
    monkeypatch.setattr("httpx.AsyncClient", lambda: mock)

    coords = [
        ("grid:0.1:1:1", 15.0, 75.0),
        ("grid:0.1:2:1", 15.1, 75.1),
    ]

    await OpenMeteoClient().fetch_precipitation_many(coords)

    assert mock.last_params["latitude"] == "15.0,15.1"
    assert mock.last_params["longitude"] == "75.0,75.1"


async def test_many_errors_when_result_count_mismatches(monkeypatch):
    monkeypatch.setattr("httpx.AsyncClient", lambda: ShortGridMockClient())

    coords = [
        ("grid:0.1:1:1", 15.0, 75.0),
        ("grid:0.1:2:1", 15.1, 75.0),
    ]

    with pytest.raises(OpenMeteoError, match="1 results for 2 locations"):
        await OpenMeteoClient().fetch_precipitation_many(coords)


async def test_many_rejects_mismatched_hourly_arrays(monkeypatch):
    """The shared parser applies to batch results too."""
    bad_hourly = {
        "time": ["2026-10-08T00:00", "2026-10-08T01:00"],
        "precipitation": [0.0],
        "precipitation_probability": [0, 40],
    }
    monkeypatch.setattr(
        "httpx.AsyncClient", lambda: GridMockClient(hourly=bad_hourly)
    )

    with pytest.raises(OpenMeteoError, match="hourly arrays with different lengths"):
        await OpenMeteoClient().fetch_precipitation_many(
            [("grid:0.1:1:1", 15.0, 75.0)]
        )