"""Reproduce the existing 02-series cleaning for ONLY Jan 1-7 2026 pickup evaluation.
Bounded-memory DuckDB; preserve raw rows/all-column deduplication and legacy metric definitions.
No original monthly output is overwritten. No modeling or test scoring is performed here.
"""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,time
import duckdb
import pandas as pd
import pyarrow.parquet as pq

RAW=Path(os.environ.get('RIDESHARE_RAW_DIR', 'data/raw/fhvhv'))/'fhvhv_tripdata_2026-01.parquet'
ROOT=Path(os.environ.get('RIDESHARE_PROCESSED_DIR', 'data/processed'))/'model_evaluation_2026'
OUTPUT=ROOT/'fhvhv_by_zone_hour_2026_01_01_to_07.parquet'
REFERENCE=Path('notebooks/02b_prepare_hourly_2024_2025.ipynb')
START='2026-01-01 00:00:00';END='2026-01-08 00:00:00'
RULES="""trip_miles > 0 AND trip_time_cal > 0 AND base_passenger_fare > 0
 AND trip_speed > 1 AND driver_pay > 0 AND pickup_datetime >= request_datetime
 AND trip_miles <= 200 AND trip_time_cal <= 10800 AND trip_speed <= 120"""
VERSION='pickup-evaluation-week-v1-existing-2024-2025-cleaning'

def save(path,obj):
 tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(obj,indent=2,default=str),encoding='utf-8');tmp.replace(path)

def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
 return h.hexdigest()

