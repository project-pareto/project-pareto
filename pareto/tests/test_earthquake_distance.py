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
"""
Test the earthquake distance calculator
"""
import pytest

# pyproj is only supported for Python 3.9+, so skip this module if we cannot
# import it.
pytest.importorskip("pyproj")

from pareto.utilities.earthquake_distance import calculate_earthquake_distances, main


# calculate_earthquake_distances uses pyproj package, which is only supported
# for Python 3.9 and later
@pytest.mark.unit
def test_earthquake_distance():
    swd_latlons = [
        {"swd_id": 1, "lat": 32.251, "lon": -101.940},
        {"swd_id": 2, "lat": 31.651, "lon": -104.410},
    ]

    # First, call calculate_earthquake_distances without any of the optional
    # keyword arguments to make sure there are no exceptions
    calculate_earthquake_distances(swd_latlons)

    # Ensure that request to USGS database works
    earthquake_distances = calculate_earthquake_distances(
        swd_latlons,
        api="usgs",
        min_date="2023-11-14",
        max_date="2024-04-14", # 5 months
        save="eq_dist_usgs_results.csv",
        overwrite=True,
    )
    assert len(earthquake_distances) >= 1

    # Ensure that request to TexNet database works
    earthquake_distances = calculate_earthquake_distances(
        swd_latlons,
        api="texnet",
        min_date="2024-03-23",
        max_date="2024-03-23",
        save="eq_dist_texnet_results.csv",
        overwrite=True,
    )
    assert len(earthquake_distances) == 2

    # Ensure that xlsx save format works
    earthquake_distances = calculate_earthquake_distances(
        swd_latlons,
        api="texnet",
        min_date="2024-03-23",
        max_date="2024-03-23",
        save="eq_dist_texnet_results.xlsx",
        overwrite=True,
    )

    # Ensure exception when incorrect date format is used
    with pytest.raises(Exception):
        calculate_earthquake_distances(
            swd_latlons,
            min_date="2024.03.23",
            max_date="2024.03.23",
        )

    # Ensure exception when invalid API is used
    with pytest.raises(Exception):
        calculate_earthquake_distances(
            swd_latlons,
            api="usgss",
        )

    # Ensure exception when min_date is later than max_date
    with pytest.raises(Exception):
        calculate_earthquake_distances(
            swd_latlons,
            min_date="2024-03-25",
            max_date="2024-03-23",
        )

    # Ensure exception when incorrect save format is used
    with pytest.raises(Exception):
        calculate_earthquake_distances(
            swd_latlons,
            api="usgs",
            min_date="2024-03-23",
            max_date="2024-03-23",
            save="eq_dist_usgs_results.cs",
            overwrite=True,
        )

    # Ensure exception when overwriting a file and overwrite option is False
    with pytest.raises(Exception):
        calculate_earthquake_distances(
            swd_latlons,
            api="usgs",
            min_date="2024-03-23",
            max_date="2024-03-23",
            save="eq_dist_usgs_results.csv",
            overwrite=False,
        )

    # Check that the main function runs without exception
    main()
