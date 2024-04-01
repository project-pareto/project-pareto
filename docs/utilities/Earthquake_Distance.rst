Earthquake Distance Function
============================



The following function is used to conveniently acquire earthquake data for subsurface risk analysis.

+--------------------------------+---------------------------------------+
| Function                       | Section                               |
+================================+=======================================+
| calculate_earthquake_distances | :ref:`calculate_earthquake_distances` |
+--------------------------------+---------------------------------------+



.. _calculate_earthquake_distances:

Calculate Earthquake Distances
------------------------------

**Method Description:**

This method uses the `API <https://earthquake.usgs.gov/fdsnws/event/1/>`_ of the USGS `Earthquake Hazards Program <https://www.usgs.gov/programs/earthquake-hazards>`_ and the `RESTful API <https://maps.texnet.beg.utexas.edu/arcgis/rest/services/catalog/catalog_all/MapServer/0/>`_ of the `TexNet Earthquake Catalog <https://www.beg.utexas.edu/texnet-cisr/texnet/earthquake-catalog/>`_ to collect earthquake data and calculate distances from input saltwater disposal (SWD) well coordinates.
The method accepts the following input arguments:

- swd_latlons:
    REQUIRED. Defines a list of dictionaries with a SWD well ID (id), its decimal latitude (lat) and longitude (lon).
    For example::

     [
         {"id": 1, "lat": 32.262, "lon": -101.931},
         {"id": 2, "lat": 31.682, "lon": -104.401},
     ]

    The SWD well IDs will be reported in the output list.

- api:
    OPTIONAL. Specifies either the USGS or TexNet API.

    * ``"usgs"``: Use the USGS API (default)
    * ``"texnet"``: Use the TexNet API

- max_radius_mi:
    OPTIONAL. Specifies the maximum radius in miles from a SWD well for earthquake data collection.
    By default, it is 5.59 miles.

- min_magnitude:
    OPTIONAL. Specifies the minimum earthquake magnitude for earthquake data colleciton.
    By default, it is 3.

- min_date:
    OPTIONAL. Specifies the minimum date in YYYY-MM-DD for earthquake data collection.
    By default, it is None, which indicates no limit.

- max_date:
    OPTIONAL. Specifies the maximum date in YYYY-MM-DD for earthquake data collection.
    By default, it is None, which indicates no limit.

- save:
    OPTIONAL. Specifies an output filename in \*.csv or \*.xlsx.
    If this argument is specified, the output will be saved as a file.
    It only supports the CSV and XLSX formats.
    The XLSX format requires the pandas and openpyxl modules.
    By default, it is None, which means no output file.

- overwrite:
    OPTIONAL. Specifies whether or not to overwrite the save output file.
    If a file given in the save argument exists, passing True to this argument will overwrite the file.
    By default, it is False.

The output of this method is a list of dictionaries containing the input SWD well ID (swd_id), earthquake ID (eq_id), event time (time), distance in miles to the SWD well (distance_mi), and its magnitude (magnitude).
For example::

    [
        {
            "swd_id": 1,
            "eq_id": "tx2024fukh",
            "time": "2024-03-23 01:36:02",
            "distance_mi": 0.9231348790234829,
            "magnitude": 3
        },
        {
            "swd_id": 2,
            "eq_id": "tx2024emvg",
            "time": "2024-03-04 15:31:07",
            "distance_mi": 2.200703681215228,
            "magnitude": 3.3
        }
    ]


**How to Use**

Example of how this method is used::

    swd_latlons = [
        {"id": 1, "lat": 32.251, "lon": -101.940},
        {"id": 2, "lat": 31.651, "lon": -104.410},
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
