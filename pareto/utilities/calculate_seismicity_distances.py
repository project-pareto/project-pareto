import urllib.request
import urllib.error
import json
import datetime
import pyproj

geod = pyproj.Geod(ellps="WGS84")
mi_per_m = 0.000621371  # mi/m
max_radius_mi = 5.59
min_magnitude = 3

def calculate_seismicity_distances_usgs(swd_latlons):
    # swd_latlons is a list of dicts with id, lat, and lon
    max_radius_km = max_radius_mi / mi_per_m / 1000  # 5.59 mi
    usgs_api_url = ("https://earthquake.usgs.gov/fdsnws/event/1/query" +
        "?format=geojson" +
        "&latitude={lat}" +
        "&longitude={lon}" +
        "&maxradiuskm={max_radius_km}" +
        "&minmagnitude={min_magnitude}" +
        "")

    # only for testing
    max_radius_km = 1000
    min_magnitude = 0.1

    seismicity_distances = []

    for swd_latlon in swd_latlons:
        swd_id = swd_latlon["id"]
        swd_lat = swd_latlon["lat"]
        swd_lon = swd_latlon["lon"]
        url = usgs_api_url.format(
            lat=swd_lat, lon=swd_lon, max_radius_km=max_radius_km, min_magnitude=min_magnitude
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
            mag = props["mag"]
            time = datetime.datetime.fromtimestamp(props["time"]/1000).strftime("%Y-%m-%d %H:%M:%S")
            dist_mi = geod.line_length([swd_lon, lon], [swd_lat, lat]) * mi_per_m
            seismicity_distances.append(
                {
                    "swd_id": swd_id,
                    "eq_id": eq_id,
                    "time": time,
                    "distance_mi": dist_mi,
                    "magnitude": mag,
                }
            )
    return seismicity_distances

def calculate_seismicity_distances_texnet(swd_latlons):
    # swd_latlons is a list of dicts with id, lat, and lon
    texnet_api_url = ("https://maps.texnet.beg.utexas.edu/arcgis/rest/services/catalog/catalog_all/MapServer/0/query" +
        "?f=geojson"
        "&where=Magnitude>={min_magnitude}" +
        "&text=" +
        "&objectIds=" +
        "&time=" +
        "&timeRelation=esriTimeRelationOverlaps" +
        "&geometry={lon},{lat}" +
        "&geometryType=esriGeometryEnvelope" +
        "&inSR=" +
        "&spatialRel=esriSpatialRelWithin" +
        "&distance={max_radius_mi}" +
        "&units=esriSRUnit_StatuteMile" +
        "&relationParam=" +
        "&outFields=*" +
        "&returnGeometry=true" +
        "&returnTrueCurves=false" +
        "&maxAllowableOffset=" +
        "&geometryPrecision=" +
        "&outSR=" +
        "&havingClause=" +
        "&returnIdsOnly=false" +
        "&returnCountOnly=false" +
        "&orderByFields=" +
        "&groupByFieldsForStatistics=" +
        "&outStatistics=" +
        "&returnZ=false" +
        "&returnM=false" +
        "&gdbVersion=" +
        "&historicMoment=" +
        "&returnDistinctValues=false" +
        "&resultOffset=" +
        "&resultRecordCount=" +
        "&returnExtentOnly=false" +
        "&sqlFormat=none" +
        "&datumTransformation=" +
        "&parameterValues=" +
        "&rangeValues=" +
        "&quantizationParameters=" +
        "&featureEncoding=esriDefault" +
        "")

    # only for testing
    max_radius_mi = 1000
    min_magnitude = 0.1

    seismicity_distances = []

    for swd_latlon in swd_latlons:
        swd_id = swd_latlon["id"]
        swd_lat = swd_latlon["lat"]
        swd_lon = swd_latlon["lon"]
        url = texnet_api_url.format(
            lat=swd_lat, lon=swd_lon, max_radius_mi=max_radius_mi, min_magnitude=min_magnitude
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
            mag = props["Magnitude"]
            time = datetime.datetime.fromtimestamp(props["Event_Date"]/1000).strftime("%Y-%m-%d %H:%M:%S")
            dist_mi = geod.line_length([swd_lon, lon], [swd_lat, lat]) * mi_per_m
            seismicity_distances.append(
                {
                    "swd_id": swd_id,
                    "eq_id": eq_id,
                    "time": time,
                    "distance_mi": dist_mi,
                    "magnitude": mag,
                }
            )
    return seismicity_distances


swd_latlons = [
    { "id": 1, "lat": 34, "lon": -106 },
    {"id": 2, "lat": 35, "lon": -105},
]

seismicity_distances = calculate_seismicity_distances_texnet(swd_latlons)

#print(json.dumps(seismicity_distances, indent=1))
