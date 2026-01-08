import csv
import requests
import time
import json
import pandas as pd
from pathlib import Path

# ── CONFIG ────────────────────────────────────────────────
API_KEY      = ""   # <-- Add your API key here
CSV_PATH     = Path("")  # Path to CSV with IPs (one per line)
CACHE_PATH   = Path("checked_ips.json")  # Local cache to avoid re-checking IPs
MAX_AGE_DAYS = 90
SLEEP_SECS   = 0
# ──────────────────────────────────────────────────────────

# Optional keywords to ignore
EXCLUDE_ISPS = {
    # "example",
    # "test",
}


def load_cache() -> dict:
    if CACHE_PATH.exists():
        try:
            with CACHE_PATH.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_cache(cache: dict) -> None:
    with CACHE_PATH.open("w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)


def check_ip(ip: str, cache: dict) -> tuple[str, str, str, str]:
    url = "https://api.abuseipdb.com/api/v2/check"
    params = {"ipAddress": ip, "maxAgeInDays": str(MAX_AGE_DAYS)}
    headers = {"Accept": "application/json", "Key": API_KEY}

    try:
        r = requests.get(url, headers=headers, params=params, timeout=30)
        r.raise_for_status()
        data = r.json().get("data", {})
        result = (
            str(data.get("abuseConfidenceScore", "N/A")),
            data.get("countryCode", "N/A"),
            data.get("isp", "N/A"),
            data.get("domain", "N/A")
        )
    except Exception as e:
        print(f"[!] Error while checking {ip}: {e}")
        result = ("Error", "Error", "Error", "Error")

    cache[ip] = {
        "score": result[0],
        "country": result[1],
        "isp": result[2],
        "domain": result[3]
    }
    return result


def should_print(score: str, isp: str, domain: str) -> bool:
    if not score.isdigit():
        return False
    if int(score) == 0:
        return False
    text = f"{isp} {domain}".lower()
    return all(excl not in text for excl in EXCLUDE_ISPS)


def main() -> None:
    if not CSV_PATH.exists():
        print("[!] CSV path not set or file missing.")
        return

    # Load CSV IPs
    with CSV_PATH.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        csv_ips = [row[0].strip() for row in reader if row]

    cache = load_cache()

    checked = 0
    skipped_cache = 0

    for ip in csv_ips:
        if not ip:
            continue

        # Skip if cached
        if ip in cache:
            skipped_cache += 1
            score, country, isp, domain = (
                cache[ip]["score"],
                cache[ip]["country"],
                cache[ip]["isp"],
                cache[ip].get("domain", "N/A")
            )
            if should_print(score, isp, domain):
                print(f"{ip}, {score}%, {country}, {isp}, {domain} (cached)")
            continue

        score, country, isp, domain = check_ip(ip, cache)
        checked += 1
        if should_print(score, isp, domain):
            print(f"{ip}, {score}%, {country}, {isp}, {domain}")

        time.sleep(SLEEP_SECS)

    save_cache(cache)

    print("\n─── Summary ───")
    print(f"Total IPs in CSV: {len(csv_ips)}")
    print(f"Skipped (already cached): {skipped_cache}")
    print(f"Checked via API: {checked}")


if __name__ == "__main__":
    main()
