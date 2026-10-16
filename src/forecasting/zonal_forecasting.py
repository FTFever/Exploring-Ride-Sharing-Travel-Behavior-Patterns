"""Leakage-safe notebook 06 helpers. No model training occurs on import.
All file locations/settings are supplied in the notebook's first cell.
"""

from pathlib import Path
import copy, hashlib, importlib.metadata, json, time, warnings
import numpy as np
import pandas as pd
from pandas.tseries.holiday import USFederalHolidayCalendar
from sklearn.compose import ColumnTransformer, TransformedTargetRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from statsmodels.tsa.arima.model import ARIMA

HOURS = 168
CAT = ["zone_id", "borough", "hour", "day_of_week", "month", "holiday_name"]
GROUPS = {
    "zone_identity": ["zone_id", "borough"],
    "spatial": [
        "is_airport_zone",
        "zone_latitude",
        "zone_longitude",
        "zone_area_km2",
        "zone_unmapped",
    ],
    "calendar": [
        "forecast_horizon",
        "hour",
        "day_of_week",
        "month",
        "hour_of_week",
        "is_weekend",
        "hour_sin",
        "hour_cos",
        "annual_sin",
        "annual_cos",
    ],
    "holiday": [
        "is_holiday",
        "holiday_name",
        "is_observed_holiday",
        "days_to_holiday",
        "days_since_holiday",
        "is_year_end_period",
    ],
    "demand_lags": [
        "pickup_lag_168h",
        "pickup_lag_336h",
        "pickup_lag_504h",
        "same_hour_week_mean_4w",
    ],
    "demand_recent": [
        "recent_mean_7d",
        "recent_mean_28d",
        "recent_std_28d",
        "recent_trend_ratio",
    ],
    "weather": [
        "temperature_2m",
        "apparent_temperature",
        "relative_humidity_2m",
        "precipitation",
        "rain",
        "snowfall",
        "wind_speed_10m",
        "cloud_cover",
        "pressure_msl",
    ],
}
FEATURES = [v for cols in GROUPS.values() for v in cols]
WEATHER = GROUPS["weather"]

# A human-readable data dictionary complements the executable feature groups.
# Future weather values below are historical climatology, not observed test weather.
FEATURE_DEFINITIONS = {
    "zone_id": (
        "Taxi-zone LocationID; an identifier, not a numerical ordering.",
        "category",
    ),
    "borough": (
        "Borough recorded in the taxi-zone shapefile; Unknown when unmapped.",
        "category",
    ),
    "is_airport_zone": (
        "1 for EWR (1), JFK (132), or LaGuardia (138); otherwise 0.",
        "0/1",
    ),
    "zone_latitude": (
        "Latitude of a representative point within the zone geometry.",
        "degrees north",
    ),
    "zone_longitude": ("Longitude of the same representative point.", "degrees east"),
    "zone_area_km2": (
        "Zone polygon area calculated in a projected coordinate system.",
        "km²",
    ),
    "zone_unmapped": ("1 when the zone has no matching shapefile geometry.", "0/1"),
    "forecast_horizon": (
        "Hours ahead of issue time; horizon 1 is the first forecast hour.",
        "1–168",
    ),
    "hour": ("Local clock hour of the target timestamp.", "0–23"),
    "day_of_week": ("Target weekday: Monday=0 through Sunday=6.", "0–6"),
    "month": ("Calendar month of the target timestamp.", "1–12"),
    "hour_of_week": ("Target weekday × 24 + target hour.", "0–167"),
    "is_weekend": ("1 when the target falls on Saturday or Sunday.", "0/1"),
    "hour_sin": ("sin(2π × target hour / 24).", "unitless"),
    "hour_cos": ("cos(2π × target hour / 24).", "unitless"),
    "annual_sin": ("Sine of the annual cycle, accounting for leap years.", "unitless"),
    "annual_cos": (
        "Cosine of the annual cycle, accounting for leap years.",
        "unitless",
    ),
    "is_holiday": (
        "1 on a selected US federal actual or observed holiday date.",
        "0/1",
    ),
    "holiday_name": ("Federal holiday name for the target date, or none.", "category"),
    "is_observed_holiday": (
        "1 on a shifted observed date that differs from the actual holiday date.",
        "0/1",
    ),
    "days_to_holiday": (
        "Calendar days until the next selected holiday, including 0 today.",
        "days",
    ),
    "days_since_holiday": (
        "Calendar days since the previous selected holiday, including 0 today.",
        "days",
    ),
    "is_year_end_period": (
        "1 during the predefined December 24–January 2 period.",
        "0/1",
    ),
    "pickup_lag_168h": (
        "Same-zone pickups 168 clock hours before the target hour.",
        "trips/hour",
    ),
    "pickup_lag_336h": (
        "Same-zone pickups 336 clock hours before the target hour.",
        "trips/hour",
    ),
    "pickup_lag_504h": (
        "Same-zone pickups 504 clock hours before the target hour.",
        "trips/hour",
    ),
    "same_hour_week_mean_4w": (
        "Mean pickups at target lags 168, 336, 504 and 672 hours.",
        "trips/hour",
    ),
    "recent_mean_7d": (
        "Zone mean over 7 days strictly before the forecast origin; fixed across the week.",
        "trips/hour",
    ),
    "recent_mean_28d": (
        "Zone mean over 28 days strictly before the forecast origin.",
        "trips/hour",
    ),
    "recent_std_28d": (
        "Zone standard deviation over those same pre-origin 28 days.",
        "trips/hour",
    ),
    "recent_trend_ratio": (
        "Latest pre-origin 7-day mean divided by the preceding 7-day mean; missing if denominator=0.",
        "ratio",
    ),
    "temperature_2m": (
        "Past-only mean air temperature for the target month/hour.",
        "°C",
    ),
    "apparent_temperature": (
        "Past-only mean feels-like temperature for the target month/hour.",
        "°C",
    ),
    "relative_humidity_2m": (
        "Past-only mean relative humidity for the target month/hour.",
        "%",
    ),
    "precipitation": (
        "Past-only mean hourly total precipitation for the target month/hour.",
        "mm/hour",
    ),
    "rain": (
        "Past-only mean hourly liquid precipitation for the target month/hour.",
        "mm/hour",
    ),
    "snowfall": (
        "Past-only mean hourly snowfall for the target month/hour.",
        "cm/hour",
    ),
    "wind_speed_10m": (
        "Past-only mean wind speed at 10 m for the target month/hour.",
        "m/s",
    ),
    "cloud_cover": ("Past-only mean cloud cover for the target month/hour.", "%"),
    "pressure_msl": (
        "Past-only mean sea-level pressure for the target month/hour.",
        "hPa",
    ),
}


