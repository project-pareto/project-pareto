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

###--- Imports ---###
from pyomo.environ import (
    Var,
    Binary,
    units as pyunits,
)
import logging

_log = logging.getLogger(__name__)


###--- Functions ---###
# free variables function
def free_variables(model, exception_list=None, time_period=None):
    for var in model.component_objects(Var):
        if exception_list is not None and var.name in exception_list:
            continue
        else:
            for index in var:
                is_in_time_period = True
                if index is not None and time_period is not None:
                    for i in index:
                        if i in model.s_T and i not in time_period:
                            is_in_time_period = False
                            break
                if not is_in_time_period:
                    continue
                index_var = var if index is None else var[index]
                # unfix binary variables and unbound the continuous variables
                if index_var.domain is Binary:
                    index_var.unfix()
                else:
                    index_var.unfix()
                    index_var.setlb(0)
                    index_var.setub(None)
    return None


# deactivate slacks model
def deactivate_slacks(model):
    model.v_C_Slack.fix(0)
    model.v_S_FracDemand.fix(0)
    model.v_S_Production.fix(0)
    model.v_S_Flowback.fix(0)
    model.v_S_PipelineCapacity.fix(0)
    model.v_S_StorageCapacity.fix(0)
    model.v_S_DisposalCapacity.fix(0)
    model.v_S_TreatmentCapacity.fix(0)
    model.v_S_BeneficialReuseCapacity.fix(0)
    return None


def fix_vars(model, vars_to_fix, indexes, v_val):
    _log.info("inside fix_vars")
    for var in model.component_objects(Var):
        if var.name in vars_to_fix:
            _log.info("\nFixing this variable")
            _log.info(var)
            for index in var:
                if index == indexes:
                    if not var[index].domain is Binary:
                        v_val = pyunits.convert_value(
                            v_val,
                            from_units=model.user_units["volume_time"],
                            to_units=model.model_units["volume_time"],
                        )
                    var[index].fix(v_val)
