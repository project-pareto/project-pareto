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
from importlib import resources
import pytest

from pareto.utilities.get_data import get_data


@pytest.mark.parametrize(
    "file_name",
    [
        "operational_generic_case_study.xlsx",
        "strategic_toy_case_study.xlsx",
        "strategic_treatment_demo.xlsx",
        "strategic_small_case_study.xlsx",
        "strategic_permian_demo.xlsx",
    ],
)
def test_case_studies(file_name: str):
    for mt in ["operational", "strategic"]:
        if file_name.startswith(mt):
            model_type = mt
            break

    with resources.path("pareto.case_studies", file_name) as fpath:
        # changing to raises=True will cause the test to fail on data loading failures
        data = get_data(fpath, model_type=model_type, raises=False)
    assert data is not None
