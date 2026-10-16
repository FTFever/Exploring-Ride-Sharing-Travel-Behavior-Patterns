"""Collect immutable, cached hourly ERA5 weather and taxi-zone lookup; no demand/model changes."""
from pathlib import Path
import json, hashlib, time, shutil
from datetime import datetime, timezone
import requests
import pandas as pd
import numpy as np
import geopandas as gpd

import os
BASE = Path(os.environ.get('RIDESHARE_REFERENCE_DIR', 'data/reference'))
OUT = BASE / 'weather_hourly'
ZONE_DIR = Path(os.environ.get('RIDESHARE_ZONE_DIR', str(BASE / 'taxi_zones')))
RAW = OUT / 'raw'
API = 'https://archive-api.open-meteo.com/v1/archive'
VARIABLES = ['temperature_2m','relative_humidity_2m','dew_point_2m','apparent_temperature',
             'precipitation','rain','snowfall','cloud_cover','pressure_msl',
             'wind_speed_10m','wind_direction_10m','weather_code']
TZ = 'America/New_York'
START = pd.Timestamp('2021-01-01',tz=TZ).tz_convert('UTC')
END = pd.Timestamp('2026-01-08',tz=TZ).tz_convert('UTC')
CUTOFF = pd.Timestamp('2026-01-01',tz=TZ).tz_convert('UTC')

def put_json(path, obj):
    tmp = path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
    tmp.replace(path)

def download(year, points):
    params = dict(latitude=','.join(f'{v:.5f}' for v in points.latitude),
        longitude=','.join(f'{v:.5f}' for v in points.longitude),
        start_date=f'{year}-01-01',end_date=f'{year}-12-31' if year<2026 else '2026-01-08',
        hourly=','.join(VARIABLES),models='era5',timezone='UTC',wind_speed_unit='ms',
        temperature_unit='celsius',precipitation_unit='mm')
    file = RAW / f'era5_{year}.json'
    request_file = RAW / f'era5_{year}_request.json'
    if file.exists():
        assert json.loads(request_file.read_text(encoding='utf-8'))['params']==params, 'Cached request mismatch'
        return json.loads(file.read_text(encoding='utf-8'))
    for attempt in range(4):
        try:
            r = requests.get(API,params=params,timeout=(20,180))
            if r.status_code in (429,500,502,503,504):
                raise RuntimeError(f'Transient HTTP {r.status_code}: {r.text[:200]}')
            r.raise_for_status()
            data=r.json()
            if isinstance(data,dict) and data.get('error'):
                raise RuntimeError(data.get('reason','API error'))
            assert isinstance(data,list) and len(data)==len(points), 'Expected multi-location response'
            put_json(request_file,dict(endpoint=API,params=params,url=r.url,retrieved_utc=datetime.now(timezone.utc).isoformat()))
            put_json(file,data)
            print(f'Downloaded {year}: {len(data)} reference locations',flush=True)
            time.sleep(2)
            return data
        except Exception:
            if attempt==3:raise
            time.sleep(5*(attempt+1))

