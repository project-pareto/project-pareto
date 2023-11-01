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
# Title: Supporting functions for both Operational and Strategic models

###############################################################################
### Imports
from pareto.strategic_water_management.strategic_produced_water_optimization import (
    WaterQuality,
)
from pyomo.environ import (
    Param,
    value,
    Any,
)


###############################################################################
### Variable bounding manager functions
def VariableBounds(model):
    """
    This function adds bounds to variables in an PARETO existing model object.
    At present, the following variables are included:
        > v_F_Piped
        > v_Q
        > v_F_Trucked (NOTE: this is to be included in a future revision, but requires a change within the PARETO Strategic model code)
    """
    model = Bound_v_F_Piped(model)
    if model.config.water_quality is WaterQuality.post_process:
        model = Bound_v_Q_PP(model)
    elif model.config.water_quality is WaterQuality.discrete:
        model = Bound_v_F_DiscretePiped(model)
        # model = Bound_v_F_Trucked(model) # TODO: resolve unit problem with p_max_number_of_trucks - it must be week^-1 to make the units work out
    elif model.config.water_quality is WaterQuality.false:
        pass
    else:
        pass
    return model


###############################################################################
### Individual variable bound generation functions
def Bound_v_F_Piped(model):
    # initialization function for parameter
    def p_F_Piped_UB_init(model, l, l_tilde):
        if (l, l_tilde) in model.s_LLA:
            if (l_tilde, l) in model.s_LLA:
                # set default value to flow capacity for a bi-directional pipeline
                # Default is Initial capacity in either directions plus twice the maximum expansion capacity to account for bi-directional pipe installation
                return (
                    model.p_sigma_Pipeline[l, l_tilde]
                    + model.p_sigma_Pipeline[l_tilde, l]
                    + 2 * max([value(model.p_delta_Pipeline[d]) for d in model.s_D])
                )
            else:
                # set default value to flow capacity for uni-directional pipeline
                # Default is Initial capacity in the direction plus the maximum expansion capacity
                return model.p_sigma_Pipeline[l, l_tilde] + max(
                    [value(model.p_delta_Pipeline[d]) for d in model.s_D]
                )

    # Set up bounds in a parameter
    model.p_F_Piped_UB = Param(
        model.s_LLA,
        default=None,
        mutable=True,
        within=Any,
        initialize=p_F_Piped_UB_init,
        units=model.model_units["volume_time"],
        doc="Maximum pipeline capacity between nodes [volume_time]",
    )
    # Assign upper bounds to variables; note that using a bounds rule would require redefining the variable
    for key in model.s_LLA:
        model.v_F_Piped[key, :].setub(model.p_F_Piped_UB[key])
    return model


def Bound_v_F_Trucked(model):
    for key in model.s_LLT:
        for t in model.s_T:
            model.v_F_Trucked[key, t].setub(
                model.p_delta_Truck * model.p_max_number_of_trucks
            )
    return model


def Bound_v_Q_PP(model):
    """
    Variable bounding function for water quality variable v_Q in the post
    processing strategic water quality extension

    Notes on contents:
        - uses the maximum value among several parameters at each node as bound
        - not all parameters will be defined on every index
        - "None" is a valid entry for a pyomo variable bound, meaning no bound
        - function "TryOrNone()" is used to return None if a parameter is not
          defined on a given index
        - If no parameter is defined at an index, then use None as that bound
    """
    quality_highest_bound = max(
        max([x.value for x in model.quality.p_xi_StorageSite.values()]),
        max([x.value for x in model.quality.p_xi_PadStorage.values()]),
        max([x.value for x in model.quality.p_nu_pad.values()]),
        max([x.value for x in model.quality.p_nu_freshwater.values()]),
    )

    """
    # Create a parameter with maximum quality values
    model.quality.p_Q_UB = Param(
        model.quality.s_WQL,
        model.s_QC,
        within=Any,
        default=None,
        mutable=True,
        # initialize=p_Q_UB_init,
        units=model.model_units["concentration"],
    )
    """
    # Assign upper bounds to variables
    for l in model.quality.s_WQL:
        for w in model.s_QC:
            for t in model.s_T:
                # Individual quality bounds (NOTE: HAVE SHOWN, THIS DOES NOT WORK)
                # model.quality.v_Q[l, w, t].setub(model.quality.p_Q_UB[l, w])
                # Highest single quality bound
                model.quality.v_Q[l, w, t].setub(quality_highest_bound)
    return model


def TryOrNone(par, ind):
    """
    A helper function that checks if a parameter is defined on an index,
    returning the parameter value if it is, and None if it is not
    """
    try:
        val = value(par[ind])
    except:
        val = None
    finally:
        return val


def Bound_v_F_DiscretePiped(model):
    # initialization function for parameter
    def p_F_DiscretePiped_UB_init(model, l, l_tilde):
        # set default value to pipeline capacity plus maximum expansion capacity
        return model.p_sigma_Pipeline[l, l_tilde] + max(
            [value(model.p_delta_Pipeline[d]) for d in model.s_D]
        )

    # Set up bounds in a parameter
    model.p_F_DiscretePiped_UB = Param(
        model.s_LLA,
        default=None,
        mutable=True,
        within=Any,
        initialize=p_F_DiscretePiped_UB_init,
        units=model.model_units["volume_time"],
        doc="Maximum pipeline capacity between nodes [volume_time]",
    )
    # Assign upper bounds to variables
    for key in model.s_NonPLP:
        for t in model.s_T:
            for w in model.s_QC:
                for q in model.s_Q:
                    model.v_F_DiscretePiped[key, t, w, q].setub(
                        model.p_F_DiscretePiped_UB[key]
                    )
    return model