def json_write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, default=str), encoding="utf-8")


def clock_valid(index):
    """Mask nonexistent spring and combined autumn clock hours explicitly."""
    return (
        ~pd.DatetimeIndex(index)
        .tz_localize("America/New_York", ambiguous="NaT", nonexistent="NaT")
        .isna()
    )


def holiday_features(index):
    """US federal actual/observed dates; predefined Christmas-New Year period Dec24-Jan2."""
    dates = pd.DatetimeIndex(index).normalize()
    low = dates.min() - pd.Timedelta(days=400)
    high = dates.max() + pd.Timedelta(days=400)
    calendar = USFederalHolidayCalendar()
    observed = calendar.holidays(low, high, return_name=True)
    parts = []
    for rule in calendar.rules:
        actual = copy.copy(rule)
        actual.observance = None
        parts.append(actual.dates(low, high, return_name=True))
    actual = pd.concat(parts).sort_index()
    actual = actual[~actual.index.duplicated()]
    observed = observed[~observed.index.duplicated()]
    union = actual.index.union(observed.index).sort_values()
    ticks = union.asi8
    nxt = np.searchsorted(ticks, dates.asi8, side="left")
    prev = np.searchsorted(ticks, dates.asi8, side="right") - 1
    names = (
        pd.Series(dates)
        .map(actual)
        .astype("string")
        .fillna(pd.Series(dates).map(observed).astype("string"))
        .fillna("none")
    )
    return pd.DataFrame(
        dict(
            is_holiday=dates.isin(union).astype(int),
            holiday_name=names.to_numpy(),
            is_observed_holiday=(
                dates.isin(observed.index) & ~dates.isin(actual.index)
            ).astype(int),
            days_to_holiday=(ticks[nxt] - dates.asi8) / 86400e9,
            days_since_holiday=(dates.asi8 - ticks[prev]) / 86400e9,
            is_year_end_period=(
                ((dates.month == 12) & (dates.day >= 24))
                | ((dates.month == 1) & (dates.day <= 2))
            ).astype(int),
        )
    )


def feature_dictionary():
    """Return definitions, units, encodings and information availability for all predictors."""
    assert set(FEATURE_DEFINITIONS) == set(FEATURES)
    return pd.DataFrame(
        [
            dict(
                feature=c,
                group=g,
                definition=FEATURE_DEFINITIONS[c][0],
                unit=FEATURE_DEFINITIONS[c][1],
                encoding="one-hot" if c in CAT else "numeric",
                availability=(
                    "past-only climatology at origin"
                    if g == "weather"
                    else (
                        "strictly pre-origin demand"
                        if g.startswith("demand")
                        else "known at origin"
                    )
                ),
            )
            for g, cols in GROUPS.items()
            for c in cols
        ]
    )


def load_static(cfg):
    """Consolidate duplicate zone polygons, then calculate spatial predictors.

    Area is calculated in a projected CRS; representative points lie inside polygons.
    Boroughs come from the shapefile rather than being inferred from zone ID numbers.
    """
    import geopandas as gpd

    files = list(Path(cfg["ZONE_DIR"]).glob("*.shp"))
    assert len(files) == 1
    zones = gpd.read_file(files[0])
    assert zones.groupby("LocationID").borough.nunique().le(1).all()
    zones = zones[["LocationID", "borough", "geometry"]].dissolve(
        by="LocationID", as_index=False, aggfunc="first"
    )
    projected = zones.to_crs(2263)
    points = projected.geometry.representative_point().to_crs(4326)
    info = pd.DataFrame(
        dict(
            zone_id=zones.LocationID.astype(int),
            borough=zones.borough,
            zone_latitude=points.y,
            zone_longitude=points.x,
            zone_area_km2=projected.geometry.area * 0.3048006096012192**2 / 1e6,
        )
    )
    info["is_airport_zone"] = info.zone_id.isin([1, 132, 138]).astype(
        int
    )  # EWR, JFK, LGA
    info["zone_unmapped"] = 0
    return info.set_index("zone_id"), zones


def read_month(folder, year, month, db, allow_partial=False):
    """Audit existing aggregates before interpreting sparse absent zone keys as zero."""
    folder = Path(folder)
    files = sorted(folder.glob("*.parquet"))
    assert (
        files and (folder / "_SUCCESS").exists()
    ), f"Missing/incomplete pickup aggregate: {folder}"
    preparation_marker = folder / "_preparation_validation.json"
    if preparation_marker.exists():
        # A fresh consolidated run records its own monthly reconciliation evidence.
        record = json.loads(preparation_marker.read_text(encoding="utf-8"))
        assert record["passed"] and (
            record["family"],
            record["year"],
            record["month"],
        ) == ("pickup", year, month)
        assert record["cleaned_rows"] == record["aggregate_trips"]
    elif year in (2021, 2022, 2023):
        c = json.loads(
            (folder / "_aggregation_contract.json").read_text(encoding="utf-8")
        )
        assert (c["version"], c["family"], c["year"], c["month"]) == (
            "earlier-years-hourly-v2",
            "pickup",
            year,
            month,
        )
    db.read_parquet([str(f) for f in files]).create_view("source", replace=True)
    bad = db.execute(
        f"""SELECT count(*) FROM source WHERE PULocationID IS NULL OR date IS NULL
 OR hour IS NULL OR hour NOT BETWEEN 0 AND 23 OR trip_count IS NULL OR trip_count<=0
 OR year(date)!={year} OR month(date)!={month}"""
    ).fetchone()[0]
    duplicate = db.execute(
        "SELECT count(*) FROM (SELECT 1 FROM source GROUP BY PULocationID,date,hour HAVING count(*)>1)"
    ).fetchone()[0]
    assert bad == duplicate == 0, f"Invalid values/duplicate keys: {folder.name}"
    data = db.execute(
        "SELECT PULocationID AS zone_id,date,hour,trip_count AS pickups FROM source"
    ).df()
    data["timestamp"] = pd.to_datetime(data.date) + pd.to_timedelta(data.hour, unit="h")
    if not allow_partial:
        start = pd.Timestamp(year=year, month=month, day=1)
        expected = pd.date_range(
            start, start + pd.offsets.MonthBegin(1), freq="h", inclusive="left"
        )
        assert (
            expected[clock_valid(expected)].isin(data.timestamp.unique()).all()
        ), f"Missing citywide hours: {folder.name}"
    return data[["zone_id", "timestamp", "pickups"]], files