def main():
    RAW.mkdir(parents=True,exist_ok=True)
    shapes=list(ZONE_DIR.glob('*.shp'));assert len(shapes)==1
    zones=gpd.read_file(shapes[0])
    assert zones.borough.notna().all()
    assert zones.groupby('LocationID').borough.nunique().eq(1).all()
    boroughs=zones.dissolve(by='borough').to_crs(2263)
    coords=boroughs.geometry.representative_point().to_crs(4326)
    points=pd.DataFrame([dict(weather_location_id=name.lower().replace(' ','_'),borough=name,
        latitude=round(p.y,5),longitude=round(p.x,5)) for name,p in coords.items()]).sort_values('borough').reset_index(drop=True)
    points.to_csv(OUT/'weather_reference_locations.csv',index=False)
    lookup=zones[['LocationID','borough']].drop_duplicates().merge(points[['borough','weather_location_id']],on='borough',validate='many_to_one')
    assert lookup.LocationID.is_unique
    lookup.to_csv(OUT/'taxi_zone_weather_lookup.csv',index=False)
    chunks, grids, units = [], [], None
    for year in range(2021,2027):
        response=download(year,points)
        for i,item in enumerate(response):
            assert item['utc_offset_seconds']==0
            assert set(VARIABLES).issubset(item['hourly'])
            if units is None:units=item['hourly_units']
            else:assert units==item['hourly_units']
            f=pd.DataFrame(item['hourly']).rename(columns={'time':'timestamp_utc'})
            f['timestamp_utc']=pd.to_datetime(f.timestamp_utc,utc=True)
            f=f[(f.timestamp_utc>=START)&(f.timestamp_utc<END)].copy()
            f['weather_location_id']=points.iloc[i].weather_location_id
            chunks.append(f)
            grids.append(dict(year=year,weather_location_id=points.iloc[i].weather_location_id,
                requested_latitude=float(points.iloc[i].latitude),requested_longitude=float(points.iloc[i].longitude),
                returned_grid_latitude=item['latitude'],returned_grid_longitude=item['longitude'],elevation=item.get('elevation')))
    weather=pd.concat(chunks,ignore_index=True).sort_values(['weather_location_id','timestamp_utc']).reset_index(drop=True)
    assert not weather.duplicated(['weather_location_id','timestamp_utc']).any()
    expected=pd.date_range(START,END-pd.Timedelta(hours=1),freq='h')
    for name,g in weather.groupby('weather_location_id'):
        assert pd.DatetimeIndex(g.timestamp_utc).equals(expected),f'UTC coverage: {name}'
    local=weather.timestamp_utc.dt.tz_convert(TZ)
    weather['timestamp_local']=local.dt.strftime('%Y-%m-%d %H:%M:%S%z')
    weather['date']=local.dt.strftime('%Y-%m-%d')
    weather['hour']=local.dt.hour
    weather['utc_offset_minutes']=local.map(lambda x:int(x.utcoffset().total_seconds()/60))
    weather['is_test_week']=weather.timestamp_utc>=CUTOFF
    weather['data_kind']='retrospective_reanalysis'
    for col in VARIABLES:assert weather[col].notna().all(),f'Missing {col}'
    assert weather.relative_humidity_2m.between(0,100).all()
    assert weather.cloud_cover.between(0,100).all()
    assert weather.wind_direction_10m.between(0,360).all()
    assert weather[['precipitation','rain','snowfall','wind_speed_10m']].ge(0).all().all()
    # Repeated autumn local hours are averaged for weather, not summed like trip counts.
    # Missing spring hours remain absent. Preserve count so folds can be identified.
    keys=['weather_location_id','date','hour']
    table=weather.groupby(keys,as_index=False)[VARIABLES].mean()
    # Wind bearings wrap at 360 degrees: use a circular, not arithmetic, mean.
    bearings=weather[keys].copy()
    bearings['wind_sin']=np.sin(np.deg2rad(weather.wind_direction_10m))
    bearings['wind_cos']=np.cos(np.deg2rad(weather.wind_direction_10m))
    circular=bearings.groupby(keys,as_index=False)[['wind_sin','wind_cos']].mean()
    circular['wind_direction_10m']=(np.rad2deg(np.arctan2(circular.wind_sin,circular.wind_cos))+360)%360
    table=table.drop(columns='wind_direction_10m').merge(circular[keys+['wind_direction_10m']],on=keys,validate='one_to_one')
    count=weather.groupby(keys).size().rename('utc_hours_in_local_hour').reset_index()
    table=table.merge(count,on=keys,validate='one_to_one')
    table['is_dst_repeated_hour']=table.utc_hours_in_local_hour.eq(2)
    table['is_test_week']=table.date.ge('2026-01-01')
    table['data_kind']='retrospective_reanalysis'
    for label,frame in [('nyc_hourly_weather_utc_2021_2026',weather),('nyc_hourly_weather_local_2021_2026',table)]:
        frame.to_parquet(OUT/f'{label}.parquet',index=False)
        frame.to_csv(OUT/f'{label}.csv',index=False)
    pd.DataFrame(grids).to_csv(OUT/'source_grid_locations.csv',index=False)
    put_json(OUT/'variable_units.json',units)
    quality=dict(passed=True,start_local='2021-01-01 00:00',end_local_inclusive='2026-01-07 23:00',
        reference_locations=len(points),mapped_taxi_zones=len(lookup),expected_utc_hours_per_location=len(expected),
        utc_rows=len(weather),local_rows=len(table),missing_values=weather[VARIABLES].isna().sum().to_dict(),
        duplicate_utc_keys=int(weather.duplicated(['weather_location_id','timestamp_utc']).sum()),
        duplicate_local_keys=int(table.duplicated(keys).sum()),
        test_week_rows=int(weather.is_test_week.sum()),
        repeated_local_hours=int(table.is_dst_repeated_hour.sum()),
        utc_counts_by_location=weather.groupby('weather_location_id').size().to_dict(),
        validated_utc=datetime.now(timezone.utc).isoformat())
    put_json(OUT/'validation.json',quality)
    provenance=dict(provider='Open-Meteo',underlying_dataset='ECMWF/Copernicus ERA5',model='era5',
        spatial_resolution='0.25 degrees (about 25 km); borough representative points, not zone-level measurements',
        source_docs='https://open-meteo.com/en/docs/historical-weather-api',
        attribution='Weather data by Open-Meteo; ERA5 by ECMWF/Copernicus Climate Change Service (C3S).',
        warning='Retrospective reanalysis is not a weather forecast issued at the demand forecast origin. Test-week actual weather must not be used as if known in advance.',
        zone_mapping='All polygons with the same LocationID mapped to their shapefile borough; EWR retained separately; unmapped demand zone IDs must be reported, not guessed.',
        files={str(p.relative_to(OUT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(RAW.glob('*.json'))})
    put_json(OUT/'provenance.json',provenance)
    readme='''# Hourly weather for zonal NYC pickup-demand modeling

Coverage: January 1, 2021 00:00 through January 7, 2026 23:00, America/New_York.
Provider: Open-Meteo Historical Weather API, explicit ERA5 model. These are retrospective gridded reanalysis estimates, not station observations or archived operational forecasts.
Docs: https://open-meteo.com/en/docs/historical-weather-api
Attribution: Weather data by Open-Meteo; ERA5 by ECMWF/Copernicus Climate Change Service (C3S).

## Files and joins
- `nyc_hourly_weather_utc_2021_2026.parquet` / `.csv`: canonical UTC hours, local timestamp with offset, date/hour, test-week flag, 12 weather variables.
- `nyc_hourly_weather_local_2021_2026.parquet` / `.csv`: one row per reference location/local date/hour. Join pickup tables on `date`, `hour`, and weather_location_id after applying the lookup below. Convert both date columns to the same type before merging; use validate='many_to_one'.
- `taxi_zone_weather_lookup.csv`: LocationID -> borough -> weather_location_id. Shapefile duplicate polygons are consolidated. Unmapped pickup IDs need explicit handling; do not invent boroughs.
- `weather_reference_locations.csv`: representative point inside each borough polygon union; Newark Airport (EWR) is a separate reference.
- `source_grid_locations.csv`: actual grid coordinates returned by the provider. ERA5 is coarse (~25 km); some reference points may share a grid cell. This table does not imply independent weather in each taxi zone.
- `variable_units.json`: units returned by the provider. Temperature/dew point/apparent temperature: Celsius; relative humidity/cloud: percent; wind speed: m/s; direction: degrees; pressure: hPa; precipitation/rain: mm; snowfall: cm; weather_code: WMO category, not a continuous numerical measurement.
- `raw/`: cached original yearly API responses and exact requests with retrieval times.
- `validation.json`: coverage, uniqueness, missingness, range and DST checks.
- `provenance.json`: sources, mapping policy and SHA256 checksums of raw responses.
- `collect_hourly_weather.py`: rerunnable collector; reuses cached matching responses.

## Time and feature semantics
UTC is canonical. We requested UTC then converted with America/New_York to handle DST correctly. On spring transitions, the nonexistent 02:00 local hour is absent. On autumn transitions, two real UTC hours map to one local hour: continuous weather features are averaged (wind direction uses a circular mean) and utc_hours_in_local_hour=2. For repeated hours, weather_code is set to missing in the local table because averaging categorical codes is invalid; derive a categorical rule explicitly if needed. Never fill a missing demand hour with zero merely to match weather. Weather precipitation/rain/snowfall are provider preceding-hour accumulations; local repeated-hour averages are hourly-intensity features, not totals over both real hours.

## Leakage and experiment use
Rows from January 1-7, 2026 are tagged is_test_week=True and are retrospective actual-condition estimates. Do not feed those into the main week-ahead forecast as if known on December 31, 2025. They are suitable for diagnostics or a separately labeled known-weather upper-bound experiment. A realistic week-ahead weather feature requires an archived forecast run available before the forecast origin, or training-only climatology. No such forecast has been collected here. Reanalysis itself is finalized with hindsight and is not an exact historical as-of observation feed.

Long weather windows and validation folds must use past-only feature construction. No interpolation, invented precipitation zeros or source mixing is performed. No pickup data or notebooks have been altered.
'''
    # Correct categorical treatment for repeated local hour.
    table.loc[table.is_dst_repeated_hour,'weather_code']=float('nan')
    table.to_parquet(OUT/'nyc_hourly_weather_local_2021_2026.parquet',index=False)
    table.to_csv(OUT/'nyc_hourly_weather_local_2021_2026.csv',index=False)
    quality['local_categorical_missing_due_to_dst']=int(table.weather_code.isna().sum())
    put_json(OUT/'validation.json',quality)
    (OUT/'README.md').write_text(readme,encoding='utf-8')
    if Path(__file__).resolve() != (OUT/'collect_hourly_weather.py').resolve():
        shutil.copy2(__file__,OUT/'collect_hourly_weather.py')
    print(json.dumps(quality,indent=2),flush=True)

if __name__=='__main__':main()
