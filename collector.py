#!/usr/bin/env python3
"""Collect NASA POWER hourly T2M and store one real record per KST date."""
import argparse
import json
import math
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")
UTC = timezone.utc
ROOT = Path(__file__).resolve().parent
HISTORY = ROOT / "data" / "history.json"
LATITUDE = 37.5665
LONGITUDE = 126.9780
API_BASE = "https://power.larc.nasa.gov/api/temporal/hourly/point"

def request_day(target: date):
    # A KST day spans 15:00 UTC on the previous date through 14:00 UTC
    # on the target date. Request a UTC date envelope and group timestamps in KST.
    utc_start = datetime.combine(target, datetime.min.time(), tzinfo=KST).astimezone(UTC)
    utc_end = datetime.combine(target + timedelta(days=1), datetime.min.time(), tzinfo=KST).astimezone(UTC)
    start = (utc_start.date() - timedelta(days=1)).strftime("%Y%m%d")
    end = utc_end.date().strftime("%Y%m%d")
    params = {
        "parameters": "T2M", "community": "RE",
        "longitude": str(LONGITUDE), "latitude": str(LATITUDE),
        "start": start, "end": end, "format": "JSON", "time-standard": "UTC"
    }
    url = API_BASE + "?" + urlencode(params)
    req = Request(url, headers={"User-Agent": "EarthPulseStudentProject/1.0", "Accept": "application/json"})
    with urlopen(req, timeout=35) as response:
        status = response.status
        raw = response.read().decode("utf-8")
    if status != 200:
        raise RuntimeError(f"NASA POWER HTTP {status}")
    payload = json.loads(raw)
    try:
        series = payload["properties"]["parameter"]["T2M"]
    except (KeyError, TypeError) as exc:
        raise ValueError("NASA POWER 응답 구조에 properties.parameter.T2M이 없습니다.") from exc
    if not isinstance(series, dict) or not series:
        raise ValueError("T2M 시간별 데이터가 비어 있거나 예상 형식이 아닙니다.")

    values = []
    for stamp, raw_value in series.items():
        try:
            ts = datetime.strptime(stamp, "%Y%m%d%H").replace(tzinfo=UTC).astimezone(KST)
            value = float(raw_value)
        except (ValueError, TypeError):
            continue
        if ts.date() != target:
            continue
        # NASA POWER uses -999 as a missing-value sentinel.
        if not math.isfinite(value) or value <= -900:
            continue
        values.append((ts, value))
    if not values:
        raise ValueError(f"{target.isoformat()} KST 날짜의 유효한 T2M 값이 없습니다.")
    values.sort(key=lambda pair: pair[0])
    mean = sum(value for _, value in values) / len(values)
    retrieved = datetime.now(KST).isoformat(timespec="seconds")
    return {
        "kst_date": target.isoformat(),
        "value_c": round(mean, 3),
        "unit": "°C",
        "valid_hours": len(values),
        "source_parameter": "T2M",
        "source_url": url,
        "source_time_standard": "UTC converted to Asia/Seoul",
        "source_window_utc": {"start": start, "end": end},
        "retrieved_at_kst": retrieved,
        "timezone": "Asia/Seoul",
        "status": "ok",
        "provenance": "NASA POWER Hourly API; mean of valid hourly values whose timestamps fall on the target KST date"
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="KST target date YYYY-MM-DD; defaults to yesterday in KST")
    parser.add_argument("--history", default=str(HISTORY), help="history JSON path")
    args = parser.parse_args()
    now_kst = datetime.now(KST)
    target = date.fromisoformat(args.date) if args.date else (now_kst.date() - timedelta(days=1))
    if target >= now_kst.date() and args.date is None:
        raise ValueError("대상 날짜는 완료된 KST 날짜여야 합니다.")

    history_path = Path(args.history)
    history_path.parent.mkdir(parents=True, exist_ok=True)
    if history_path.exists():
        try:
            doc = json.loads(history_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("기존 history.json이 올바른 JSON이 아닙니다. 원본을 보존하고 수동 점검하세요.") from exc
    else:
        doc = {"schema_version": 1, "records": []}
    if not isinstance(doc, dict) or not isinstance(doc.get("records"), list):
        raise ValueError("history.json 스키마가 예상과 다릅니다.")

    record = request_day(target)
    # Idempotent upsert: one record per KST date; same-date reruns replace that day's row.
    rows = [r for r in doc["records"] if isinstance(r, dict) and r.get("kst_date") != target.isoformat()]
    rows.append(record)
    rows.sort(key=lambda r: r.get("kst_date", ""))
    doc["schema_version"] = 1
    doc["records"] = rows
    doc["updated_at_kst"] = datetime.now(KST).isoformat(timespec="seconds")
    temp = history_path.with_suffix(".json.tmp")
    temp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(history_path)
    print(json.dumps({"result": "success", "kst_date": record["kst_date"], "value_c": record["value_c"], "valid_hours": record["valid_hours"], "retrieved_at_kst": record["retrieved_at_kst"], "history": str(history_path)}, ensure_ascii=False))

if __name__ == "__main__":
    try:
        main()
    except HTTPError as exc:
        print(f"NASA POWER HTTP {exc.code}: {exc.reason}", file=sys.stderr)
        sys.exit(2)
    except URLError as exc:
        print(f"Network/timeout error: {exc.reason}", file=sys.stderr)
        sys.exit(3)
    except Exception as exc:
        print(f"Collection failed: {exc}", file=sys.stderr)
        sys.exit(4)