class ForecastData:
    """Training panel and past-only features. January 2026 targets are never read here."""

    def __init__(self, cfg):
        import duckdb

        self.cfg = cfg
        self.static, self.zones = load_static(cfg)
        # Read monthly aggregates sequentially to bound memory; do not load raw trips.
        db = duckdb.connect()
        db.execute("SET threads=1")
        db.execute("SET memory_limit='256MB'")
        # Include one empty origin row at TRAIN_END so shifted summaries exist for Jan 1.
        index = pd.date_range(
            cfg["TRAIN_START"], cfg["TRAIN_END"], freq="h", inclusive="both"
        )
        panel = pd.DataFrame(0, index=index, columns=self.static.index, dtype="float32")
        manifest = []
        for year in range(2021, 2026):
            for month in range(1, 13):
                folder = (
                    Path(cfg["DATA_DIR"])
                    / f"fhvhv_by_zone_hour_{year}_{month:02d}.parquet"
                )
                data, files = read_month(folder, year, month, db)
                wide = data.pivot(
                    index="timestamp", columns="zone_id", values="pickups"
                )
                for zone in wide.columns.difference(panel.columns):
                    panel[int(zone)] = np.float32(0)
                panel.loc[wide.index, wide.columns] = wide.fillna(0).astype("float32")
                manifest.append(
                    dict(
                        year=year,
                        month=month,
                        path=str(folder),
                        parts=len(files),
                        rows=len(data),
                        source_parts=[
                            dict(
                                name=f.name,
                                size=f.stat().st_size,
                                mtime_ns=f.stat().st_mtime_ns,
                            )
                            for f in files
                        ],
                    )
                )
        db.close()
        panel = panel.sort_index(axis=1).astype("float32")
        panel.loc[~clock_valid(index), :] = np.nan
        panel.loc[pd.Timestamp(cfg["TRAIN_END"]), :] = np.nan
        # Freeze zone eligibility using observations BEFORE the first validation week.
        eligible = panel.loc[panel.index < pd.Timestamp(cfg["FOLDS"][0])].sum().gt(0)
        excluded = panel.columns[~eligible].tolist()
        self.panel = panel.loc[:, eligible]
        self.zone_ids = self.panel.columns.to_numpy(dtype=int)
        self.index = self.panel.index
        self.values = self.panel.to_numpy(dtype="float32")
        self.static = self.static.reindex(self.zone_ids)
        unknown = self.static.borough.isna()
        self.static.loc[unknown, "borough"] = "Unknown"
        self.static.loc[unknown, "is_airport_zone"] = (
            self.static.index[unknown].isin([1, 132, 138]).astype(int)
        )
        self.static["zone_unmapped"] = unknown.astype(int)
        # Shift by one hour first: every origin summary excludes that origin's target.
        prior = self.panel.shift(1)
        self.mean7 = (
            prior.rolling(168, min_periods=144).mean().to_numpy(dtype="float32")
        )
        self.mean28 = (
            prior.rolling(672, min_periods=600).mean().to_numpy(dtype="float32")
        )
        self.std28 = (
            prior.rolling(672, min_periods=600).std(ddof=0).to_numpy(dtype="float32")
        )
        previous7 = (
            prior.shift(168)
            .rolling(168, min_periods=144)
            .mean()
            .to_numpy(dtype="float32")
        )
        self.trend = np.divide(
            self.mean7,
            previous7,
            out=np.full_like(self.mean7, np.nan),
            where=previous7 > 0,
        )
        self.manifest = manifest
        # Actual weather is retained for diagnostics. Prediction features use past-only cache lookups.
        self.weather = pd.read_parquet(
            Path(cfg["WEATHER_DIR"]) / "nyc_hourly_weather_local_2021_2026.parquet"
        )
        self.weather["timestamp"] = pd.to_datetime(self.weather.date) + pd.to_timedelta(
            self.weather.hour, unit="h"
        )
        assert not self.weather.duplicated(["weather_location_id", "timestamp"]).any()
        mapping = pd.read_csv(
            Path(cfg["WEATHER_DIR"]) / "taxi_zone_weather_lookup.csv"
        ).set_index("LocationID")
        self.weather_locations = (
            mapping.reindex(self.zone_ids)
            .weather_location_id.fillna("manhattan")
            .to_numpy()
        )
        self.weather_proxy = pd.Series(
            ~pd.Index(self.zone_ids).isin(mapping.index), index=self.zone_ids
        )
        self._build_weather_cache()
        root = Path(cfg["RESULTS_DIR"])
        json_write(root / "input_manifest.json", manifest)
        pd.DataFrame(
            dict(
                zone_id=self.zone_ids,
                weather_location_id=self.weather_locations,
                uses_city_weather_proxy=self.weather_proxy.to_numpy(),
                unmapped_geometry=unknown.to_numpy(),
            )
        ).to_csv(root / "zone_eligibility.csv", index=False)
        json_write(
            root / "data_audit.json",
            dict(
                training_shape=self.values.shape,
                eligible_zones=self.zone_ids.tolist(),
                excluded_zero_activity_zones=excluded,
                dst_clock_hours_excluded=int((~clock_valid(index)).sum()),
                zero_policy="Absent zone keys are zero only within audited complete citywide months; DST hours excluded.",
                weather_policy="Climatology from TRAIN_START strictly before each example origin.",
            ),
        )

    def _build_weather_cache(self):
        """Build cumulative weather sums so each example can query its own past only."""
        self.weather_cache = {}
        for location, g in self.weather.groupby("weather_location_id"):
            for month in range(13):
                for hour in range(24) if month else [-1]:
                    selected = (
                        g
                        if month == 0
                        else g[
                            (g.timestamp.dt.month == month)
                            & (g.timestamp.dt.hour == hour)
                        ]
                    )
                    selected = selected.sort_values("timestamp")
                    v = selected[WEATHER].to_numpy(float)
                    assert np.isfinite(v).all()
                    self.weather_cache[(location, month, hour)] = (
                        selected.timestamp.to_numpy("datetime64[ns]"),
                        np.vstack([np.zeros(len(WEATHER)), np.cumsum(v, axis=0)]),
                    )

    def positions(self, times):
        return self.index.get_indexer(pd.DatetimeIndex(times))

    def values_at(self, times, zone_indices):
        position = self.positions(times)
        result = np.full(len(position), np.nan)
        valid = position >= 0
        result[valid] = self.values[position[valid], np.asarray(zone_indices)[valid]]
        return result

    def climatology(self, locations, targets, origins):
        """Prefix sums exclude all weather at/after each row's own forecast origin."""
        result = np.full((len(targets), len(WEATHER)), np.nan)
        q = pd.DataFrame(
            dict(location=locations, month=targets.month, hour=targets.hour)
        )
        issue = origins.to_numpy("datetime64[ns]")
        start = np.datetime64(self.cfg["TRAIN_START"])
        for (location, month, hour), indices in q.groupby(
            ["location", "month", "hour"]
        ).groups.items():
            rows = np.asarray(indices)
            dates, sums = self.weather_cache[(location, int(month), int(hour))]
            lo = np.searchsorted(dates, start, side="left")
            counts = np.searchsorted(dates, issue[rows], side="left")
            n = counts - lo
            good = n > 0
            result[rows[good]] = (sums[counts[good]] - sums[lo]) / n[good, None]
            if (~good).any():
                dates, sums = self.weather_cache[(location, 0, -1)]
                lo = np.searchsorted(dates, start, side="left")
                r = rows[~good]
                counts = np.searchsorted(dates, issue[r], side="left")
                n = counts - lo
                assert (n > 0).all(), "No pre-origin weather history"
                result[r] = (sums[counts] - sums[lo]) / n[:, None]
        return result

    def features(self, origins, zone_indices, horizons):
        """One direct target per row. All demand inputs precede the row's origin."""
        origins = pd.DatetimeIndex(origins)
        zone_indices = np.asarray(zone_indices, dtype=int)
        horizons = np.asarray(horizons, dtype=int)
        assert ((horizons >= 1) & (horizons <= 168)).all()
        targets = origins + pd.to_timedelta(horizons - 1, unit="h")
        # Even the last target's one-week lag must precede the forecast origin.
        assert ((targets - pd.Timedelta(hours=168)) < origins).all()
        origin_pos = self.positions(origins)
        assert (origin_pos >= 0).all()
        # Calendar values are known in advance for every target hour.
        x = pd.DataFrame(
            dict(
                forecast_horizon=horizons,
                hour=targets.hour,
                day_of_week=targets.dayofweek,
                month=targets.month,
                hour_of_week=targets.dayofweek * 24 + targets.hour,
                is_weekend=(targets.dayofweek >= 5).astype(int),
                hour_sin=np.sin(2 * np.pi * targets.hour / 24),
                hour_cos=np.cos(2 * np.pi * targets.hour / 24),
                annual_sin=np.sin(
                    2
                    * np.pi
                    * (targets.dayofyear - 1)
                    / np.where(targets.is_leap_year, 366, 365)
                ),
                annual_cos=np.cos(
                    2
                    * np.pi
                    * (targets.dayofyear - 1)
                    / np.where(targets.is_leap_year, 366, 365)
                ),
            )
        )
        x = pd.concat([x, holiday_features(targets)], axis=1)
        # Use target-aligned WEEKLY lags; short lags would require unknown within-week demand.
        for lag in (168, 336, 504):
            x[f"pickup_lag_{lag}h"] = self.values_at(
                targets - pd.Timedelta(hours=lag), zone_indices
            )
        lag4 = np.column_stack(
            [
                self.values_at(targets - pd.Timedelta(hours=lag), zone_indices)
                for lag in (168, 336, 504, 672)
            ]
        )
        x["same_hour_week_mean_4w"] = np.mean(
            lag4, axis=1
        )  # DST missingness remains explicit.
        # Origin summaries are fixed across the week, unlike target-aligned weekly lags.
        for name, array in [
            ("recent_mean_7d", self.mean7),
            ("recent_mean_28d", self.mean28),
            ("recent_std_28d", self.std28),
            ("recent_trend_ratio", self.trend),
        ]:
            x[name] = array[origin_pos, zone_indices]
        static = self.static.iloc[zone_indices].reset_index()
        for name in ["zone_id"] + GROUPS["spatial"] + ["borough"]:
            x[name] = static[name].to_numpy()
        w = self.climatology(self.weather_locations[zone_indices], targets, origins)
        for i, name in enumerate(WEATHER):
            x[name] = w[:, i]
        # Store categories as strings so zone IDs/hours are never treated as ordered numbers.
        for name in CAT:
            x[name] = x[name].astype(str)
        meta = pd.DataFrame(
            dict(
                zone_id=self.zone_ids[zone_indices],
                origin=origins,
                target_datetime=targets,
                forecast_horizon=horizons,
                forecast_day=(horizons - 1) // 24 + 1,
            )
        )
        return x[FEATURES], meta

    def training_examples(self, cutoff):
        """Reproducible bounded sample covering all years; same examples for all ML candidates.
        Sampled zone/day-origin/horizon triples avoid materializing every overlapping week.
        All labels, including hour 168, must be strictly before the fold cutoff.
        """
        cutoff = pd.Timestamp(cutoff)
        rng = np.random.default_rng(self.cfg["SEED"])
        origins = pd.date_range(
            pd.Timestamp(self.cfg["TRAIN_START"]) + pd.Timedelta(days=28),
            cutoff - pd.Timedelta(days=7),
            freq="D",
        )
        assert len(origins) > 0
        n = self.cfg["MAX_TRAIN_EXAMPLES"]
        triples = pd.DataFrame(
            dict(
                o=rng.integers(len(origins), size=n),
                z=rng.integers(len(self.zone_ids), size=n),
                h=rng.integers(1, 169, size=n),
            )
        ).drop_duplicates()
        x, meta = self.features(
            origins.take(triples.o), triples.z.to_numpy(), triples.h.to_numpy()
        )
        y = self.values_at(meta.target_datetime, triples.z.to_numpy())
        keep = np.isfinite(y) & clock_valid(meta.target_datetime)
        assert (meta.target_datetime < cutoff).all()
        x = x.loc[keep].reset_index(drop=True)
        meta = meta.loc[keep].reset_index(drop=True)
        y = y[keep]
        assert len(y) > 100
        return x, y, meta

    def forecast_examples(self, origin):
        issues = pd.DatetimeIndex([pd.Timestamp(origin)] * (len(self.zone_ids) * 168))
        return self.features(
            issues,
            np.repeat(np.arange(len(self.zone_ids)), 168),
            np.tile(np.arange(1, 169), len(self.zone_ids)),
        )

    def scales(self, cutoff):
        train = self.panel[self.panel.index < pd.Timestamp(cutoff)]
        scale = (train - train.shift(168)).abs().mean()
        return scale.where(scale > 0)

    def observations(self, meta):
        return self.values_at(
            meta.target_datetime, pd.Index(self.zone_ids).get_indexer(meta.zone_id)
        )


