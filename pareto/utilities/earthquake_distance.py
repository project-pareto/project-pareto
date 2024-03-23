#####################################################################################################
# PARETO was produced under the DOE Produced Water Application for Beneficial Reuse Environmental
# Impact and Treatment Optimization (PARETO), and is copyright (c) 2021-2024 by the software owners:
# The Regents of the University of California, through Lawrence Berkeley National Laboratory, et al.
# All rights reserved.
#
# NOTICE. This Software was developed under funding from the U.S. Department of Energy and the U.S.
# Government consequently retains certain rights. As such, the U.S. Government has been granted for
# itself and others acting on its behalf a paid-up, nonexclusive, irrevocable, worldwide license in
# the Software to reproduce, distribute copies to the public, prepare derivative works, and perform
# publicly and display publicly, and to permit others to do so.
#####################################################################################################

import urllib.request
import urllib.error
import json
import datetime
import pyproj

geod = pyproj.Geod(ellps="WGS84")
mi_per_m = 0.000621371  # mi/m
max_radius_mi = 5.59
min_magnitude = 3
usgs_api_url = (
    "https://earthquake.usgs.gov/fdsnws/event/1/query"
    + "?format=geojson"
    + "&latitude={lat}"
    + "&longitude={lon}"
    + "&maxradiuskm={max_radius_km}"
    + "&minmagnitude={min_magnitude}"
    + ""
)
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


def calculate_earthquake_distances(swd_latlons, api="usgs"):
    # swd_latlons is a list of dicts with id, lat, and lon
    if api not in ("usgs", "texnet"):
        raise "api must be either usgs or texnet"

    earthquake_distances = []

    for swd_latlon in swd_latlons:
        swd_id = swd_latlon["id"]
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
            raise
        for feat in response["features"]:
            eq_id = feat["id"]
            props = feat["properties"]
            coords = feat["geometry"]["coordinates"]

            lat = coords[1]
            lon = coords[0]
            mag = props["mag"] if api == "usgs" else props["Magnitude"]
            time = datetime.datetime.fromtimestamp(
                (props["time"] if api == "usgs" else props["Event_Date"]) / 1000
            ).strftime("%Y-%m-%d %H:%M:%S")
            dist_mi = geod.line_length([swd_lon, lon], [swd_lat, lat]) * mi_per_m
            earthquake_distances.append(
                {
                    "swd_id": swd_id,
                    "eq_id": eq_id,
                    "time": time,
                    "distance_mi": dist_mi,
                    "magnitude": mag,
                }
            )

    return earthquake_distances


if __name__ == "__main__":
    # Example
    swd_latlons = [
        {"id": 1, "lat": 32.262, "lon": -101.931},
        {"id": 2, "lat": 31.682, "lon": -104.401},
    ]

    earthquake_distances = calculate_earthquake_distances(swd_latlons, "texnet")
    print("# TexNet API\n", json.dumps(earthquake_distances, indent=1))

    earthquake_distances = calculate_earthquake_distances(swd_latlons)
    print("# USGS API\n", json.dumps(earthquake_distances, indent=1))
