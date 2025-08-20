import os, json, datetime, urllib.request, boto3

ssm = boto3.client("ssm")
s3_cient = boto3.client("s3")

RAW_BUCKET = os.environ["RAW_BUCKET"]
FPL_BASE_URL_PARAM = os.environ.get("FPL_BASE_URL_PARAM", "/fpl-optimizer/fpl_base_url")

ENDPOINTS = ["bootstrap-static/", "fixtures"]

def _get_base() -> str:
    return ssm.get_parameter(Name=FPL_BASE_URL_PARAM)["Parameter"]["Value"].rstrip("/")

def _fetch(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=20) as response:
        return response.read()

def _put(key: str, data: bytes):
    s3_cient.put_object(Bucket=RAW_BUCKET, Key=key, Body=data)

def lambda_handler(event, context):
    base = _get_base()
    time_stamp = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    date = datetime.datetime.utcnow().strftime("dt=%Y-%m-%d")
    prefix = f"fpl_raw/{date}/{time_stamp}"
    out = {}
    for endpoint in ENDPOINTS:
        url = f"{base}/{endpoint}"
        data = _fetch(url)
        key = f"{prefix}/{endpoint.replace('/', '_')}.json"
        _put(key, data)
        out[endpoint] = {"key": key, "bytes": len(data)}
    _put(f"{prefix}/_manifest.json", json.dumps(out).encode("utf-8"))
    return {"status": "ok", "objects": out, "prefix": prefix}