def columns_without(drop_groups):
    assert set(drop_groups) <= set(GROUPS)
    return [c for g, cols in GROUPS.items() if g not in drop_groups for c in cols]


def build_model(name, params, columns, seed=42):
    """Construct an UNFITTED pipeline; .fit() occurs only inside an enabled training stage.

    Numerical imputation/scaling and one-hot categories are learned from training rows.
    The returned object bundles preprocessing and prediction for reproducible reuse.
    """
    cats = [c for c in CAT if c in columns]
    numeric = [c for c in columns if c not in cats]
    preprocess = ColumnTransformer(
        [
            (
                "num",
                Pipeline(
                    [
                        (
                            "impute",
                            SimpleImputer(strategy="median", add_indicator=True),
                        ),
                        ("scale", StandardScaler()),
                    ]
                ),
                numeric,
            ),
            (
                "cat",
                OneHotEncoder(
                    handle_unknown="ignore", sparse_output=False, dtype=np.float32
                ),
                cats,
            ),
        ],
        sparse_threshold=0,
    )
    if name == "RandomForest":
        settings = dict(
            n_estimators=100,
            max_depth=16,
            min_samples_leaf=5,
            max_features=0.8,
            n_jobs=2,
            random_state=seed,
        )
        settings.update(params)
        estimator = RandomForestRegressor(**settings)
    elif name == "XGBoost":
        try:
            from xgboost import XGBRegressor
        except ImportError as exc:
            raise ImportError(
                "Install xgboost in this kernel; no agreed model is silently omitted."
            ) from exc
        settings = dict(
            objective="reg:squarederror",
            tree_method="hist",
            n_estimators=250,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            n_jobs=2,
            random_state=seed,
        )
        settings.update(params)
        estimator = XGBRegressor(**settings)
    elif name == "NeuralNetwork":
        # A feed-forward neural network. Target scaling and numerical feature scaling aid training.
        # Random internal early-stopping validation is disabled; outer folds are chronological.
        settings = dict(
            hidden_layer_sizes=(64, 32),
            activation="relu",
            solver="adam",
            batch_size=512,
            max_iter=60,
            early_stopping=False,
            shuffle=True,
            random_state=seed,
        )
        settings.update(params)
        estimator = TransformedTargetRegressor(
            regressor=MLPRegressor(**settings), transformer=StandardScaler()
        )
    else:
        raise ValueError(name)
    return Pipeline([("preprocess", preprocess), ("model", estimator)])


