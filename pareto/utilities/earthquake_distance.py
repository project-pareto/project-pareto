#####################################################################################################
# PARETO was produced under the DOE Produced Water Application for Beneficial Reuse Environmental
# Impact and Treatment Optimization (PARETO), and is copyright (c) 2021-2025 by the software owners:
# The Regents of the University of California, through Lawrence Berkeley National Laboratory, et al.
# All rights reserved.
#
# NOTICE. This Software was developed under funding from the U.S. Department of Energy and the U.S.
# Government consequently retains certain rights. As such, the U.S. Government has been granted for
# itself and others acting on its behalf a paid-up, nonexclusive, irrevocable, worldwide license in
# the Software to reproduce, distribute copies to the public, prepare derivative works, and perform
# publicly and display publicly, and to permit others to do so.
#####################################################################################################

import os
import re
import json
import csv
import pandas as pd
import pyproj
import urllib.request
import urllib.error
from datetime import datetime

# API documentation: https://earthquake.usgs.gov/fdsnws/event/1/
usgs_api_url = (
    "https://earthquake.usgs.gov/fdsnws/event/1/query"
    + "?format=geojson"
    + "&latitude={lat}"
    + "&longitude={lon}"
    + "&maxradiuskm={max_radius_km}"
    + "&minmagnitude={min_magnitude}"
    + ""
)
# API documentation: https://www.beg.utexas.edu/texnet-cisr/texnet/earthquake-catalog/ =>
# Important Information =>
# Frequently Asked Questions =>
# Is there a RESTful API that I can use to access these data?
# https://maps.texnet.beg.utexas.edu/arcgis/rest/services/catalog/catalog_all/MapServer
texnet_api_url = (
    "https://maps.texnet.beg.utexas.edu/arcgis/rest/services/catalog/catalog_all/MapServer/0/query"
    + "?f=geojson"
    "&where=Magnitude>={min_magnitude}"
    + "&text="
    + "&objectIds="
    + "&time="
    + "&timeRelation=esriTimeRelationOverlaps"
    + "&geometry={lon},{lat}"
    + "&geometryType=esriGeometryEnvelope"
    + "&inSR="
    + "&spatialRel=esriSpatialRelWithin"
    + "&distance={max_radius_mi}"
    + "&units=esriSRUnit_StatuteMile"
    + "&relationParam="
    + "&outFields=*"
    + "&returnGeometry=true"
    + "&returnTrueCurves=false"
    + "&maxAllowableOffset="
    + "&geometryPrecision="
    + "&outSR="
    + "&havingClause="
    + "&returnIdsOnly=false"
    + "&returnCountOnly=false"
    + "&orderByFields="
    + "&groupByFieldsForStatistics="
    + "&outStatistics="
    + "&returnZ=false"
    + "&returnM=false"
    + "&gdbVersion="
    + "&historicMoment="
    + "&returnDistinctValues=false"
    + "&resultOffset="
    + "&resultRecordCount="
    + "&returnExtentOnly=false"
    + "&sqlFormat=none"
    + "&datumTransformation="
    + "&parameterValues="
    + "&rangeValues="
    + "&quantizationParameters="
    + "&featureEncoding=esriDefault"
    + ""
)
mi_per_m = 0.000621371  # mi/m
date_re = re.compile("^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
save_re = re.compile("^.*\.(csv|xlsx)$", re.IGNORECASE)
geod = pyproj.Geod(ellps="WGS84")


def convert_date_to_timestamp(date):
    if date:
        if date_re.match(date):
            date_ts = datetime.strptime(date, "%Y-%m-%d").timestamp()
        else:
            raise Exception("date must be in YYYY-MM-DD")
    else:
        date_ts = None
    return date_ts


def calculate_earthquake_distances(
    swd_latlons,
    api="usgs",
    max_radius_mi=5.59,
    min_magnitude=3,
    min_date=None,
    max_date=None,
    save=None,
    overwrite=False,
):
    # swd_latlons is a list of dicts with id, lat, and lon
    if api not in ("usgs", "texnet"):
        raise Exception("api must be either usgs or texnet")

    min_date_ts = convert_date_to_timestamp(min_date)
    max_date_ts = convert_date_to_timestamp(max_date)
    if max_date_ts:
        max_date_ts += 24 * 60 * 60  # max date 24:00:00

    if min_date_ts and max_date_ts and min_date_ts > max_date_ts:
        raise Exception("min_date must be earlier than or equal to max_date")

    if save:
        m = save_re.match(save)
        if not m:
            raise Exception("save must be in *.csv or *.xlsx")
        fmt = m[1].lower()
        if not overwrite and os.path.exists(save):
            raise Exception(f"{save} already exists")
    else:
        fmt = None

    earthquake_distances = []

    keys = ("swd_id", "eq_id", "time", "distance_mi", "magnitude")

    for swd_latlon in swd_latlons:
        swd_id = swd_latlon["swd_id"]
        swd_lat = swd_latlon["lat"]
        swd_lon = swd_latlon["lon"]
        if api == "usgs":
            max_radius_km = max_radius_mi / mi_per_m / 1000  # 5.59 mi
            url = usgs_api_url.format(
                lat=swd_lat,
                lon=swd_lon,
                max_radius_km=max_radius_km,
                min_magnitude=min_magnitude,
            )
        else:
            url = texnet_api_url.format(
                lat=swd_lat,
                lon=swd_lon,
                max_radius_mi=max_radius_mi,
                min_magnitude=min_magnitude,
            )

        try:
            request = urllib.request.Request(url)
            with urllib.request.urlopen(request) as f:
                response = json.load(f)
        except:
            raise Exception("API error")
        for feat in response["features"]:
            eq_id = feat["id"]
            props = feat["properties"]
            coords = feat["geometry"]["coordinates"]

            time_ts = (props["time"] if api == "usgs" else props["Event_Date"]) / 1000
            if (min_date_ts and time_ts < min_date_ts) or (
                max_date_ts and time_ts > max_date_ts
            ):
                continue

            time = datetime.fromtimestamp(time_ts).strftime("%Y-%m-%d %H:%M:%S")
            lat = coords[1]
            lon = coords[0]
            mag = props["mag"] if api == "usgs" else props["Magnitude"]
            dist_mi = geod.line_length([swd_lon, lon], [swd_lat, lat]) * mi_per_m
            earthquake_distances.append(
                {
                    keys[0]: swd_id,
                    keys[1]: eq_id,
                    keys[2]: time,
                    keys[3]: dist_mi,
                    keys[4]: mag,
                }
            )

    if fmt == "csv":
        with open(save, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(keys)
            for row in earthquake_distances:
                writer.writerow(row.values())
    elif fmt == "xlsx":
        pd.DataFrame(earthquake_distances).to_excel(save, index=None)

    return earthquake_distances


def main():
    # Example
    swd_latlons = [
        {"swd_id": 1, "lat": 32.251, "lon": -101.940},
        {"swd_id": 2, "lat": 31.651, "lon": -104.410},
    ]

    earthquake_distances = calculate_earthquake_distances(
        swd_latlons, "texnet", save="eq_dist_texnet_results.csv", overwrite=True
    )
    earthquake_distances = calculate_earthquake_distances(
        swd_latlons, "texnet", save="eq_dist_texnet_results.xlsx", overwrite=True
    )
    print("# TexNet API\n", json.dumps(earthquake_distances, indent=1))

    earthquake_distances = calculate_earthquake_distances(swd_latlons)
    print("# USGS API\n", json.dumps(earthquake_distances, indent=1))

    earthquake_distances = calculate_earthquake_distances(
        swd_latlons, min_date="2024-03-20"
    )
    print("# USGS API\n", json.dumps(earthquake_distances, indent=1))

    earthquake_distances = calculate_earthquake_distances(
        swd_latlons, max_date="2024-03-20"
    )
    print("# USGS API\n", json.dumps(earthquake_distances, indent=1))

    earthquake_distances = calculate_earthquake_distances(
        swd_latlons, min_date="2024-03-23", max_date="2024-03-23"
    )
    print("# USGS API\n", json.dumps(earthquake_distances, indent=1))


if __name__ == "__main__":
    main()
