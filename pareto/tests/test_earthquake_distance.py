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

from pareto.utilities.earthquake_distance import calculate_earthquake_distances


def test_earthquake_distance():
    swd_latlons = [
        {"id": 1, "lat": 32.251, "lon": -101.940},
        {"id": 2, "lat": 31.651, "lon": -104.410},
    ]

    earthquake_distances = calculate_earthquake_distances(
        swd_latlons, min_date="2024-03-23", max_date="2024-03-23"
    )

    assert len(earthquake_distances) == 1

    earthquake_distances = calculate_earthquake_distances(
        swd_latlons, "texnet", min_date="2024-03-23", max_date="2024-03-23"
    )

    assert len(earthquake_distances) == 2


if __name__ == "__main__":
    test_earthquake_distance()