def package_versions():
    result = {}
    for package in [
        "numpy",
        "pandas",
        "duckdb",
        "scikit-learn",
        "statsmodels",
        "xgboost",
        "shap",
        "geopandas",
    ]:
        try:
            result[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            result[package] = "NOT INSTALLED"
    return result


def add_losses(frame, scale):
    f = frame.copy()
    f["mase_scale"] = f.zone_id.map(scale)
    f["error"] = f.prediction - f.actual
    f["absolute_error"] = f.error.abs()
    f["squared_error"] = f.error**2
    f["scaled_absolute_error"] = f.absolute_error / f.mase_scale
    return f


def metrics(frame, groups):
    """MASE is the mean zone-hour scaled error; zero training scales are undefined, not zero."""
    rows = []
    for keys, g in frame.groupby(groups, dropna=False, sort=False, observed=True):
        if not isinstance(keys, tuple):
            keys = (keys,)
        valid = g.actual.notna() & g.prediction.notna()
        v = g.loc[valid]
        row = dict(zip(groups, keys))
        row.update(
            MAE=v.absolute_error.mean(),
            RMSE=np.sqrt(v.squared_error.mean()),
            MASE=v.scaled_absolute_error.mean(),
            bias=v.error.mean(),
            n_scored=len(v),
            n_missing_target=int(g.actual.isna().sum()),
            n_missing_prediction=int(g.prediction.isna().sum()),
            n_undefined_mase=int(v.scaled_absolute_error.isna().sum()),
        )
        rows.append(row)
    return pd.DataFrame(rows)


def arima_forecast(data, origin, order):
    """Demand-only ARIMA per zone, full pre-origin history. Never substitutes a different model on error.
    This explicit nonseasonal baseline is compared with weekly-naive to expose missed seasonality.
    """
    forecast = np.empty((len(data.zone_ids), 168))
    logs = []
    train = data.panel[data.panel.index < pd.Timestamp(origin)]
    for i, zone in enumerate(data.zone_ids):
        y = train[zone].to_numpy(float)
        if np.nanmax(y) == np.nanmin(y):
            forecast[i] = max(0, float(np.nanmean(y)))
            logs.append(
                dict(zone_id=int(zone), status="constant_series", order=list(order))
            )
            continue
        try:
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                fitted = ARIMA(
                    y,
                    order=tuple(order),
                    trend="n" if order[1] > 0 else "c",
                    missing="none",
                ).fit(method_kwargs={"maxiter": 200})
            if not fitted.mle_retvals.get("converged", True):
                raise RuntimeError("ARIMA optimizer did not converge")
            values = np.asarray(fitted.forecast(168), float)
            assert np.isfinite(values).all()
            forecast[i] = np.maximum(0, values)
            logs.append(
                dict(
                    zone_id=int(zone),
                    status="ok",
                    order=list(order),
                    warnings=[str(w.message) for w in caught],
                )
            )
        except Exception as exc:
            logs.append(
                dict(
                    zone_id=int(zone),
                    status="failed",
                    order=list(order),
                    error=str(exc),
                )
            )
            json_write(
                Path(data.cfg["RESULTS_DIR"]) / "arima_failure.json",
                dict(origin=origin, records=logs),
            )
            raise RuntimeError(
                f"ARIMA failed for zone {zone}; see arima_failure.json. No substitution made."
            ) from exc
    return forecast.ravel(), logs


def prediction_frame(data, meta, prediction, model, candidate, phase, actual=None):
    assert len(prediction) == len(meta) and np.isfinite(prediction).all()
    f = meta.copy()
    f["prediction"] = np.maximum(0, np.asarray(prediction, float))
    f["actual"] = (
        data.observations(meta) if actual is None else np.asarray(actual, float)
    )
    f["model"] = model
    f["candidate"] = candidate
    f["phase"] = phase
    return add_losses(f, data.scales(meta.origin.iloc[0]))


def run_cv(data, candidates, drop_groups=(), tag="full"):
    """Sequential fits with the same examples, zones and hours. Save forecasts and fit warnings."""
    root = Path(data.cfg["RESULTS_DIR"])
    columns = columns_without(drop_groups)
    predictions = []
    fit_log = []
    signature = dict(
        candidates=candidates,
        drop_groups=list(drop_groups),
        manifest_sha256=hashlib.sha256(
            (root / "input_manifest.json").read_bytes()
        ).hexdigest(),
        helper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    )
    receipt = root / f"{tag}_cv_signature.json"
    if receipt.exists():
        assert (
            json.loads(receipt.read_text()) == signature
        ), "CV inputs/code changed: choose a new run name."
    for fold, origin in enumerate(data.cfg["FOLDS"], 1):
        print(f"{tag}: fold {fold}/4, issue {origin}", flush=True)
        x, y, train_meta = data.training_examples(origin)
        future, meta = data.forecast_examples(origin)
        if tag == "full":
            zi = np.repeat(np.arange(len(data.zone_ids)), 168)
            naive = data.values_at(meta.target_datetime - pd.Timedelta(hours=168), zi)
            assert np.isfinite(
                naive
            ).all(), "Weekly-naive inputs unavailable: review common scoring mask"
            p = prediction_frame(
                data, meta, naive, "WeeklyNaive", "weekly_naive", "validation"
            )
            p["fold"] = fold
            p["feature_set"] = tag
            predictions.append(p)
        for candidate in candidates:
            started = time.perf_counter()
            name = candidate["model"]
            identifier = candidate["id"]
            if name == "ARIMA":
                predicted, logs = arima_forecast(
                    data, origin, candidate["params"]["order"]
                )
                json_write(root / f"{tag}_{identifier}_fold{fold}_arima_log.json", logs)
                rows = int((data.panel.index < pd.Timestamp(origin)).sum()) * len(
                    data.zone_ids
                )
                warn = []
            else:
                model = build_model(
                    name, candidate["params"], columns, data.cfg["SEED"]
                )
                with warnings.catch_warnings(record=True) as records:
                    warnings.simplefilter("always")
                    model.fit(x[columns], y)
                warn = [str(w.message) for w in records]
                predicted = model.predict(future[columns])
                rows = len(y)
                del model
            p = prediction_frame(data, meta, predicted, name, identifier, "validation")
            p["fold"] = fold
            p["feature_set"] = tag
            p.to_parquet(
                root / f"{tag}_{identifier}_fold{fold}_forecasts.parquet", index=False
            )
            predictions.append(p)
            fit_log.append(
                dict(
                    feature_set=tag,
                    fold=fold,
                    origin=origin,
                    candidate=identifier,
                    model=name,
                    training_examples=rows,
                    seconds=time.perf_counter() - started,
                    warnings=warn,
                )
            )
            json_write(root / f"{tag}_fit_log.json", fit_log)
        train_meta.assign(target_year=train_meta.target_datetime.dt.year).groupby(
            "target_year"
        ).size().to_csv(root / f"{tag}_fold{fold}_training_year_counts.csv")
        del x, y, future
    all_predictions = pd.concat(predictions, ignore_index=True)
    all_predictions.to_parquet(root / f"{tag}_cv_forecasts.parquet", index=False)
    scores = metrics(all_predictions, ["feature_set", "candidate", "model", "fold"])
    scores.to_csv(root / f"{tag}_cv_metrics.csv", index=False)
    json_write(receipt, signature)
    return all_predictions, scores


def select_candidates(scores):
    """Choose one configuration per family using equal-weight mean validation MAE."""
    summary = scores.groupby(["candidate", "model"], as_index=False)[
        ["MAE", "RMSE", "MASE", "bias"]
    ].mean()
    assert np.isfinite(summary[["MAE", "RMSE"]]).all().all()
    best = (
        summary.sort_values(["MAE", "candidate"])
        .groupby("model", as_index=False)
        .first()
    )
    return summary, best


def shap_fold(data, candidate, origin, fold, drop_groups=()):
    """Explain held-out rows using training-only background; regroup dummy columns."""
    import shap

    columns = columns_without(drop_groups)
    x, y, _ = data.training_examples(origin)
    future, meta = data.forecast_examples(origin)
    model = build_model(
        candidate["model"], candidate["params"], columns, data.cfg["SEED"]
    )
    model.fit(x[columns], y)
    rng = np.random.default_rng(data.cfg["SEED"] + fold)
    chosen = rng.choice(
        len(future), min(data.cfg["SHAP_ROWS"], len(future)), replace=False
    )
    background = rng.choice(
        len(x), min(data.cfg["SHAP_BACKGROUND"], len(x)), replace=False
    )
    prep = model.named_steps["preprocess"]
    terminal = model.named_steps["model"]
    explain_x = prep.transform(future.iloc[chosen][columns])
    background_x = prep.transform(x.iloc[background][columns])
    names = prep.get_feature_names_out()
    if candidate["model"] in ("RandomForest", "XGBoost"):
        explainer = shap.TreeExplainer(
            terminal,
            data=background_x,
            feature_perturbation="interventional",
            model_output="raw",
        )
        explanation = explainer(explain_x, check_additivity=True)
    else:
        # Permutation SHAP explains the NN in original pickup units, including target inverse scaling.
        explainer = shap.Explainer(
            terminal.predict,
            shap.maskers.Independent(background_x),
            algorithm="permutation",
            feature_names=names,
            seed=data.cfg["SEED"],
        )
        explanation = explainer(explain_x, max_evals=2 * len(names) + 1)
    values = np.asarray(explanation.values)
    assert values.shape == explain_x.shape
    grouped = {name: np.zeros(len(chosen)) for name in columns}
    for i, encoded in enumerate(names):
        name = encoded.split("__", 1)[1]
        if name.startswith("missingindicator_"):
            name = name[len("missingindicator_") :]
        matches = [
            c for c in columns if name == c or (c in CAT and name.startswith(c + "_"))
        ]
        assert matches, f"Unmapped encoded feature: {encoded}"
        grouped[max(matches, key=len)] += values[:, i]
    contributions = pd.DataFrame(grouped)
    out = pd.concat(
        [meta.iloc[chosen].reset_index(drop=True), contributions.add_prefix("shap__")],
        axis=1,
    )
    out["fold"] = fold
    reconstructed = np.asarray(explanation.base_values).reshape(-1) + values.sum(axis=1)
    assert np.allclose(
        terminal.predict(explain_x), reconstructed, rtol=1e-3, atol=0.1
    ), "SHAP must reconstruct raw output"
    ranking = pd.DataFrame(
        dict(
            feature=columns,
            mean_abs_shap=[np.abs(grouped[c]).mean() for c in columns],
            fold=fold,
        )
    )
    ranking["group"] = ranking.feature.map(
        {c: g for g, cols in GROUPS.items() for c in cols}
    )
    root = Path(data.cfg["RESULTS_DIR"])
    out.to_parquet(root / f'shap_{candidate["id"]}_fold{fold}.parquet', index=False)
    ranking.to_csv(
        root / f'shap_{candidate["id"]}_fold{fold}_importance.csv', index=False
    )
    # Feature values accompany contributions for dependence plots.
    values_frame = future.iloc[chosen][columns].reset_index(drop=True)
    values_frame["fold"] = fold
    values_frame.to_parquet(
        root / f'shap_{candidate["id"]}_fold{fold}_feature_values.parquet', index=False
    )
    return ranking, out, values_frame


def load_test_targets(data):
    """Call only after freezing. No test file -> no test scores; never fabricate labels."""
    import duckdb

    folder = Path(data.cfg["TEST_PICKUP_DIR"])
    if not list(folder.glob("*.parquet")) or not (folder / "_SUCCESS").exists():
        return (
            None,
            f"Test scoring unavailable: missing complete {folder.name}. Forecasts are saved without labels.",
        )
    db = duckdb.connect()
    db.execute("SET threads=1")
    db.execute("SET memory_limit='256MB'")
    observed, _ = read_month(folder, 2026, 1, db, allow_partial=True)
    db.close()
    times = pd.date_range(data.cfg["TEST_ORIGIN"], periods=168, freq="h")
    selected = observed[observed.timestamp.isin(times)]
    assert times.isin(
        selected.timestamp.unique()
    ).all(), "Test week has missing citywide hours"
    unknown = (
        selected.loc[~selected.zone_id.isin(data.zone_ids), "zone_id"].unique().tolist()
    )
    if unknown:
        json_write(
            Path(data.cfg["RESULTS_DIR"]) / "test_unseen_zones.json",
            dict(unseen_zone_ids=unknown),
        )
        warnings.warn(
            "Test zones outside the training-defined universe are reported separately."
        )
    wide = (
        selected.pivot(index="timestamp", columns="zone_id", values="pickups")
        .reindex(index=times, columns=data.zone_ids)
        .fillna(0)
    )
    return (
        wide.to_numpy(float).T.ravel(),
        "Test coverage complete for frozen eligible zones.",
    )


def fit_final(data, selected, drop_groups):
    import joblib

    root = Path(data.cfg["RESULTS_DIR"])
    origin = data.cfg["TEST_ORIGIN"]
    assert (root / "frozen_experiment.json").exists()
    x, y, _ = data.training_examples(origin)
    future, meta = data.forecast_examples(origin)
    forecasts = []
    zi = np.repeat(np.arange(len(data.zone_ids)), 168)
    naive = data.values_at(meta.target_datetime - pd.Timedelta(hours=168), zi)
    forecasts.append(
        prediction_frame(
            data,
            meta,
            naive,
            "WeeklyNaive",
            "weekly_naive",
            "test",
            actual=np.full(len(meta), np.nan),
        )
    )
    for candidate in selected:
        if candidate["model"] == "ARIMA":
            pred, logs = arima_forecast(data, origin, candidate["params"]["order"])
            json_write(root / "final_arima_log.json", logs)
        else:
            columns = columns_without(drop_groups.get(candidate["id"], []))
            model = build_model(
                candidate["model"], candidate["params"], columns, data.cfg["SEED"]
            )
            model.fit(x[columns], y)
            pred = model.predict(future[columns])
            joblib.dump(model, root / f'final_{candidate["id"]}.joblib', compress=3)
            del model
        forecasts.append(
            prediction_frame(
                data,
                meta,
                pred,
                candidate["model"],
                candidate["id"],
                "test",
                actual=np.full(len(meta), np.nan),
            )
        )
    result = pd.concat(forecasts, ignore_index=True)
    result.to_parquet(root / "final_week_forecasts_unscored.parquet", index=False)
    return result


def diagnostic_labels(frame, data):
    """Observed weather labels errors retrospectively; it never enters forecast features."""
    f = frame.copy()
    t = pd.DatetimeIndex(f.target_datetime)
    f["hour"] = t.hour
    f["weekday"] = t.day_name()
    f["date"] = t.normalize()
    h = holiday_features(t)
    f["holiday"] = np.where(h.is_holiday.to_numpy() == 1, "Holiday", "Other")
    f["borough"] = f.zone_id.map(data.static.borough)
    f["airport"] = np.where(f.zone_id.isin([1, 132, 138]), "Airport", "Other")
    f["demand_band"] = pd.cut(
        f.actual,
        [-np.inf, 0, 10, 50, 200, np.inf],
        labels=["Zero", "1-10", "11-50", "51-200", "Above 200"],
    )
    f["weather_location_id"] = f.zone_id.map(
        dict(zip(data.zone_ids, data.weather_locations))
    )
    w = data.weather[
        [
            "weather_location_id",
            "timestamp",
            "precipitation",
            "snowfall",
            "temperature_2m",
        ]
    ]
    f = f.merge(
        w,
        left_on=["weather_location_id", "target_datetime"],
        right_on=["weather_location_id", "timestamp"],
        how="left",
        validate="many_to_one",
    )
    f["weather_condition"] = np.select(
        [f.snowfall.gt(0), f.precipitation.gt(0), f.precipitation.notna()],
        ["Snow", "Rain", "Dry"],
        default="Missing weather",
    )
    f["temperature_band"] = pd.cut(
        f.temperature_2m,
        [-np.inf, 0, 10, 20, 30, np.inf],
        labels=["Below 0C", "0-10C", "10-20C", "20-30C", "Above 30C"],
    )
    return f


# Plot builders return figures instead of saving files themselves. The notebook's
# finish() function controls output paths, filenames and display consistently.
def plot_horizon_errors(by_day):
    """Compare all four metrics as the forecast advances from day 1 to day 7."""
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 2, figsize=(14, 8))
    for ax, metric in zip(axes.flat, ["MAE", "RMSE", "MASE", "bias"]):
        for model, group in by_day.groupby("model"):
            ax.plot(group.forecast_day, group[metric], marker="o", label=model)
        ax.set(
            title=f"{metric} by forecast day",
            xlabel="Forecast day",
            ylabel=metric,
            xticks=range(1, 8),
        )
        if metric == "bias":
            ax.axhline(0, color="black", linewidth=0.6)
    axes[0, 0].legend(fontsize=8)
    return fig


