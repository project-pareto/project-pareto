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


"""
Base Case Run
Run file which runs any specific CM case study from the case_studies folder
"""

import pyomo.environ as pyo
from pareto.models_extra.CM_module.models.qcp_br import build_qcp_br
from pareto.utilities.get_data import get_data
from pareto.models_extra.CM_module.cm_utils.gen_utils import report_results_to_excel
from pareto.models_extra.CM_module.cm_utils.data_parser import data_parser
from pareto.models_extra.CM_module.cm_utils.run_utils import solving
from importlib import resources


# -------------------------Loading data and model------------------------------
"""
Purpose of each of the files:
CM_large_permian.xlsx: This file is the large permian case study with no TDS concentrations.
CM_small_permian.xlsx: This file is the small permian case study with LI and TDS concentrations.
"""

fname = "CM_small_permian"
with resources.path(
    "pareto.models_extra.CM_module.case_studies",
    "CM_small_permian.xlsx",
) as fpath:
    [df_sets, df_parameters] = get_data(fpath, model_type="critical_mineral")

data = data_parser(df_sets, df_parameters)

# building model
model = build_qcp_br(data)

print(f"\nSolving case study: {fname}")
model, _ = solving(model, tee=True)

print("\nGenerating Report...")
report_results_to_excel(
    model, filename=f"{fname}_operational_results.xlsx", split_var={"s_A": 3}
)
