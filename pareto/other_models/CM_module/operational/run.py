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
Base Case Run
Run file which runs any specific CM case study from the case_studies folder
"""

import pyomo.environ as pyo
from pareto.other_models.CM_module.models.qcp_br import build_qcp_br
from pareto.utilities.get_data import get_data
from pareto.utilities.cm_utils.gen_utils import report_results_to_excel
from pareto.utilities.cm_utils.data_parser import data_parser
from pareto.utilities.cm_utils.run_utils import solving
from set_param_list import set_list, parameter_list
from importlib import resources


# -------------------------Loading data and model------------------------------
"""
Purpose of each of the files:
large_case_study_Li: This file is the actual final case study with no TDS concentrations. USE THIS CASE STUDY
small_case_study_Li_Arsh: This file is the small case study with LI and TDS concentrations and a concentration requirement.
"""

fname = "small_case_study_Li"
with resources.path(
    "pareto.case_studies",
    "small_case_study_Li.xlsx",
) as fpath:
    [df_sets, df_parameters] = get_data(fpath, set_list, parameter_list)

data = data_parser(df_sets, df_parameters)

# building model
model = build_qcp_br(data)

print(f"\nSolving case study: {fname}")
model, _ = solving(model, tee=True)

print("\nGenerating Report...")
# report_results_to_excel(model, filename=f'{fname}_operational_results.xlsx', split_var={'s_A':3})