def plot_subgroup_errors(table, dimension, colors):
    """Show error magnitude, direction and support counts for each subgroup."""
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 3, figsize=(18, 4))
    for ax, metric in zip(axes, ["MAE", "bias", "n_scored"]):
        values = table.pivot(index=dimension, columns="model", values=metric)
        values.plot.bar(ax=ax, color=colors)
        ax.set(
            title=f"{metric} by {dimension}",
            xlabel=dimension,
            ylabel="Zone-hours" if metric == "n_scored" else "Trips/zone-hour",
        )
        if metric == "bias":
            ax.axhline(0, color="black", linewidth=0.6)
    return fig


def plot_zone_errors(zones, table, model, mae_max, bias_limit):
    """Use shared color limits across models so equal colors mean equal errors."""
    import matplotlib.pyplot as plt

    layer = zones.merge(
        table,
        left_on="LocationID",
        right_on="zone_id",
        how="left",
        validate="one_to_one",
    )
    fig, axes = plt.subplots(1, 2, figsize=(14, 7))
    style = dict(
        legend=True,
        edgecolor="#808080",
        linewidth=0.15,
        missing_kwds={"color": "lightgrey"},
    )
    layer.plot(column="MAE", ax=axes[0], cmap="Blues", vmin=0, vmax=mae_max, **style)
    layer.plot(
        column="bias",
        ax=axes[1],
        cmap="BrBG",
        vmin=-bias_limit,
        vmax=bias_limit,
        **style,
    )
    for ax, title in zip(axes, [f"{model}: MAE", f"{model}: signed bias"]):
        ax.set_title(title)
        ax.set_axis_off()
    return fig