def main():
 started=time.perf_counter();ROOT.mkdir(parents=True,exist_ok=True)
 state=ROOT/'test_week_aggregation_state.json'
 def status(step,**kw):
  save(state,dict(pid=os.getpid(),step=step,updated_utc=datetime.now(timezone.utc).isoformat(),**kw))
 if OUTPUT.exists():
  validation=OUTPUT/'_evaluation_validation.json'
  if validation.exists() and (OUTPUT/'_SUCCESS').exists():
   result=json.loads(validation.read_text());assert result['passed'] and result['contract']['version']==VERSION
   assert result['contract']['source_sha256']==sha(RAW),'Source changed; do not reuse old target'
   print('Existing matching validated output retained.');return
  raise RuntimeError('Existing incomplete output: inspect it before recovery; no overwrite attempted.')
 assert RAW.is_file()
 source_stat=RAW.stat();notebook=json.loads(REFERENCE.read_text(encoding='utf-8'))
 clean_cell=next(''.join(c['source']) for c in notebook['cells'] if c['cell_type']=='code' and '.dropDuplicates()' in ''.join(c['source']) and 'trip_speed' in ''.join(c['source']))
 expected=["trip_miles", "trip_time_cal", "base_passenger_fare", "trip_speed", "driver_pay", "request_datetime", '200','10800','120']
 assert all(x in clean_cell for x in expected)
 staging=ROOT/('test_week_staging_'+datetime.now().strftime('%Y%m%d_%H%M%S'))
 staging.mkdir()
 work=ROOT/('work_'+str(os.getpid()));work.mkdir()
 con=duckdb.connect(str(work/'cleaning.duckdb'))
 con.execute('SET threads=1');con.execute("SET memory_limit='256MB'");con.execute('SET preserve_insertion_order=false')
 con.execute('SET temp_directory=?',[str(work/'spill')])
 con.read_parquet(str(RAW)).create_view('raw_month')
 con.execute(f"CREATE VIEW raw_week AS SELECT * FROM raw_month WHERE pickup_datetime >= TIMESTAMP '{START}' AND pickup_datetime < TIMESTAMP '{END}'")
 raw_count=con.execute('SELECT count(*) FROM raw_week').fetchone()[0]
 status('deduplicating',raw_week_rows=raw_count);print('Raw test-week rows:',raw_count,flush=True)
 # Spark adds deterministic derived columns BEFORE dropDuplicates; all raw columns remain in the key.
 # Filtering the pickup range commutes with exact all-column deduplication.
 derived='''SELECT *,
   CAST(floor(epoch(dropoff_datetime)) AS BIGINT)-CAST(floor(epoch(pickup_datetime)) AS BIGINT) AS trip_time_cal,
   (trip_miles / NULLIF(trip_time,0))*3600 AS trip_speed FROM raw_week'''
 con.execute('CREATE TABLE deduplicated AS '+derived+' WHERE FALSE')
 # Exact duplicate rows necessarily share the same pickup date. Daily partitions
 # preserve global all-column deduplication while bounding hash-table memory.
 for day in pd.date_range(START,periods=7,freq='D'):
  tomorrow=day+pd.Timedelta(days=1)
  con.execute('INSERT INTO deduplicated SELECT DISTINCT * FROM ('+derived+
   f" WHERE pickup_datetime>=TIMESTAMP '{day}' AND pickup_datetime<TIMESTAMP '{tomorrow}')")
  status('deduplicating_by_day',day=str(day.date()),raw_week_rows=raw_count)
  print('Deduplicated day:',str(day.date()),flush=True)
 dedup_count=con.execute('SELECT count(*) FROM deduplicated').fetchone()[0]
 status('cleaning',raw_week_rows=raw_count,deduplicated_rows=dedup_count);print('After exact deduplication:',dedup_count,flush=True)
 con.execute(f'CREATE TABLE cleaned AS SELECT * EXCLUDE(cbd_congestion_fee),coalesce(cbd_congestion_fee,0.0) AS cbd_congestion_fee FROM deduplicated WHERE {RULES}')
 cleaned_count=con.execute('SELECT count(*) FROM cleaned').fetchone()[0]
 assert cleaned_count>0
 assert con.execute('SELECT count(*) FROM cleaned WHERE PULocationID IS NULL').fetchone()[0]==0,'Cleaning retained null pickup zones; investigate rather than silently discard.'
 assert con.execute(f'SELECT count(*) FROM cleaned WHERE NOT ({RULES})').fetchone()[0]==0
 print('Cleaned test-week trips:',cleaned_count,flush=True)
 status('aggregating',cleaned_trips=cleaned_count)
 # Match 02's aggregate-first sums, rounding and null-fee behavior. No extra imputation/filtering.
 con.execute('''CREATE TABLE aggregates AS WITH featured AS (
  SELECT PULocationID,CAST(pickup_datetime AS DATE) AS date,
   year(pickup_datetime)::INTEGER AS year,month(pickup_datetime)::INTEGER AS month,
   week(pickup_datetime)::INTEGER AS week,dayofweek(pickup_datetime)::INTEGER+1 AS day_of_week,
   CASE WHEN dayofweek(pickup_datetime) IN (0,6) THEN 1 ELSE 0 END AS is_weekend,
   hour(pickup_datetime)::INTEGER AS hour,
   CASE WHEN pickup_datetime < TIMESTAMP '2025-01-05' THEN 'pre_policy' ELSE 'post_policy' END AS policy_period,
   CAST(floor(epoch(pickup_datetime)) AS BIGINT)-CAST(floor(epoch(request_datetime)) AS BIGINT) AS wait_time_sec,
   base_passenger_fare,driver_pay,trip_miles,trip_time_cal/60.0 AS trip_duration_min,
   base_passenger_fare+tolls+tips+congestion_surcharge+sales_tax+bcf+airport_fee+cbd_congestion_fee AS total_fare,
   base_passenger_fare+tips-driver_pay AS tnc_comp FROM cleaned)
 SELECT PULocationID,date,year,month,week,day_of_week,is_weekend,hour,policy_period,
  count(*) AS trip_count,
  round(sum(wait_time_sec)/count(*),2) AS avg_wait_time_sec,
  round(sum(base_passenger_fare)/sum(trip_miles),4) AS base_fare_per_mile,
  round(sum(base_passenger_fare)/sum(trip_duration_min),4) AS base_fare_per_min,
  round(sum(base_passenger_fare)/count(*),4) AS base_fare_per_trip,
  round(sum(total_fare)/count(*),4) AS total_fare_per_trip,
  round(sum(driver_pay)/sum(trip_miles),4) AS driver_pay_per_mile,
  round(sum(driver_pay)/sum(trip_duration_min),4) AS driver_pay_per_min,
  round(sum(driver_pay)/count(*),4) AS driver_pay_per_trip,
  round(sum(tnc_comp)/sum(base_passenger_fare),4) AS tnc_commission_rate
 FROM featured GROUP BY PULocationID,date,year,month,week,day_of_week,is_weekend,hour,policy_period''')
 target=staging/'part-00000.parquet'
 con.execute('COPY aggregates TO ? (FORMAT PARQUET, COMPRESSION SNAPPY)',[str(target)])
 status('validating',cleaned_trips=cleaned_count)
 con.read_parquet(str(target)).create_view('saved')
 observed=con.execute('SELECT sum(trip_count),count(*),count(DISTINCT date),min(date),max(date),count(DISTINCT PULocationID) FROM saved').fetchone()
 assert observed[0]==cleaned_count
 assert observed[2]==7 and str(observed[3])=='2026-01-01' and str(observed[4])=='2026-01-07'
 assert con.execute('SELECT count(*) FROM saved WHERE PULocationID IS NULL OR hour NOT BETWEEN 0 AND 23 OR trip_count<=0').fetchone()[0]==0
 assert con.execute('SELECT count(*) FROM (SELECT 1 FROM saved GROUP BY PULocationID,date,hour HAVING count(*)>1)').fetchone()[0]==0
 times=con.execute('SELECT date,hour FROM saved GROUP BY date,hour').df()
 timestamps=pd.to_datetime(times.date)+pd.to_timedelta(times.hour,unit='h')
 assert len(timestamps)==168 and set(timestamps)==set(pd.date_range(START,periods=168,freq='h'))
 # Reconcile every city hour and every zone-day against cleaned raw records, not just a grand total.
 for label,raw_sql,saved_sql in [
  ('city_hour','SELECT CAST(pickup_datetime AS DATE) AS date,hour(pickup_datetime) AS hour,count(*) AS n FROM cleaned GROUP BY date,hour',
   'SELECT date,hour,sum(trip_count) AS n FROM saved GROUP BY date,hour'),
  ('zone_day','SELECT PULocationID,CAST(pickup_datetime AS DATE) AS date,count(*) AS n FROM cleaned GROUP BY PULocationID,date',
   'SELECT PULocationID,date,sum(trip_count) AS n FROM saved GROUP BY PULocationID,date')]:
  mismatches=con.execute(f'SELECT count(*) FROM (({raw_sql} EXCEPT {saved_sql}) UNION ALL ({saved_sql} EXCEPT {raw_sql}))').fetchone()[0]
  assert mismatches==0,f'{label} reconciliation failed'
 con.execute('COPY (SELECT CAST(pickup_datetime AS DATE) AS date,hvfhs_license_num,count(*) AS cleaned_trips FROM cleaned GROUP BY date,hvfhs_license_num ORDER BY date,hvfhs_license_num) TO ? (HEADER, DELIMITER \',\')',[str(staging/'_cleaned_platform_daily.csv')])
 contract=dict(version=VERSION,family='pickup',year=2026,month=1,coverage='test_week_only',
  start_inclusive=START,end_exclusive=END,date_basis='actual_pickup_date_and_hour',
  source_path=str(RAW),source_size=source_stat.st_size,source_mtime_ns=source_stat.st_mtime_ns,source_sha256=sha(RAW),
  cleaning_reference=str(REFERENCE),cleaning_cell_sha256=hashlib.sha256(clean_cell.encode()).hexdigest(),
  cleaning_sql=RULES,deduplication='exact all raw columns before fee coalescing',platform_scope='all recorded HVFHV platforms',
  metrics='existing 2024/2025 aggregate-first definitions; 19-column pickup schema',engine='DuckDB '+duckdb.__version__)
 assert RAW.stat().st_size==source_stat.st_size and RAW.stat().st_mtime_ns==source_stat.st_mtime_ns,'Raw source changed during execution'
 validation=dict(passed=True,contract=contract,raw_week_rows=raw_count,deduplicated_week_rows=dedup_count,
  duplicate_rows_removed=raw_count-dedup_count,cleaned_trips=cleaned_count,rows=int(observed[1]),observed_zones=int(observed[5]),
  city_hours=168,days=7,city_hour_reconciliation_passed=True,zone_day_reconciliation_passed=True,
  output_sha256=sha(target),validated_utc=datetime.now(timezone.utc).isoformat(),elapsed_seconds=round(time.perf_counter()-started,2))
 save(staging/'_aggregation_contract.json',contract);save(staging/'_evaluation_validation.json',validation)
 (staging/'_SUCCESS').write_text('',encoding='utf-8')
 con.close();staging.rename(OUTPUT)
 status('completed',output=str(OUTPUT),validation=validation)
 shutil_copy=ROOT/'aggregate_test_week_2026.py'
 if Path(__file__).resolve()!=shutil_copy.resolve():
  import shutil;shutil.copy2(__file__,shutil_copy)
 print(json.dumps({k:v for k,v in validation.items() if k!='contract'},indent=2),flush=True)

if __name__=='__main__':
 try:main()
 except Exception as exc:
  ROOT.mkdir(parents=True,exist_ok=True)
  save(ROOT/'test_week_aggregation_error.json',dict(error=repr(exc),pid=os.getpid(),time_utc=datetime.now(timezone.utc).isoformat()))
  raise
