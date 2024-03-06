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


import pyomo.environ as pyo
from importlib import resources
import pytest

from pareto.CM_module.models.qcp_br import build_qcp_br
from pareto.CM_module.operational.set_param_list import set_list, parameter_list

from pareto.utilities.cm_utils.data_parser import data_parser
from pareto.utilities.get_data import get_data


class TestCMqcpModel:
    def build_cm_qcp_model(self):
        """
        Building critical mineral qcp model to run on the Li small case study
        """

        with resources.path(
            "pareto.case_studies",
            "small_case_study_Li_Arsh.xlsx",
        ) as fpath:
            [df_sets, df_parameters] = get_data(fpath, set_list, parameter_list)

            data = data_parser(df_sets, df_parameters)

            # building model
            model = build_qcp_br(data)

            return model

    def test_model_data(self):
        """
        The correct objective value must be active
        """
        model = self.build_cm_qcp_model()

        assert model.br_obj.active  # correct objective function is active
        assert not model.obj.active

        assert model.p_Cmin["R01_CW", "Li"].value == 100  # minimum lithium req is 100

    def test_small_case_study(self):
        model = self.build_cm_qcp_model()

        solver = "ipopt"
        opt = pyo.SolverFactory(solver)
        assert opt.available()

        status = opt.solve(model, tee=False)
        pyo.assert_optimal_termination(status)


if __name__ == "__main__":
    pytest.main()