def plot_hourly_error_heatmap(records, model):
    """Locate weekday/hour combinations with elevated mean absolute errors."""
    import matplotlib.pyplot as plt

    calendar = records.assign(
        weekday_id=records.target_datetime.dt.dayofweek,
        clock_hour=records.target_datetime.dt.hour,
    )
    heat = calendar.groupby(["weekday_id", "clock_hour"]).absolute_error.mean()
    heat = heat.unstack().reindex(index=range(7), columns=range(24))
    fig, ax = plt.subplots(figsize=(12, 4))
    image = ax.imshow(heat, aspect="auto", cmap="Blues")
    ax.set(
        yticks=range(7),
        yticklabels=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        xlabel="Local hour",
        title=f"{model}: MAE by weekday/hour",
    )
    fig.colorbar(image, ax=ax, label="MAE")
    return fig


def plot_residual_diagnostics(records, model, seed):
    """Separate poor fit, demand-dependent errors and systematic signed errors."""
    import matplotlib.pyplot as plt

    valid = records.dropna(subset=["actual", "prediction"])
    sample = valid.sample(n=min(5000, len(valid)), random_state=seed)
    fig, axes = plt.subplots(1, 3, figsize=(17, 4))
    axes[0].scatter(sample.actual, sample.prediction, s=5, alpha=0.2, color="#0072B2")
    bound = max(sample.actual.max(), sample.prediction.max())
    axes[0].plot([0, bound], [0, bound], color="#D55E00")
    axes[0].set(xlabel="Observed", ylabel="Predicted", title=f"{model}: fit")
    axes[1].scatter(sample.prediction, sample.error, s=5, alpha=0.2, color="#444444")
    axes[1].axhline(0, color="#D55E00")
    axes[1].set(xlabel="Predicted", ylabel="Residual", title="Errors vs forecast level")
    axes[2].hist(sample.error, bins=40, color="#0072B2", alpha=0.8)
    axes[2].axvline(0, color="#D55E00")
    axes[2].set(
        xlabel="Predicted minus observed",
        ylabel="Zone-hours",
        title="Residual distribution",
    )
    return fig


def plot_forecast_overlay(records, model):
    """Plot separate forecast weeks, avoiding misleading lines across omitted months."""
    import matplotlib.pyplot as plt

    city = records.groupby(["origin", "target_datetime"])[["actual", "prediction"]]
    city = city.sum(min_count=1).reset_index()
    origins = city.origin.unique()
    fig, axes = plt.subplots(
        len(origins), 1, figsize=(14, 3 * len(origins)), squeeze=False
    )
    for ax, origin in zip(axes.flat, origins):
        week = city[city.origin.eq(origin)]
        ax.plot(week.target_datetime, week.actual, color="#333333", label="Observed")
        ax.plot(
            week.target_datetime, week.prediction, color="#D55E00", label="Predicted"
        )
        ax.set(
            title=f"{model}: issued {pd.Timestamp(origin):%Y-%m-%d}",
            ylabel="City pickups/hour",
        )
        ax.legend()
    return fig
