#!/usr/bin/env python3
"""Benchmark Nominatim vs Geocodio accuracy on apartment-heavy addresses.

Why: Nominatim resolves apartment/multi-unit addresses poorly. Since It's
Electric leads skew toward apartments, a bad geocode picks the wrong nearest
charger. This script compares both providers on the metric that matters:
does it resolve, and does it land close enough to pick the right charger.

Usage:
    export GEOCODIO_API_KEY=...            # free key from geocod.io
    python scripts/geocode_benchmark.py addresses.csv

Input CSV columns:
    address              (required) free-text address, as it arrives from forms
    truth_lat,truth_lon  (optional) hand-verified coordinates for ground truth

Two modes, chosen automatically per row:
  - Accuracy  (truth present): error in meters for each provider + whether the
    provider's nearest-charger pick matches the truth's nearest-charger pick.
  - Agreement (no truth):      resolution rate + distance between the two
    providers' answers. Flags disagreement; cannot say which is correct.
"""

import csv
import os
import sys
import time

from geopy.distance import geodesic
from geopy.exc import GeocoderServiceError
from geopy.geocoders import Geocodio, Nominatim

from itselectric.geo import _strip_unit, find_nearest_charger, load_chargers

NOMINATIM = Nominatim(user_agent="itselectric-benchmark/1.0", timeout=10)


def geocode_nominatim(addr):
    try:
        loc = NOMINATIM.geocode(addr)
    except GeocoderServiceError:
        loc = None
    time.sleep(1)  # Nominatim ToS: 1 req/sec
    return (loc.latitude, loc.longitude) if loc else None


def geocode_geocodio(client, addr):
    try:
        loc = client.geocode(addr, timeout=10)
    except GeocoderServiceError:
        loc = None
    return (loc.latitude, loc.longitude) if loc else None


def nearest_name(coords, chargers):
    if coords is None:
        return None
    result = find_nearest_charger(coords[0], coords[1], chargers)
    return result[0]["name"] if result else None


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: python scripts/geocode_benchmark.py <addresses.csv>")

    key = os.environ.get("GEOCODIO_API_KEY")
    if not key:
        sys.exit("set GEOCODIO_API_KEY (free key from geocod.io)")
    geocodio = Geocodio(api_key=key)

    chargers = load_chargers()
    with open(sys.argv[1], newline="") as f:
        rows = list(csv.DictReader(f))

    n_nom = n_geo = 0
    nom_errs, geo_errs = [], []
    nom_pick_ok = geo_pick_ok = pick_total = 0
    agree_dists = []

    print(f"{'address':<45} {'nominatim':>12} {'geocodio':>12}  note")
    print("-" * 90)

    for row in rows:
        raw = row["address"]
        addr = _strip_unit(raw)
        nom = geocode_nominatim(addr)
        geo = geocode_geocodio(geocodio, addr)

        n_nom += nom is not None
        n_geo += geo is not None

        truth = None
        if row.get("truth_lat") and row.get("truth_lon"):
            truth = (float(row["truth_lat"]), float(row["truth_lon"]))

        note = ""
        if truth:
            truth_pick = nearest_name(truth, chargers)
            pick_total += 1
            if nom:
                nom_errs.append(geodesic(truth, nom).meters)
                nom_pick_ok += nearest_name(nom, chargers) == truth_pick
            if geo:
                geo_errs.append(geodesic(truth, geo).meters)
                geo_pick_ok += nearest_name(geo, chargers) == truth_pick
            n_e = f"{nom_errs[-1]:.0f}m" if nom else "FAIL"
            g_e = f"{geo_errs[-1]:.0f}m" if geo else "FAIL"
            note = f"err nom={n_e} geo={g_e}"
            # Dump raw coords when either provider lands >1km off, to tell a
            # real accuracy miss from a harness bug (lat/lon swap, wrong metro).
            if os.environ.get("BENCH_DEBUG") and (
                (geo_errs and geo_errs[-1] > 1000) or (nom_errs and nom_errs[-1] > 1000)
            ):
                print(f"    truth={truth}  nom={nom}  geo={geo}")
        elif nom and geo:
            d = geodesic(nom, geo).meters
            agree_dists.append(d)
            note = f"disagree {d:.0f}m"
        elif nom or geo:
            note = "one FAILED"

        print(f"{raw[:44]:<45} {str(nom is not None):>12} {str(geo is not None):>12}  {note}")

    total = len(rows)
    print("\n=== summary ===")
    print(f"rows: {total}")
    print(f"resolved: nominatim {n_nom}/{total}  geocodio {n_geo}/{total}")

    def med(xs):
        s = sorted(xs)
        return s[len(s) // 2] if s else float("nan")

    if pick_total:
        print("\n-- accuracy (rows with ground truth) --")
        print(f"median error: nominatim {med(nom_errs):.0f}m  geocodio {med(geo_errs):.0f}m")
        print(f"nearest-charger pick correct: "
              f"nominatim {nom_pick_ok}/{pick_total}  geocodio {geo_pick_ok}/{pick_total}")
    if agree_dists:
        print("\n-- agreement (rows without ground truth) --")
        print(f"median distance between providers: {med(agree_dists):.0f}m")
        print(f"disagree >100m: {sum(d > 100 for d in agree_dists)}/{len(agree_dists)}")


if __name__ == "__main__":
    main()
