#####################################################################################################
# PARETO was produced under the DOE Produced Water Application for Beneficial Reuse Environmental
# Impact and Treatment Optimization (PARETO), and is copyright (c) 2021-2023 by the software owners:
# The Regents of the University of California, through Lawrence Berkeley National Laboratory, et al.
# All rights reserved.
#
# NOTICE. This Software was developed under funding from the U.S. Department of Energy and the U.S.
# Government consequently retains certain rights. As such, the U.S. Government has been granted for
# itself and others acting on its behalf a paid-up, nonexclusive, irrevocable, worldwide license in
# the Software to reproduce, distribute copies to the public, prepare derivative works, and perform
# publicly and display publicly, and to permit others to do so.
#####################################################################################################

import pytest
import pyomo.environ as pyo
from importlib import resources
from pareto.utilities.get_data import get_data
from pareto.other_models.CM_module.operational.set_param_list import (
    set_list,
    parameter_list,
)
from pareto.utilities.cm_utils.data_parser import data_parser
from pareto.other_models.Integrate_desal.integrated_models.integrated_optimization_mvr import (
    integrated_model_build,
)

ipopt_avail = pyo.SolverFactory("ipopt").available()


class TestIntegratedOptimizationMvr:
    def test_single_stage_mvr(self):
        with resources.path(
            "pareto.case_studies",
            "integrated_desalination_demo.xlsx",
        ) as fpath:
            [df_sets, df_parameters] = get_data(fpath, set_list, parameter_list)

            data = data_parser(df_sets, df_parameters)
        m = integrated_model_build(network_data=data, treatment_dict={"R01_IN": 1})

        ipopt = pyo.SolverFactory("ipopt")
        res = ipopt.solve(m)
        pyo.assert_optimal_termination(res)

    def test_two_stage_mvr(self):
        with resources.path(
            "pareto.case_studies",
            "integrated_desalination_demo.xlsx",
        ) as fpath:
            [df_sets, df_parameters] = get_data(fpath, set_list, parameter_list)

            data = data_parser(df_sets, df_parameters)
        m = integrated_model_build(network_data=data, treatment_dict={"R01_IN": 2})

        ipopt = pyo.SolverFactory("ipopt")
        res = ipopt.solve(m)
        pyo.assert_optimal_termination(res)


if __name__ == "__main__":
    pytest.main()
