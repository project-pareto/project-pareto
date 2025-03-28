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
# Title: STRATEGIC Produced Water Optimization Model

# Import
import math
from cmath import nan
import numpy as np
import os
import re


from pyomo.environ import (
    Var,
    Param,
    Set,
    ConcreteModel,
    Expression,
    Constraint,
    Objective,
    minimize,
    maximize,
    NonNegativeReals,
    Reals,
    Binary,
    Any,
    units as pyunits,
    Block,
    Suffix,
    TransformationFactory,
    value,
    SolverFactory,
)
from pyomo.common.fileutils import this_file_dir

from pyomo.core.base.constraint import simple_constraint_rule

from pyomo.common.config import ConfigBlock, ConfigValue, In, Bool

from pareto.utilities.solvers import get_solver, set_timeout
from pyomo.opt import TerminationCondition
from pathlib import Path

from pareto.utilities.process_data import (
    check_required_data,
    model_infeasibility_detection,
)
from pareto.utilities.units_support import units_setup
from pareto.utilities.build_utils import (
    build_sets,
    build_common_params,
    build_common_vars,
    build_common_constraints,
    process_constraint,
)
from pareto.utilities.enums import (
    Objectives,
    PipelineCapacity,
    PipelineCost,
    WaterQuality,
    Hydraulics,
    RemovalEfficiencyMethod,
    TreatmentStreams,
    InfrastructureTiming,
    SubsurfaceRisk,
    DesalinationModel,
)


# create config dictionary
CONFIG = ConfigBlock()

CONFIG.declare(
    "objective",
    ConfigValue(
        default=Objectives.cost,
        domain=In(Objectives),
        description="alternate objectives selection",
        doc="Alternate objective functions (i.e., minimize cost, maximize reuse, minimize environmental impact)",
    ),
)

CONFIG.declare(
    "pipeline_capacity",
    ConfigValue(
        default=PipelineCapacity.input,
        domain=In(PipelineCapacity),
        description="alternate pipeline capacity selection",
        doc="""Alternate pipeline capacity selection (calculated or input)
        ***default*** - PipelineCapacity.input
        **Valid Values:** - {
        **PipelineCapacity.input** - use input for pipeline capacity,
        **PipelineCapacity.calculated** - calculate pipeline capacity from pipeline diameters
        }""",
    ),
)

CONFIG.declare(
    "hydraulics",
    ConfigValue(
        default=Hydraulics.false,
        domain=In(Hydraulics),
        description="add hydraulics constraints",
        doc="""option to include pipeline hydraulics in the model either during or post optimization
        ***default*** - Hydraulics.false
        **Valid Values:** - {
        **Hydraulics.false** - does not add hydraulics feature
        **Hydraulics.post_process** - adds economic parameters for flow based on elevation changes and computes pressures at each node post-optimization,
        **Hydraulics.co_optimize** - re-solves the problem using an MINLP formulation to simulatenuosly optimize pressures and flows,
        **Hydraulics.co_optimize_linearized** - a linearized approximation of the co-optimization model,
        }""",
    ),
)

CONFIG.declare(
    "pipeline_cost",
    ConfigValue(
        default=PipelineCost.capacity_based,
        domain=In(PipelineCost),
        description="alternate pipeline cost selection",
        doc="""Alternate pipeline capex cost structures (distance or capacity based)
        ***default*** - PipelineCost.capacity_based
        **Valid Values:** - {
        **PipelineCost.capacity_based** - use pipeline capacities and rate in [currency/volume] to calculate pipeline capex costs,
        **PipelineCost.distance_based** - use pipeline distances and rate in [currency/(diameter-distance)] to calculate pipeline capex costs
        }""",
    ),
)

CONFIG.declare(
    "node_capacity",
    ConfigValue(
        default=True,
        domain=Bool,
        description="Node Capacity",
        doc="""Selection to include Node Capacity
        ***default*** - True
        **Valid Values:** - {
        **True** - Include network node capacity constraints,
        **False** - Exclude network node capacity constraints
        }""",
    ),
)

CONFIG.declare(
    "desalination_model",
    ConfigValue(
        default=DesalinationModel.false,
        domain=In(DesalinationModel),
        description="Desalination Model",
        doc="""Selection to include Desalination Model
        ***default*** - DesalinationModel.false
        **Valid Values:** - {
        **DesalinationModel.false** - Exclude surrogate constraints for desalination model,
        **DesalinationModel.mvc** - Include surrogate constraints for MVC (Mechanical Vapor Compressor) desalination model,
        **DesalinationModel.md** - Include surrogate constraints for MD (Membrane Distillation) desalination model,
        }""",
    ),
)

CONFIG.declare(
    "water_quality",
    ConfigValue(
        default=WaterQuality.post_process,
        domain=In(WaterQuality),
        description="Water quality",
        doc="""Selection to include water quality
        ***default*** - WaterQuality.post_process
        **Valid Values:** - {
        **WaterQuality.false** - Exclude water quality from model,
        **WaterQuality.post_process** - Include water quality as post process
        **WaterQuality.discrete** - Include water quality as discrete values in model
        }""",
    ),
)

CONFIG.declare(
    "removal_efficiency_method",
    ConfigValue(
        default=RemovalEfficiencyMethod.concentration_based,
        domain=In(RemovalEfficiencyMethod),
        description="Removal efficiency calculation method",
        doc="""Method for calculating removal efficiency (load or concentration based).
        ***default*** - RemovalEfficiencyMethod.concentration_based
        **Valid Values:** - {
        **RemovalEfficiencyMethod.load_based** - use contaminant load (flow times concentration) to calculate removal efficiency,
        **RemovalEfficiencyMethod.concentration_based** - use contaminant concentration to calculate removal efficiency
        }""",
    ),
)

CONFIG.declare(
    "infrastructure_timing",
    ConfigValue(
        default=InfrastructureTiming.false,
        domain=In(InfrastructureTiming),
        description="Infrastructure timing",
        doc="""Selection to include infrastructure timing.
        ***default*** - InfrastructureTiming.false
        **Valid Values:** - {
        **InfrastructureTiming.false** - Exclude infrastructure timing from model,
        **InfrastructureTiming.true** - Include infrastructure timing in model
        }""",
    ),
)

CONFIG.declare(
    "subsurface_risk",
    ConfigValue(
        default=SubsurfaceRisk.false,
        domain=In(SubsurfaceRisk),
        description="Subsurface risk",
        doc="""Selection to include subsurface risk.
        ***default*** - SubsurfaceRisk.false
        **Valid Values:** - {
        **SubsurfaceRisk.false** - Exclude subsurface risk from model (unless the subsurface risk objective function is selected),
        **SubsurfaceRisk.exclude_over_and_under_pressured_wells** - Calculate subsurface risk metrics and disallow disposal to overpressured and underpressured wells,
        **SubsurfaceRisk.calculate_risk_metrics** - Calculate subsurface risk metrics for the user to view, but don't change the optimization model
        }""",
    ),
)


def create_model(df_sets, df_parameters, default={}):
    model = ConcreteModel()

    # import config dictionary
    model.config = CONFIG(default)
    model.type = "strategic"

    # check that input data contains required data
    model.df_sets, model.df_parameters = check_required_data(
        df_sets, df_parameters, model.config
    )

    # Setup units for model
    units_setup(model)

    model.proprietary_data = df_parameters["proprietary_data"][0]

    # Pre-process Data #
    _preprocess_data(model)

    # Build sets #
    build_sets(model)

    # Build parameters #
    build_common_params(model)

    model.p_chi_OutsideCompletionsPad = Param(
        model.s_CP,
        initialize=model.df_parameters["CompletionsPadOutsideSystem"],
        default=0,
        doc="Binary parameter designating the Completion Pads that are outside the system",
    )
    model.p_chi_DesalinationTechnology = Param(
        model.s_WT,
        initialize=model.df_parameters["DesalinationTechnologies"],
        doc="Binary parameter designating the treatment technologies for Desalination",
    )
    model.p_chi_DesalinationSites = Param(
        model.s_R,
        initialize=model.df_parameters["DesalinationSites"],
        doc="Binary parameter designating which treatment sites are for desalination (1) and which are not (0)",
    )

    model.p_alpha_AnnualizationRate = Param(
        default=1,
        initialize=model.df_parameters["AnnualizationRate"],
        mutable=True,
        doc="Annualization rate [%]",
    )

    model.p_beta_TotalProd = Param(
        default=0,
        initialize=sum(
            sum(
                model.p_beta_Production[p, t] + model.p_beta_Flowback[p, t]
                for p in model.s_P
            )
            for t in model.s_T
        ),
        units=model.model_units["volume"],
        doc="Combined water supply forecast (flowback & production) over the planning horizon [volume]",
        mutable=True,
    )
    model.p_sigma_BeneficialReuseMinimum = Param(
        model.s_O,
        model.s_T,
        default=0,
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["volume_time"],
                to_units=model.model_units["volume_time"],
            )
            for key, value in model.df_parameters["ReuseMinimum"].items()
        },
        units=model.model_units["volume_time"],
        doc="Minimum flow that must be sent to beneficial reuse option [volume/time]",
    )
    model.p_sigma_BeneficialReuse = Param(
        model.s_O,
        model.s_T,
        # Use a negative number for default so later we can detect for which indexes the user did/did not provide a parameter value
        default=-1,
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["volume_time"],
                to_units=model.model_units["volume_time"],
            )
            for key, value in model.df_parameters["ReuseCapacity"].items()
        },
        units=model.model_units["volume_time"],
        doc="Capacity of beneficial reuse option [volume/time]",
    )

    if model.config.node_capacity == True:
        model.p_sigma_NetworkNode = Param(
            model.s_N,
            default=nan,
            within=Any,
            initialize={
                key: pyunits.convert_value(
                    value,
                    from_units=model.user_units["volume_time"],
                    to_units=model.model_units["volume_time"],
                )
                for key, value in df_parameters["NodeCapacities"].items()
            },
            units=model.model_units["volume_time"],
            doc="Capacity per network node [volume/time]",
        )

    model.p_epsilon_TreatmentRemoval = Param(
        model.s_R,
        model.s_WT,
        model.s_QC,
        default=0,
        initialize=model.df_parameters["RemovalEfficiency"],
        mutable=True,
        doc="Removal efficiency [%]",
    )
    # Note PipelineCapacityIncrements_Calculated is set in _pre_process. These values are already in model units, they
    # do not need to be calculated
    if model.config.pipeline_capacity == PipelineCapacity.calculated:
        model.p_delta_Pipeline = Param(
            model.s_D,
            default=0,
            initialize=model.df_parameters["PipelineCapacityIncrements_Calculated"],
            units=model.model_units["volume_time"],
            doc="Pipeline capacity installation/expansion increments [volume/time]",
        )
    elif model.config.pipeline_capacity == PipelineCapacity.input:
        model.p_delta_Pipeline = Param(
            model.s_D,
            default=0,
            initialize={
                key: pyunits.convert_value(
                    value,
                    from_units=model.user_units["volume_time"],
                    to_units=model.model_units["volume_time"],
                )
                for key, value in model.df_parameters[
                    "PipelineCapacityIncrements"
                ].items()
            },
            units=model.model_units["volume_time"],
            doc="Pipeline capacity installation/expansion increments [volume/time]",
        )
    model.p_delta_Disposal = Param(
        model.s_K,
        model.s_I,
        default=pyunits.convert_value(
            10,
            from_units=pyunits.oil_bbl / pyunits.week,
            to_units=model.model_units["volume_time"],
        ),
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["volume_time"],
                to_units=model.model_units["volume_time"],
            )
            for key, value in model.df_parameters["DisposalCapacityIncrements"].items()
        },
        units=model.model_units["volume_time"],
        doc="Disposal capacity installation/expansion increments [volume/time]",
    )
    model.p_delta_Storage = Param(
        model.s_C,
        default=pyunits.convert_value(
            10,
            from_units=pyunits.oil_bbl,
            to_units=model.model_units["volume"],
        ),
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["volume"],
                to_units=model.model_units["volume"],
            )
            for key, value in model.df_parameters["StorageCapacityIncrements"].items()
        },
        units=model.model_units["volume"],
        doc="Storage capacity installation/expansion increments [volume]",
    )
    model.p_delta_Treatment = Param(
        model.s_WT,
        model.s_J,
        default=pyunits.convert_value(
            10,
            from_units=pyunits.oil_bbl / pyunits.week,
            to_units=model.model_units["volume_time"],
        ),
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["volume_time"],
                to_units=model.model_units["volume_time"],
            )
            for key, value in model.df_parameters["TreatmentCapacityIncrements"].items()
        },
        units=model.model_units["volume_time"],
        doc="Treatment capacity installation/expansion increments [volume/time]",
    )
    model.p_theta_Storage = Param(
        model.s_S,
        default=0,
        units=model.model_units["volume"],
        doc="Terminal storage level at storage site [volume]",
    )
    PipelineExpansionDistance_convert_to_model = {
        key: pyunits.convert_value(
            value,
            from_units=model.user_units["distance"],
            to_units=model.model_units["distance"],
        )
        for key, value in model.df_parameters["PipelineExpansionDistance"].items()
    }
    model.p_lambda_Pipeline = Param(
        model.s_L,
        model.s_L,
        default=(
            max(PipelineExpansionDistance_convert_to_model.values()) * 100
            if PipelineExpansionDistance_convert_to_model
            else pyunits.convert_value(
                10000, from_units=pyunits.miles, to_units=model.model_units["distance"]
            )
        ),
        initialize=PipelineExpansionDistance_convert_to_model,
        units=model.model_units["distance"],
        doc="Pipeline segment length [distance]",
    )
    model.p_kappa_Disposal = Param(
        model.s_K,
        model.s_I,
        default=pyunits.convert_value(
            20,
            from_units=pyunits.USD / (pyunits.oil_bbl / pyunits.day),
            to_units=model.model_units["currency_volume_time"],
        ),
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["currency_volume_time"],
                to_units=model.model_units["currency_volume_time"],
            )
            for key, value in model.df_parameters["DisposalExpansionCost"].items()
        },
        units=model.model_units["currency_volume_time"],
        doc="Disposal construction/expansion capital cost for selected increment [currency/(volume/time)]",
    )
    model.p_kappa_Storage = Param(
        model.s_S,
        model.s_C,
        default=pyunits.convert_value(
            0.1,
            from_units=pyunits.USD / pyunits.oil_bbl,
            to_units=model.model_units["currency_volume"],
        ),
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["currency_volume"],
                to_units=model.model_units["currency_volume"],
            )
            for key, value in model.df_parameters["StorageExpansionCost"].items()
        },
        units=model.model_units["currency_volume"],
        doc="Storage construction/expansion capital cost for selected increment [currency/volume]",
    )
    model.p_kappa_Treatment = Param(
        model.s_R,
        model.s_WT,
        model.s_J,
        default=pyunits.convert_value(
            10,
            from_units=pyunits.USD / (pyunits.oil_bbl / pyunits.day),
            to_units=model.model_units["currency_volume_time"],
        ),
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["currency_volume_time"],
                to_units=model.model_units["currency_volume_time"],
            )
            for key, value in model.df_parameters["TreatmentExpansionCost"].items()
        },
        units=model.model_units["currency_volume_time"],
        doc="Treatment construction/expansion capital cost for selected increment [currency/(volume/time)]",
    )

    if model.config.infrastructure_timing == InfrastructureTiming.true:
        model.p_tau_Disposal = Param(
            model.s_K,
            default=pyunits.convert_value(
                12, from_units=pyunits.week, to_units=model.decision_period
            ),
            units=model.decision_period,
            doc="Disposal construction/expansion lead time [time]",
        )

        model.p_tau_Storage = Param(
            model.s_S,
            default=pyunits.convert_value(
                12, from_units=pyunits.week, to_units=model.decision_period
            ),
            units=model.decision_period,
            doc="Storage construction/expansion lead time [time]",
        )

        model.p_tau_Pipeline = Param(
            model.s_L,
            model.s_L,
            default=pyunits.convert_value(
                12, from_units=pyunits.week, to_units=model.decision_period
            ),
            units=model.decision_period,
            doc="Pipeline construction/expansion lead time [time]",
        )

        model.p_tau_TreatmentExpansionLeadTime = Param(
            model.s_R,
            model.s_WT,
            model.s_J,
            default=0,
            # input units are already model units (decision period), so do not need to be converted
            initialize=model.df_parameters["TreatmentExpansionLeadTime"],
            units=model.model_units["time"],
            doc="Treatment construction/expansion lead time for selected site, treatment type, and size [time]",
        )

        model.p_tau_DisposalExpansionLeadTime = Param(
            model.s_K,
            model.s_I,
            default=0,
            # input units are already model units (decision period), so do not need to be converted
            initialize=model.df_parameters["DisposalExpansionLeadTime"],
            units=model.model_units["time"],
            doc="Disposal construction/expansion lead time for selected site and size [time]",
        )

        model.p_tau_StorageExpansionLeadTime = Param(
            model.s_S,
            model.s_C,
            default=0,
            # input units are already model units (decision period), so do not need to be converted
            initialize=model.df_parameters["StorageExpansionLeadTime"],
            units=model.model_units["time"],
            doc="Storage construction/expansion lead time for selected site and size [time]",
        )

        if model.config.pipeline_cost == PipelineCost.distance_based:
            model.p_tau_PipelineExpansionLeadTime = Param(
                default=0,
                # distance units need to be converted
                initialize=pyunits.convert_value(
                    model.df_parameters["PipelineExpansionLeadTime_Dist"][
                        "pipeline_expansion_lead_time"
                    ],
                    from_units=model.model_units["time"] / model.user_units["distance"],
                    to_units=model.model_units["time"] / model.model_units["distance"],
                ),
                units=model.model_units["time"] / model.model_units["distance"],
                doc="Pipeline construction/expansion lead time [time/distance]",
            )
        elif model.config.pipeline_cost == PipelineCost.capacity_based:
            model.p_tau_PipelineExpansionLeadTime = Param(
                model.s_L,
                model.s_L,
                model.s_D,
                default=0,
                # input units are already model units (decision period), so do not need to be converted
                initialize=model.df_parameters["PipelineExpansionLeadTime_Capac"],
                units=model.model_units["time"],
                doc="Pipeline construction/expansion lead time [time]",
            )

    model.p_omega_EvaporationRate = Param(
        default=pyunits.convert_value(
            3000,
            from_units=pyunits.oil_bbl / pyunits.day,
            to_units=model.model_units["volume_time"],
        ),
        units=model.model_units["volume_time"],
        doc="Evaporation rate [volume/time]",
    )

    if model.config.pipeline_cost == PipelineCost.distance_based:
        model.p_kappa_Pipeline = Param(
            default=pyunits.convert_value(
                120000,
                from_units=pyunits.USD / (pyunits.inch * pyunits.mile),
                to_units=model.model_units["pipe_cost_distance"],
            ),
            initialize=pyunits.convert_value(
                model.df_parameters["PipelineCapexDistanceBased"][
                    "pipeline_expansion_cost"
                ],
                from_units=model.user_units["pipe_cost_distance"],
                to_units=model.model_units["pipe_cost_distance"],
            ),
            units=model.model_units["pipe_cost_distance"],
            doc="Pipeline construction/expansion capital cost for selected increment [[currency/(diameter-distance)]",
        )
        model.p_mu_Pipeline = Param(
            model.s_D,
            default=0,
            initialize={
                key: pyunits.convert_value(
                    value,
                    from_units=model.user_units["diameter"],
                    to_units=model.model_units["diameter"],
                )
                for key, value in model.df_parameters["PipelineDiameterValues"].items()
            },
            units=model.model_units["diameter"],
            doc="Pipeline capacity installation/expansion increments [diameter]",
        )
    elif model.config.pipeline_cost == PipelineCost.capacity_based:
        model.p_kappa_Pipeline = Param(
            model.s_L,
            model.s_L,
            model.s_D,
            default=pyunits.convert_value(
                30,
                from_units=pyunits.USD / (pyunits.oil_bbl / pyunits.day),
                to_units=model.model_units["pipe_cost_capacity"],
            ),
            initialize={
                key: pyunits.convert_value(
                    value,
                    from_units=model.user_units["pipe_cost_capacity"],
                    to_units=model.model_units["pipe_cost_capacity"],
                )
                for key, value in model.df_parameters[
                    "PipelineCapexCapacityBased"
                ].items()
            },
            units=model.model_units["pipe_cost_capacity"],
            doc="Pipeline construction/expansion capital cost for selected increment [currency/volume/time]",
        )

    model.p_pi_BeneficialReuse = Param(
        model.s_O,
        default=pyunits.convert_value(
            0.0,
            from_units=pyunits.USD / pyunits.oil_bbl,
            to_units=model.model_units["currency_volume"],
        ),
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["currency_volume"],
                to_units=model.model_units["currency_volume"],
            )
            for key, value in model.df_parameters["BeneficialReuseCost"].items()
        },
        units=model.model_units["currency_volume"],
        doc="Processing cost for sending water to beneficial reuse [currency/volume]",
    )
    model.p_rho_BeneficialReuse = Param(
        model.s_O,
        default=pyunits.convert_value(
            0.0,
            from_units=pyunits.USD / pyunits.oil_bbl,
            to_units=model.model_units["currency_volume"],
        ),
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["currency_volume"],
                to_units=model.model_units["currency_volume"],
            )
            for key, value in model.df_parameters["BeneficialReuseCredit"].items()
        },
        units=model.model_units["currency_volume"],
        doc="Credit for sending water to beneficial reuse [currency/volume]",
    )

    model.p_M_Concentration = Param(
        default=100,
        units=model.model_units["concentration"],
        doc="Big-M concentration parameter [concentration]",
    )

    model.p_M_Flow_Conc = Param(
        initialize=model.p_M_Concentration * model.p_M_Flow,
        units=model.model_units["concentration"] * model.model_units["volume_time"],
        doc="Big-M flow-concentration parameter [concentration*volume/time]",
    )

    model.p_chi_DisposalExpansionAllowed = Param(
        model.s_K,
        default=0,
        # If initial capacity > 0, then DisposalExpansionAllowed is 0
        initialize={
            key: 0 if value and value > 0 else 1
            for key, value in model.df_parameters["InitialDisposalCapacity"].items()
        },
        mutable=True,
        doc="Indicates if Expansion is allowed at site k",
    )

    model.p_epsilon_DisposalOperatingCapacity = Param(
        model.s_K,
        model.s_T,
        default=1,
        initialize=model.df_parameters["DisposalOperatingCapacity"],
        mutable=True,
        doc="Operating capacity of disposal site [%]",
    )

    model.p_eta_TruckingEmissionsCoefficient = Param(
        model.s_AC,
        default=0,
        initialize={
            a: pyunits.convert_value(
                model.df_parameters["AirEmissionCoefficients"][(label, a)],
                from_units=model.user_units["mass"],
                to_units=model.model_units["mass"],
            )
            for (label, a) in model.df_parameters["AirEmissionCoefficients"]
            if "Trucking" in label
        },
        units=model.model_units[
            "mass"
        ],  # Note: Hours are not modeled as a separate unit (see p_pi_Trucking)
        mutable=True,
        doc="Air emissions trucking coefficients [mass/driving hour]",
    )

    model.p_eta_PipelineOperationsEmissionsCoefficient = Param(
        model.s_AC,
        default=0,
        initialize={
            a: pyunits.convert_value(
                model.df_parameters["AirEmissionCoefficients"][(label, a)],
                from_units=model.user_units["mass"]
                / model.user_units["volume"]
                / model.user_units["distance"],
                to_units=model.model_units["mass"]
                / model.model_units["volume"]
                / model.model_units["distance"],
            )
            for (label, a) in model.df_parameters["AirEmissionCoefficients"]
            if "Pipeline Operations" in label
        },
        units=model.model_units["mass"]
        / model.model_units["volume"]
        / model.model_units["distance"],
        mutable=True,
        doc="Air emissions pipeline operations coefficients [mass/(volume*distance)]",
    )

    model.p_eta_PipelineInstallationEmissionsCoefficient = Param(
        model.s_AC,
        default=0,
        initialize={
            a: pyunits.convert_value(
                model.df_parameters["AirEmissionCoefficients"][(label, a)],
                from_units=model.user_units["mass"] / model.user_units["distance"],
                to_units=model.model_units["mass"] / model.model_units["distance"],
            )
            for (label, a) in model.df_parameters["AirEmissionCoefficients"]
            if "Pipeline Installation" in label
        },
        units=model.model_units["mass"] / model.model_units["distance"],
        mutable=True,
        doc="Air emissions pipeline installation coefficients [mass/distance]",
    )

    model.p_eta_DisposalEmissionsCoefficient = Param(
        model.s_AC,
        default=0,
        initialize={
            a: pyunits.convert_value(
                model.df_parameters["AirEmissionCoefficients"][(label, a)],
                from_units=model.user_units["mass"] / model.user_units["volume"],
                to_units=model.model_units["mass"] / model.model_units["volume"],
            )
            for (label, a) in model.df_parameters["AirEmissionCoefficients"]
            if "Disposal" in label
        },
        units=model.model_units["mass"] / model.model_units["volume"],
        mutable=True,
        doc="Air emissions disposal coefficients [mass/volume]",
    )

    model.p_eta_StorageEmissionsCoefficient = Param(
        model.s_AC,
        default=0,
        initialize={
            a: pyunits.convert_value(
                model.df_parameters["AirEmissionCoefficients"][(label, a)],
                from_units=model.user_units["mass"]
                / model.user_units["volume"]
                / model.user_units["time"],
                to_units=model.model_units["mass"]
                / model.model_units["volume"]
                / model.model_units["time"],
            )
            for (label, a) in model.df_parameters["AirEmissionCoefficients"]
            if "Storage" in label
        },
        units=model.model_units["mass"]
        / model.model_units["volume"]
        / model.model_units["time"],
        mutable=True,
        doc="Air emissions storage coefficients [mass/(volume*time)]",
    )
    model.p_eta_TreatmentEmissionsCoefficient = Param(
        model.s_WT,
        model.s_AC,
        default=0,
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["mass"] / model.user_units["volume"],
                to_units=model.model_units["mass"] / model.model_units["volume"],
            )
            for key, value in model.df_parameters[
                "TreatmentEmissionCoefficients"
            ].items()
        },
        units=model.model_units["mass"] / model.model_units["volume"],
        mutable=True,
        doc="Air emissions treatment technology coefficients [mass/volume]",
    )

    # Build variables #
    build_common_vars(model)

    model.v_F_StorageEvaporationStream = Var(
        model.s_S,
        model.s_T,
        initialize=0,
        within=NonNegativeReals,
        units=model.model_units["volume_time"],
        doc="Water at storage lost to evaporation [bbl/week]",
    )

    model.v_F_TreatmentFeed = Var(
        model.s_R,
        model.s_T,
        within=NonNegativeReals,
        units=model.model_units["volume_time"],
        doc="Flow of feed to a treatment site [volume/time]",
    )

    model.v_F_TreatmentFeedTech = Var(
        model.s_R,
        model.s_WT,
        model.s_T,
        within=NonNegativeReals,
        units=model.model_units["volume_time"],
        doc="Flow of feed to a treatment site indexed by treatment technology [volume/time]",
    )

    model.v_F_ResidualWater = Var(
        model.s_R,
        model.s_T,
        within=NonNegativeReals,
        units=model.model_units["volume_time"],
        doc="Flow of residual out at a treatment site [volume/time]",
    )

    model.v_F_TreatedWater = Var(
        model.s_R,
        model.s_T,
        within=NonNegativeReals,
        units=model.model_units["volume_time"],
        doc="Flow of treated water out at a treatment site [volume/time]",
    )

    model.v_F_TotalTrucked = Var(
        within=NonNegativeReals,
        units=model.model_units["volume"],
        doc="Total volume water trucked [volume]",
    )

    model.v_F_TotalDisposed = Var(
        within=NonNegativeReals,
        units=model.model_units["volume"],
        doc="Total volume of water disposed [volume]",
    )

    model.v_F_TotalReused = Var(
        within=NonNegativeReals,
        units=model.model_units["volume"],
        doc="Total volume of produced water reused at completions [volume]",
    )

    model.v_F_TotalBeneficialReuse = Var(
        within=NonNegativeReals,
        units=model.model_units["volume"],
        doc="Total volume of water beneficially reused [volume]",
    )

    model.v_C_DisposalCapEx = Var(
        within=NonNegativeReals,
        units=model.model_units["currency"],
        doc="Capital cost of constructing or expanding disposal capacity [currency]",
    )

    model.v_C_PipelineCapEx = Var(
        within=NonNegativeReals,
        units=model.model_units["currency"],
        doc="Capital cost of constructing or expanding piping capacity [currency]",
    )

    model.v_C_StorageCapEx = Var(
        within=NonNegativeReals,
        units=model.model_units["currency"],
        doc="Capital cost of constructing or expanding storage capacity [currency]",
    )

    model.v_C_BeneficialReuse = Var(
        model.s_O,
        model.s_T,
        initialize=0,
        within=NonNegativeReals,
        units=model.model_units["currency_time"],
        doc="Processing cost of sending water to beneficial reuse [currency/time]",
    )

    model.v_R_BeneficialReuse = Var(
        model.s_O,
        model.s_T,
        initialize=0,
        within=NonNegativeReals,
        units=model.model_units["currency_time"],
        doc="Credit for sending water to beneficial reuse [currency/time]",
    )

    model.v_C_TotalBeneficialReuse = Var(
        within=NonNegativeReals,
        units=model.model_units["currency"],
        doc="Total processing cost for sending water to beneficial reuse [currency]",
    )

    model.v_R_TotalBeneficialReuse = Var(
        within=NonNegativeReals,
        units=model.model_units["currency"],
        doc="Total credit for sending water to beneficial reuse [currency]",
    )

    model.v_F_CompletionsDestination = Var(
        model.s_CP,
        model.s_T,
        within=NonNegativeReals,
        units=model.model_units["volume_time"],
        doc="Total deliveries to completions pad that meet completions demand [volume/time]",
    )

    model.v_T_Capacity = Var(
        model.s_R,
        within=NonNegativeReals,
        units=model.model_units["volume_time"],
        doc="Treatment capacity at a treatment site [volume/time]",
    )

    # If p_chi_DesalinationSites was not specified for one or more r, raise an
    # Exception
    missing_desal_sites = []
    for r in model.s_R:
        if r not in model.p_chi_DesalinationSites:
            missing_desal_sites.append(r)
    if missing_desal_sites:
        raise Exception(
            'The parameter chi_DesalinationSites (spreadsheet tab "DesalinationSites") must be specified for every treatment site (missing: '
            + ", ".join(missing_desal_sites)
            + ")"
        )

    model.v_C_TreatmentCapEx = Var(
        within=NonNegativeReals,
        units=model.model_units["currency"],
        doc="Capital cost of constructing or expanding treatment capacity [currency]",
    )

    # Binary variables
    model.vb_y_Pipeline = Var(
        model.s_L,
        model.s_L,
        model.s_D,
        within=Binary,
        initialize=0,
        doc="New pipeline installed between one location and another location with specific diameter",
    )

    model.vb_y_Storage = Var(
        model.s_S,
        model.s_C,
        within=Binary,
        initialize=0,
        doc="New or additional storage capacity installed at storage site with specific storage capacity",
    )

    model.vb_y_Treatment = Var(
        model.s_R,
        model.s_WT,
        model.s_J,
        within=Binary,
        initialize=0,
        doc="New or additional treatment capacity installed at treatment site with specific treatment capacity and treatment technology",
    )

    model.vb_y_Disposal = Var(
        model.s_K,
        model.s_I,
        within=Binary,
        initialize=0,
        doc="New or additional disposal capacity installed at disposal site with specific injection capacity",
    )

    model.vb_y_BeneficialReuse = Var(
        model.s_O,
        model.s_T,
        within=Binary,
        initialize=0,
        doc="Beneficial reuse option selection",
    )

    # Define emissions expressions #

    def TotalTruckingEmissionsRule(model, a):
        return (
            sum(
                sum(
                    sum(
                        model.v_F_Trucked[l, l_tilde, t]
                        / model.p_delta_Truck
                        * model.p_tau_Trucking[l, l_tilde]
                        * model.p_eta_TruckingEmissionsCoefficient[a]
                        for l in model.s_L
                        if (l, l_tilde) in model.s_LLT
                    )
                    for l_tilde in model.s_L
                )
                for t in model.s_T
            )
            * model.model_units["time"]
        )

    model.e_TotalTruckingEmissions = Expression(
        model.s_AC, rule=TotalTruckingEmissionsRule, doc="Total trucking emissions"
    )

    def TotalPipelineOperationsEmissionsRule(model, a):
        return (
            sum(
                sum(
                    sum(
                        model.v_F_Piped[l, l_tilde, t]
                        * model.p_lambda_Pipeline[l, l_tilde]
                        * model.p_eta_PipelineOperationsEmissionsCoefficient[a]
                        for l in model.s_L
                        if (l, l_tilde) in model.s_LLA
                    )
                    for l_tilde in model.s_L
                )
                for t in model.s_T
            )
            * model.model_units["time"]
        )

    model.e_TotalPipeOperationsEmissions = Expression(
        model.s_AC,
        rule=TotalPipelineOperationsEmissionsRule,
        doc="Total pipeline operations emissions",
    )

    def TotalPipelineInstallationEmissionsRule(model, a):
        return sum(
            sum(
                sum(model.vb_y_Pipeline[l, l_tilde, d] for d in model.s_D)
                * model.p_lambda_Pipeline[l, l_tilde]
                * model.p_eta_PipelineInstallationEmissionsCoefficient[a]
                for l in model.s_L
                if (l, l_tilde) in model.s_LLA
            )
            for l_tilde in model.s_L
        )

    model.e_TotalPipeInstallEmissions = Expression(
        model.s_AC,
        rule=TotalPipelineInstallationEmissionsRule,
        doc="Total pipeline installation emissions",
    )

    def TotalDisposalEmissionsRule(model, a):
        return model.v_F_TotalDisposed * model.p_eta_DisposalEmissionsCoefficient[a]

    model.e_TotalDisposalEmissions = Expression(
        model.s_AC, rule=TotalDisposalEmissionsRule, doc="Total disposal emissions"
    )

    def TotalStorageEmissionsRule(model, a):
        return (
            sum(
                sum(
                    model.v_L_Storage[s, t] * model.p_eta_StorageEmissionsCoefficient[a]
                    for s in model.s_S
                )
                for t in model.s_T
            )
            * model.model_units["time"]
        )

    model.e_TotalStorageEmissions = Expression(
        model.s_AC, rule=TotalStorageEmissionsRule, doc="Total storage emissions"
    )

    def TotalTreatmentEmissionsRule(model, a):
        return (
            sum(
                sum(
                    sum(
                        model.v_F_TreatmentFeedTech[r, wt, t]
                        * model.p_eta_TreatmentEmissionsCoefficient[wt, a]
                        for wt in model.s_WT
                    )
                    for r in model.s_R
                )
                for t in model.s_T
            )
            * model.model_units["time"]
        )

    model.e_TotalTreatmentEmissions = Expression(
        model.s_AC, rule=TotalTreatmentEmissionsRule, doc="Total treatment emissions"
    )

    def TotalEmissionsByComponentRule(model, a):
        return (
            model.e_TotalTruckingEmissions[a]
            + model.e_TotalPipeOperationsEmissions[a]
            + model.e_TotalPipeInstallEmissions[a]
            + model.e_TotalDisposalEmissions[a]
            + model.e_TotalStorageEmissions[a]
            + model.e_TotalTreatmentEmissions[a]
        )

    model.e_TotalEmissionsByComponent = Expression(
        model.s_AC,
        rule=TotalEmissionsByComponentRule,
        doc="Total emissions by component",
    )

    model.e_TotalEmissions = Expression(
        expr=sum(model.e_TotalEmissionsByComponent[a] for a in model.s_AC),
        doc="Total emissions [mass]",
    )

    # Define expressions for additional KPIs #
    model.e_DisposalFraction = Expression(
        expr=model.v_F_TotalDisposed / model.p_beta_TotalProd,
        doc="Fraction of produced and flowback water that is disposed [fraction]",
    )

    model.e_TotalCompletionsDeliveries = Expression(
        expr=sum(
            sum(model.v_F_CompletionsDestination[cp, t] for cp in model.s_CP)
            for t in model.s_T
        )
        * model.model_units["time"],
        doc="Total deliveries to completions pads to meet completions demand [volume]",
    )

    model.e_CompletionsSourcedFrac = Expression(
        expr=model.v_F_TotalSourced / model.e_TotalCompletionsDeliveries,
        doc="Fraction of completions deliveries using externally sourced water [fraction]",
    )

    model.e_CompletionsReusedFrac = Expression(
        expr=model.v_F_TotalReused / model.e_TotalCompletionsDeliveries,
        doc="Fraction of completions deliveries using reused water [fraction]",
    )

    model.e_TotalResidualWater = Expression(
        expr=sum(
            sum(model.v_F_ResidualWater[r, t] for t in model.s_T) for r in model.s_R
        )
        * model.model_units["time"],
        doc="Total residual water from treatment sites [volume]",
    )

    model.e_TotalResidualDesalinationWater = Expression(
        expr=sum(
            sum(model.v_F_ResidualWater[r, t] for t in model.s_T)
            for r in model.s_R
            if model.p_chi_DesalinationSites[r] == 1
        )
        * model.model_units["time"],
        doc="Total residual water from desalination treatment sites [volume]",
    )

    model.e_TotalResidualNonDesalWater = Expression(
        expr=sum(
            sum(model.v_F_ResidualWater[r, t] for t in model.s_T)
            for r in model.s_R
            if model.p_chi_DesalinationSites[r] == 0
        )
        * model.model_units["time"],
        doc="Total residual water from non-desalination treatment sites [volume]",
    )

    model.e_TotalReused = Expression(
        expr=sum(
            sum(model.v_F_ReuseDestination[p, t] for p in model.s_CP) for t in model.s_T
        )
        * model.model_units["time"],
        doc="Total water reused to meet completions demand [volume]",
    )

    model.e_TotalReusedInternal = Expression(
        expr=sum(
            sum(
                model.v_F_ReuseDestination[p, t]
                for p in model.s_CP
                if model.p_chi_OutsideCompletionsPad[p] == 0
            )
            for t in model.s_T
        )
        * model.model_units["time"],
        doc="Total water reused to meet completions demand internal to system [volume]",
    )

    model.e_TotalReusedExternal = Expression(
        expr=sum(
            sum(
                model.v_F_ReuseDestination[p, t]
                for p in model.s_CP
                if model.p_chi_OutsideCompletionsPad[p] == 1
            )
            for t in model.s_T
        )
        * model.model_units["time"],
        doc="Total water reused to meet completions demand external to system [volume]",
    )

    model.e_TotalEvaporated = Expression(
        expr=sum(
            sum(model.v_F_StorageEvaporationStream[s, t] for s in model.s_S)
            for t in model.s_T
        )
        * model.model_units["time"],
        doc="Total water evaporated [volume]",
    )

    # Calculate subsurface risk metrics if necessary
    model.do_subsurface_risk_calcs = (
        model.config.subsurface_risk != SubsurfaceRisk.false
        or model.config.objective == Objectives.subsurface_risk
    )
    if model.do_subsurface_risk_calcs:
        subsurface_risk(model)

    # For each possible objective function, create a corresponding variable and constrain it with the correct expression #

    ####### Minimum cost objective #######
    model.v_Z = Var(
        within=Reals,
        units=model.model_units["currency"],
        doc="Objective function variable - minimize cost [currency]",
    )

    model.ObjectiveFunctionCost = Constraint(
        expr=model.v_Z
        == model.v_C_TotalSourced
        + model.v_C_TotalDisposal
        + model.v_C_TotalTreatment
        + model.v_C_TotalReuse
        + model.v_C_TotalPiping
        + model.v_C_TotalStorage
        + model.v_C_TotalTrucking
        + model.v_C_TotalBeneficialReuse
        + model.p_alpha_AnnualizationRate
        * (
            model.v_C_DisposalCapEx
            + model.v_C_StorageCapEx
            + model.v_C_TreatmentCapEx
            + model.v_C_PipelineCapEx
        )
        + model.v_C_Slack
        - model.v_R_TotalStorage
        - model.v_R_TotalBeneficialReuse,
        doc="Objective function constraint - minimize cost",
    )

    model.objective_Cost = Objective(
        expr=model.v_Z, sense=minimize, doc="Objective function - minimize cost"
    )

    model.objective_Cost.deactivate()

    ####### Maximum reuse objective #######
    model.v_Z_Reuse = Var(
        within=Reals,
        units=pyunits.dimensionless,
        doc="Objective function variable - maximize reuse [dimensionless]",
    )

    model.ObjectiveFunctionReuse = Constraint(
        expr=model.v_Z_Reuse == model.v_F_TotalReused / model.p_beta_TotalProd,
        doc="Objective function constraint - maximize reuse",
    )

    model.objective_Reuse = Objective(
        expr=model.v_Z_Reuse, sense=maximize, doc="Objective function - maximize reuse"
    )

    model.objective_Reuse.deactivate()

    ####### Minimum subsurface risk objective #######
    if model.do_subsurface_risk_calcs:
        model.v_Z_SubsurfaceRisk = Var(
            within=Reals,
            units=model.model_units["volume_time"],
            doc="Objective function variable - minimize subsurface risk [volume/time]",
        )
        model.ObjectiveFunctionSubsurfaceRisk = Constraint(
            expr=model.v_Z_SubsurfaceRisk
            == sum(
                sum(model.v_F_DisposalDestination[k, t] for t in model.s_T)
                * model.subsurface.e_risk_metrics[k]
                for k in model.s_K
            ),
            doc="Objective function constraint - minimize subsurface risk",
        )

        model.objective_SubsurfaceRisk = Objective(
            expr=model.v_Z_SubsurfaceRisk,
            sense=minimize,
            doc="Objective function - minimize subsurface risk",
        )

        model.objective_SubsurfaceRisk.deactivate()

    ####### Minimum emissions objective #######
    model.objective_Emissions = Objective(
        expr=model.e_TotalEmissions,
        sense=minimize,
        doc="Objective function - minimize emissions",
    )

    model.objective_Emissions.deactivate()

    # Surrogate desalination models #

    if model.config.objective == Objectives.cost_surrogate:
        if model.config.desalination_model == DesalinationModel.false:
            raise Exception(
                "Cannot create a surrogate objective without a Desalination Model being selected"
            )
        from idaes.core.surrogate.surrogate_block import SurrogateBlock
        from idaes.core.surrogate.keras_surrogate import KerasSurrogate

        # Create variables needed for surrogate #
        model.v_C_Treatment_site = Var(
            model.s_R,
            model.s_T,
            initialize=0,
            within=NonNegativeReals,
            units=model.model_units["currency_time"],
            doc="Cost of treating produced water at treatment site [currency_time]",
        )
        model.v_C_Treatment_site_ReLU = Var(
            model.s_R,
            model.s_T,
            initialize=0,
            within=NonNegativeReals,
            units=model.model_units["currency_time"],
            doc="Annualized cost of treating produced water at treatment site with flow consideration [currency_time]",
        )
        model.v_C_TreatmentCapEx_site = Var(
            model.s_R,
            initialize=0,
            within=NonNegativeReals,
            units=model.model_units["currency"],
            doc="Annualized capital cost of constructing or expanding treatment capacity for each site [currency]",
        )
        model.v_C_TreatmentCapEx_site_time = Var(
            model.s_R,
            model.s_T,
            initialize=0,
            within=NonNegativeReals,
            units=model.model_units["currency"],
            doc="Annualized capital cost of constructing or expanding treatment capacity for each time at each site [currency]",
        )
        model.v_C_TreatmentCapEx_surrogate = Var(
            initialize=0,
            within=NonNegativeReals,
            units=model.model_units["currency"],
            doc="Annualized capital cost of constructing or expanding treatment capacity [currency]",
        )
        model.vb_y_DesalSelected = Var(
            model.s_R,
            within=Binary,
            initialize=0,
            doc="Selection for each desalination site",
        )
        model.inlet_salinity = Var(
            model.s_R,
            within=Reals,
            initialize=model.df_parameters["DesalinationSurrogate"]["inlet_salinity"],
            units=pyunits.kg / pyunits.litre,
            doc="Inlet salinity in the feed [kg/L]",
        )
        model.recovery = Var(
            model.s_R,
            initialize=model.df_parameters["DesalinationSurrogate"]["recovery"],
            within=Reals,
            bounds=(0, 1),
            doc="Volumetric recovery fraction of water",
        )
        model.vb_y_flow_ReLU = Var(
            model.s_R,
            model.s_T,
            initialize=0,
            within=Binary,
            doc="Binary indicating flow greater than 0",
        )
        model.v_T_Treatment_scaled_ReLU = Var(
            model.s_R,
            model.s_T,
            initialize=0,
            within=NonNegativeReals,
            doc="Putting flow to 0 if DesalSite is not selected",
        )
        model.v_C_TreatmentOpex_surrogate = Var(
            initialize=0,
            within=NonNegativeReals,
            units=model.model_units["currency"],
            doc="Capital operating treatment capacity [currency]",
        )
        model.BigM = Param(initialize=1e6, mutable=True)

        ####### Minimum cost objective with surrogate model #######
        model.v_Z_Surrogate = Var(
            within=Reals,
            units=model.model_units["currency"],
            doc="Objective function variable - minimize cost with surrogate desalination model [currency]",
        )

        model.ObjectiveFunctionCostSurrogate = Constraint(
            expr=model.v_Z_Surrogate
            == model.v_C_TotalSourced
            + model.v_C_TotalDisposal
            + model.v_C_TotalTreatment
            + model.v_C_TotalReuse
            + model.v_C_TotalPiping
            + model.v_C_TotalStorage
            + model.v_C_TotalTrucking
            + model.v_C_TotalBeneficialReuse
            + model.v_C_TreatmentOpex_surrogate
            + model.v_C_TreatmentCapEx_surrogate
            + model.p_alpha_AnnualizationRate
            * (
                model.v_C_DisposalCapEx
                + model.v_C_StorageCapEx
                + model.v_C_PipelineCapEx
                + model.v_C_TreatmentCapEx
            )
            + model.v_C_Slack
            - model.v_R_TotalStorage
            - model.v_R_TotalBeneficialReuse,
            doc="Objective function constraint - minimize cost with surrogate",
        )

        model.objective_CostSurrogate = Objective(
            expr=model.v_Z_Surrogate,
            sense=minimize,
            doc="Objective function - minimize cost with surrogate",
        )

        model.objective_CostSurrogate.deactivate()

        # Define constraints for surrogate #
        model.inlet_salinity.fix()
        model.recovery.fix()
        model.surrogate_costs = SurrogateBlock(model.s_R, model.s_T)
        model.model_units["L_per_s"] = pyunits.L / pyunits.s
        conversion_factor = pyunits.convert_value(
            1,
            from_units=model.model_units["volume_time"],
            to_units=model.model_units["L_per_s"],
        )

        model.v_T_Treatment_scaled = Var(
            model.s_R,
            model.s_T,
            within=NonNegativeReals,
            initialize=1 * 5 * conversion_factor,
        )

        model.cap_upper_bound = Param(
            initialize=29,
            mutable=True,
            units=model.model_units["L_per_s"],
            doc="Upper bound of flow for trained surrogate [L/s]",
        )

        model.cap_lower_bound = Param(
            initialize=0,
            mutable=True,
            units=model.model_units["L_per_s"],
            doc="Lower bound of flow for trained surrogate [L/s]",
        )

        for i in model.s_R:
            for t in model.s_T:
                if model.p_chi_DesalinationSites[i]:
                    model.v_T_Treatment_scaled[i, t].setlb(model.cap_lower_bound)
                    model.v_T_Treatment_scaled[i, t].setub(model.cap_upper_bound)

                else:
                    model.v_T_Treatment_scaled[i, t].fix(0)

        def scalingTreatment(model, r, t):
            if model.p_chi_DesalinationSites[r]:
                return model.v_T_Treatment_scaled[r, t] == conversion_factor * (
                    sum(
                        model.v_F_Piped[l, r, t]
                        for l in model.s_L
                        if (l, r) in model.s_LLA
                    )
                    + sum(
                        model.v_F_Trucked[l, r, t]
                        for l in model.s_L
                        if (l, r) in model.s_LLT
                    )
                )
            else:
                return Constraint.Skip

        model.treatment_vol = Constraint(model.s_R, model.s_T, rule=scalingTreatment)
        base_dir = Path(this_file_dir())
        if model.config.desalination_model == DesalinationModel.mvc:
            keras_surrogate = KerasSurrogate.load_from_folder(
                str(base_dir / "mvc_keras")
            )
        elif model.config.desalination_model == DesalinationModel.md:
            keras_surrogate = KerasSurrogate.load_from_folder(
                str(base_dir / "md_keras")
            )

        for i in model.s_R:
            for t in model.s_T:
                if model.p_chi_DesalinationSites[i]:
                    # Build the model with non-zero outputs
                    cap = model.v_T_Treatment_scaled[i, t]
                    model.surrogate_costs[i, t].build_model(
                        keras_surrogate,
                        formulation=KerasSurrogate.Formulation.RELU_BIGM,
                        input_vars=[model.inlet_salinity[i], model.recovery[i], cap],
                        output_vars=[
                            model.v_C_TreatmentCapEx_site_time[i, t],
                            model.v_C_Treatment_site[i, t],
                        ],
                    )
                else:
                    # If not a desalination site, fix the outputs to zero
                    model.v_T_Treatment_scaled[i, t].fix(0)
                    model.v_C_TreatmentCapEx_site_time[i, t].fix(0)
                    model.v_C_Treatment_site[i, t].fix(0)

        def flowBinRule(model, r, t):
            return model.v_T_Treatment_scaled[r, t] >= 0 + 1e-6 - model.BigM * (
                1 - model.vb_y_flow_ReLU[r, t]
            )

        model.flowBin = Constraint(
            model.s_R,
            model.s_T,
            rule=flowBinRule,
            doc="Flow binary to set to 0 if flow is 0, else 1",
        )

        def flowMaxRule(model, r, t):
            return (
                model.v_T_Treatment_scaled[r, t]
                <= model.BigM * model.vb_y_flow_ReLU[r, t]
            )

        model.flowMax = Constraint(
            model.s_R,
            model.s_T,
            rule=flowMaxRule,
            doc="Flow binary to set to 0 if flow is 0 else 1",
        )

        def OpexTreatmentRule(model, r, t):
            return model.v_C_Treatment_site_ReLU[r, t] >= model.v_C_Treatment_site[
                r, t
            ] - model.BigM * (1 - model.vb_y_flow_ReLU[r, t])

        model.OpexTreatment = Constraint(
            model.s_R, model.s_T, rule=OpexTreatmentRule, doc="Opex based on binary"
        )

        def treatmentCost(model):
            if model.decision_period == pyunits.day:
                annual_factor = 365
            elif model.decision_period == pyunits.week:
                annual_factor = 52
            elif model.decision_period == pyunits.fortnight:
                annual_factor = 26
            elif model.decision_period == pyunits.month:
                annual_factor = 12
            else:
                raise Exception(
                    "Decision Period should be day, week, fortnight or month"
                )
            return (
                model.v_C_TreatmentOpex_surrogate
                == sum(
                    sum(model.v_C_Treatment_site_ReLU[r, t] for r in model.s_R)
                    for t in model.s_T
                )
                / annual_factor  # model.v_C_Treatment_site_ReLU yeilds an annualized opex and thus needs to be divided by annual_factor which gives opex for period t
            )

        model.treatmentCost = Constraint(rule=treatmentCost, doc="Treatment Rule")

        def treatmentCapexSurrogate(model, i, t):
            return model.v_C_TreatmentCapEx_site[
                i
            ] >= model.v_C_TreatmentCapEx_site_time[i, t] - model.BigM * (
                1 - model.vb_y_flow_ReLU[i, t]
            )

        model.max_cap = Constraint(
            model.s_R,
            model.s_T,
            rule=treatmentCapexSurrogate,
            doc="Max treated vol as capex",
        )

        def capExSurrogate(model):
            return model.v_C_TreatmentCapEx_surrogate == sum(
                model.v_C_TreatmentCapEx_site[i] for i in model.s_R
            )

        model.CapEx_cost = Constraint(rule=capExSurrogate, doc="Treatment costs")

    # Activate correct objective function based on config value #
    set_objective(model, model.config.objective)

    # Build constraints #
    build_common_constraints(model)

    def TerminalStorageLevelRule(model, s, t):
        if t == model.s_T.last():
            constraint = model.v_L_Storage[s, t] <= model.p_theta_Storage[s]
        else:
            return Constraint.Skip

        return process_constraint(constraint)

    model.TerminalStorageLevel = Constraint(
        model.s_S,
        model.s_T,
        rule=TerminalStorageLevelRule,
        doc="Terminal storage site level",
    )

    # only include network node capacity constraint if config is set to true
    if model.config.node_capacity == True:

        def NetworkNodeCapacityRule(model, n, t):
            if value(model.p_sigma_NetworkNode[n]) > 0:
                constraint = (
                    sum(
                        model.v_F_Piped[l, n, t]
                        for l in model.s_L
                        if (l, n) in model.s_LLA
                    )
                    <= model.p_sigma_NetworkNode[n]
                )
            else:
                return Constraint.Skip

            return process_constraint(constraint)

        # simple constraint rule required to prevent errors if there are no node flows
        model.NetworkCapacity = Constraint(
            model.s_N,
            model.s_T,
            rule=simple_constraint_rule(NetworkNodeCapacityRule),
            doc="Network node capacity",
        )

    def TreatmentCapacityExpansionRule(model, r):
        if model.config.objective == Objectives.cost_surrogate:
            return (
                model.v_T_Capacity[r]
                == sum(
                    (
                        model.p_sigma_Treatment[r, wt]
                        * sum(model.vb_y_Treatment[r, wt, j] for j in model.s_J)
                        + sum(
                            model.p_delta_Treatment[wt, j]
                            * model.vb_y_Treatment[r, wt, j]
                            for j in model.s_J
                        )
                    )
                    for wt in model.s_WT
                )
                + model.cap_upper_bound * model.vb_y_DesalSelected[r]
            )
        else:
            return model.v_T_Capacity[r] == sum(
                (
                    model.p_sigma_Treatment[r, wt]
                    * sum(model.vb_y_Treatment[r, wt, j] for j in model.s_J)
                    + sum(
                        model.p_delta_Treatment[wt, j] * model.vb_y_Treatment[r, wt, j]
                        for j in model.s_J
                    )
                )
                for wt in model.s_WT
            )

    model.TreatmentCapacityExpansion = Constraint(
        model.s_R,
        rule=TreatmentCapacityExpansionRule,
        doc="Treatment capacity construction/expansion",
    )

    def TreatmentFeedBalanceRule(model, r, t):
        constraint = (
            sum(model.v_F_Piped[l, r, t] for l in model.s_L if (l, r) in model.s_LLA)
            + sum(
                model.v_F_Trucked[l, r, t] for l in model.s_L if (l, r) in model.s_LLT
            )
            == model.v_F_TreatmentFeed[r, t]
        )
        return process_constraint(constraint)

    model.TreatmentFeedBalance = Constraint(
        model.s_R,
        model.s_T,
        rule=TreatmentFeedBalanceRule,
        doc="Treatment center feed flow balance",
    )

    def TreatmentFeedTechLHSRule(model, r, wt, t):
        constraint = model.v_F_TreatmentFeedTech[r, wt, t] >= model.v_F_TreatmentFeed[
            r, t
        ] - model.p_M_Flow * (
            1 - sum(model.vb_y_Treatment[r, wt, j] for j in model.s_J)
        )
        return process_constraint(constraint)

    model.TreatmentFeedTechLHS = Constraint(
        model.s_R,
        model.s_WT,
        model.s_T,
        rule=TreatmentFeedTechLHSRule,
        doc="Treatment feed indexed by treatment technology",
    )

    def TreatmentFeedTechRHSRule(model, r, wt, t):
        constraint = model.v_F_TreatmentFeedTech[r, wt, t] <= model.v_F_TreatmentFeed[
            r, t
        ] + model.p_M_Flow * (
            1 - sum(model.vb_y_Treatment[r, wt, j] for j in model.s_J)
        )
        return process_constraint(constraint)

    model.TreatmentFeedTechRHS = Constraint(
        model.s_R,
        model.s_WT,
        model.s_T,
        rule=TreatmentFeedTechRHSRule,
        doc="Treatment feed indexed by treatment technology",
    )

    def TreatmentBalanceRule(model, r, t):
        constraint = (
            model.v_F_TreatmentFeed[r, t]
            == model.v_F_ResidualWater[r, t] + model.v_F_TreatedWater[r, t]
        )
        return process_constraint(constraint)

    model.TreatmentBalance = Constraint(
        model.s_R,
        model.s_T,
        rule=TreatmentBalanceRule,
        doc="Treatment center flow balance",
    )

    def ResidualWaterLHSRule(model, r, wt, t):
        if model.config.objective == Objectives.cost_surrogate:
            if model.p_chi_DesalinationSites[r]:
                epsilon_treatment = model.recovery[r]
                treatment_selection = model.vb_y_DesalSelected[r]
            else:
                epsilon_treatment = model.p_epsilon_Treatment[r, wt]
                treatment_selection = sum(
                    model.vb_y_Treatment[r, wt, j] for j in model.s_J
                )

            constraint = (
                model.v_F_TreatmentFeed[r, t] * (1 - epsilon_treatment)
                - model.p_M_Flow * (1 - treatment_selection)
                <= model.v_F_ResidualWater[r, t]
            )
            return process_constraint(constraint)
        else:
            constraint = (
                model.v_F_TreatmentFeed[r, t] * (1 - model.p_epsilon_Treatment[r, wt])
                - model.p_M_Flow
                * (1 - sum(model.vb_y_Treatment[r, wt, j] for j in model.s_J))
                <= model.v_F_ResidualWater[r, t]
            )
            return process_constraint(constraint)

    model.ResidualWaterLHS = Constraint(
        model.s_R,
        model.s_WT,
        model.s_T,
        rule=ResidualWaterLHSRule,
        doc="Residual water based on treatment efficiency",
    )

    def ResidualWaterRHSRule(model, r, wt, t):
        if model.config.objective == Objectives.cost_surrogate:
            if model.p_chi_DesalinationSites[r]:
                epsilon_treatment = model.recovery[r]
                treatment_selection = model.vb_y_DesalSelected[r]
            else:
                epsilon_treatment = model.p_epsilon_Treatment[r, wt]
                treatment_selection = sum(
                    model.vb_y_Treatment[r, wt, j] for j in model.s_J
                )

            constraint = (
                model.v_F_TreatmentFeed[r, t] * (1 - epsilon_treatment)
                + model.p_M_Flow * (1 - treatment_selection)
                >= model.v_F_ResidualWater[r, t]
            )

            return process_constraint(constraint)
        else:
            constraint = (
                model.v_F_TreatmentFeed[r, t] * (1 - model.p_epsilon_Treatment[r, wt])
                + model.p_M_Flow
                * (1 - sum(model.vb_y_Treatment[r, wt, j] for j in model.s_J))
                >= model.v_F_ResidualWater[r, t]
            )
            return process_constraint(constraint)

    model.ResidualWaterRHS = Constraint(
        model.s_R,
        model.s_WT,
        model.s_T,
        rule=ResidualWaterRHSRule,
        doc="Residual water based on treatment efficiency",
    )

    # Create a set of all treatment sites for which the treated stream should
    # be modeled
    treatment_sites_with_treated_stream_modeled = {
        origin
        for ((origin, _), value) in list(model.df_parameters["LLA"].items())
        + list(model.df_parameters["LLT"].items())
        if origin in model.s_R and value == TreatmentStreams.treated_stream
    }

    def TreatedWaterBalanceRule(model, r, t):
        # If treated stream from a treatment site should be modeled, then
        # create constraint for the treated water. Otherwise, skip.
        if r in treatment_sites_with_treated_stream_modeled:
            constraint = model.v_F_TreatedWater[r, t] == sum(
                model.v_F_Piped[r, l, t]
                for l in model.s_L
                if (r, l) in model.s_LLA
                and model.df_parameters["LLA"][r, l] == TreatmentStreams.treated_stream
            ) + sum(
                model.v_F_Trucked[r, l, t]
                for l in model.s_L
                if (r, l) in model.s_LLT
                and model.df_parameters["LLT"][r, l] == TreatmentStreams.treated_stream
            )
            return process_constraint(constraint)
        else:
            return Constraint.Skip

    model.TreatedWaterBalance = Constraint(
        model.s_R, model.s_T, rule=TreatedWaterBalanceRule, doc="Treated water balance"
    )

    # Create a set of all treatment sites for which the residual stream should
    # be modeled. Arcs originating from a treatment site may have a value of 0,
    # 1, or 2 to denote no arc, treated stream, and residual stream,
    # respectively.
    treatment_sites_with_residual_stream_modeled = {
        origin
        for ((origin, _), value) in list(model.df_parameters["LLA"].items())
        + list(model.df_parameters["LLT"].items())
        if origin in model.s_R and value == TreatmentStreams.residual_stream
    }

    def ResidualWaterBalanceRule(model, r, t):
        # If residual stream from a treatment site should be modeled, then
        # create constraint for the residual water. Otherwise, skip.
        if r in treatment_sites_with_residual_stream_modeled:
            constraint = model.v_F_ResidualWater[r, t] == sum(
                model.v_F_Piped[r, l, t]
                for l in model.s_L
                if (r, l) in model.s_LLA
                and model.df_parameters["LLA"][r, l] == TreatmentStreams.residual_stream
            ) + sum(
                model.v_F_Trucked[r, l, t]
                for l in model.s_L
                if (r, l) in model.s_LLT
                and model.df_parameters["LLT"][r, l] == TreatmentStreams.residual_stream
            )
            return process_constraint(constraint)
        else:
            return Constraint.Skip

    model.ResidualWaterBalance = Constraint(
        model.s_R,
        model.s_T,
        rule=ResidualWaterBalanceRule,
        doc="Residual water balance",
    )

    def BeneficialReuseMinimumRule(model, o, t):
        if value(model.p_sigma_BeneficialReuseMinimum[o, t]) > 0:
            constraint = (
                model.v_F_BeneficialReuseDestination[o, t]
                >= model.p_sigma_BeneficialReuseMinimum[o, t]
                * model.vb_y_BeneficialReuse[o, t]
            )
            return process_constraint(constraint)
        else:
            return Constraint.Skip

    model.BeneficialReuseMinimum = Constraint(
        model.s_O,
        model.s_T,
        rule=BeneficialReuseMinimumRule,
        doc="Beneficial reuse minimum flow",
    )

    def BeneficialReuseCapacityRule(model, o, t):
        if value(model.p_sigma_BeneficialReuse[o, t]) < 0:
            # Beneficial reuse capacity value has not been provided by user
            constraint = (
                model.v_F_BeneficialReuseDestination[o, t]
                <= model.p_M_Flow * model.vb_y_BeneficialReuse[o, t]
                + model.v_S_BeneficialReuseCapacity[o]
            )
        else:
            # Beneficial reuse capacity value has been provided by user
            constraint = (
                model.v_F_BeneficialReuseDestination[o, t]
                <= model.p_sigma_BeneficialReuse[o, t]
                * model.vb_y_BeneficialReuse[o, t]
                + model.v_S_BeneficialReuseCapacity[o]
            )

        return process_constraint(constraint)

    model.BeneficialReuseCapacity = Constraint(
        model.s_O,
        model.s_T,
        rule=BeneficialReuseCapacityRule,
        doc="Beneficial reuse capacity",
    )

    # TODO: Improve testing of Beneficial reuse capacity constraint

    def TotalBeneficialReuseVolumeRule(model):
        constraint = model.v_F_TotalBeneficialReuse == (
            sum(
                sum(model.v_F_BeneficialReuseDestination[o, t] for o in model.s_O)
                for t in model.s_T
            )
        )
        return process_constraint(constraint)

    model.TotalBeneficialReuse = Constraint(
        rule=TotalBeneficialReuseVolumeRule, doc="Total beneficial reuse volume"
    )

    def TotalDisposalVolumeRule(model):
        constraint = model.v_F_TotalDisposed == sum(
            sum(model.v_F_DisposalDestination[k, t] for k in model.s_K)
            for t in model.s_T
        )

        return process_constraint(constraint)

    model.TotalDisposalVolume = Constraint(
        rule=TotalDisposalVolumeRule, doc="Total disposal volume"
    )

    def TreatmentCostLHSRule(model, r, wt, t):
        constraint = (
            model.v_C_Treatment[r, t]
            >= (
                sum(
                    model.v_F_Piped[l, r, t] for l in model.s_L if (l, r) in model.s_LLA
                )
                + sum(
                    model.v_F_Trucked[l, r, t]
                    for l in model.s_L
                    if (l, r) in model.s_LLT
                )
                - model.p_M_Flow
                * (1 - sum(model.vb_y_Treatment[r, wt, j] for j in model.s_J))
            )
            * model.p_pi_Treatment[r, wt]
        )
        return process_constraint(constraint)

    model.TreatmentCostLHS = Constraint(
        model.s_R,
        model.s_WT,
        model.s_T,
        rule=TreatmentCostLHSRule,
        doc="Treatment cost",
    )

    def TreatmentCostRHSRule(model, r, wt, t):
        constraint = (
            model.v_C_Treatment[r, t]
            <= (
                sum(
                    model.v_F_Piped[l, r, t] for l in model.s_L if (l, r) in model.s_LLA
                )
                + sum(
                    model.v_F_Trucked[l, r, t]
                    for l in model.s_L
                    if (l, r) in model.s_LLT
                )
                + model.p_M_Flow
                * (1 - sum(model.vb_y_Treatment[r, wt, j] for j in model.s_J))
            )
            * model.p_pi_Treatment[r, wt]
        )
        return process_constraint(constraint)

    model.TreatmentCostRHS = Constraint(
        model.s_R,
        model.s_WT,
        model.s_T,
        rule=TreatmentCostRHSRule,
        doc="Treatment cost",
    )

    def TotalReuseVolumeRule(model):
        constraint = model.v_F_TotalReused == (
            sum(
                sum(
                    sum(
                        model.v_F_Piped[l, p, t]
                        for l in (model.s_L - model.s_F)
                        if (l, p) in model.s_LLA
                    )
                    + sum(
                        model.v_F_Trucked[l, p, t]
                        for l in (model.s_L - model.s_F)
                        if (l, p) in model.s_LLT
                    )
                    for p in model.s_CP
                )
                for t in model.s_T
            )
        )
        return process_constraint(constraint)

    model.TotalReuseVolume = Constraint(
        rule=TotalReuseVolumeRule, doc="Total volume reused at completions"
    )

    def BeneficialReuseCostRule(model, o, t):
        constraint = model.v_C_BeneficialReuse[o, t] == (
            (
                sum(
                    model.v_F_Piped[l, o, t] for l in model.s_L if (l, o) in model.s_LLA
                )
                + sum(
                    model.v_F_Trucked[l, o, t]
                    for l in model.s_L
                    if (l, o) in model.s_LLT
                )
            )
            * model.p_pi_BeneficialReuse[o]
        )

        return process_constraint(constraint)

    model.BeneficialReuseCost = Constraint(
        model.s_O,
        model.s_T,
        rule=BeneficialReuseCostRule,
        doc="Beneficial reuse processing cost",
    )

    def TotalBeneficialReuseCostRule(model):
        constraint = model.v_C_TotalBeneficialReuse == sum(
            sum(model.v_C_BeneficialReuse[o, t] for o in model.s_O) for t in model.s_T
        )
        return process_constraint(constraint)

    model.TotalBeneficialReuseCost = Constraint(
        rule=TotalBeneficialReuseCostRule, doc="Total beneficial reuse processing cost"
    )

    def BeneficialReuseCreditRule(model, o, t):
        constraint = model.v_R_BeneficialReuse[o, t] == (
            (
                sum(
                    model.v_F_Piped[l, o, t] for l in model.s_L if (l, o) in model.s_LLA
                )
                + sum(
                    model.v_F_Trucked[l, o, t]
                    for l in model.s_L
                    if (l, o) in model.s_LLT
                )
            )
            * model.p_rho_BeneficialReuse[o]
        )

        return process_constraint(constraint)

    model.BeneficialReuseCredit = Constraint(
        model.s_O,
        model.s_T,
        rule=BeneficialReuseCreditRule,
        doc="Beneficial reuse credit",
    )

    def TotalBeneficialReuseCreditRule(model):
        constraint = model.v_R_TotalBeneficialReuse == sum(
            sum(model.v_R_BeneficialReuse[o, t] for o in model.s_O) for t in model.s_T
        )
        return process_constraint(constraint)

    model.TotalBeneficialReuseCredit = Constraint(
        rule=TotalBeneficialReuseCreditRule, doc="Total beneficial reuse credit"
    )

    def TotalTruckingVolumeRule(model):
        constraint = model.v_F_TotalTrucked == (
            sum(
                sum(
                    sum(
                        model.v_F_Trucked[l, l_tilde, t]
                        for l in model.s_L
                        if (l, l_tilde) in model.s_LLT
                    )
                    for l_tilde in model.s_L
                )
                for t in model.s_T
            )
        )
        return process_constraint(constraint)

    model.TotalTruckingVolume = Constraint(
        rule=TotalTruckingVolumeRule, doc="Total trucking volume"
    )

    def DisposalExpansionCapExRule(model):
        constraint = model.v_C_DisposalCapEx == sum(
            sum(
                model.vb_y_Disposal[k, i]
                * model.p_kappa_Disposal[k, i]
                * model.p_delta_Disposal[k, i]
                for i in model.s_I
            )
            for k in model.s_K
        )
        return process_constraint(constraint)

    model.DisposalExpansionCapEx = Constraint(
        rule=DisposalExpansionCapExRule,
        doc="Disposal construction or capacity expansion cost",
    )

    def StorageExpansionCapExRule(model):
        constraint = model.v_C_StorageCapEx == sum(
            sum(
                model.vb_y_Storage[s, c]
                * model.p_kappa_Storage[s, c]
                * model.p_delta_Storage[c]
                for s in model.s_S
            )
            for c in model.s_C
        )
        return process_constraint(constraint)

    model.StorageExpansionCapEx = Constraint(
        rule=StorageExpansionCapExRule,
        doc="Storage construction or capacity expansion cost",
    )

    def TreatmentExpansionCapExRule(model):
        constraint = model.v_C_TreatmentCapEx == sum(
            sum(
                sum(
                    model.vb_y_Treatment[r, wt, j]
                    * model.p_kappa_Treatment[r, wt, j]
                    * model.p_delta_Treatment[wt, j]
                    for r in model.s_R
                )
                for j in model.s_J
            )
            for wt in model.s_WT
        )
        return process_constraint(constraint)

    model.TreatmentExpansionCapEx = Constraint(
        rule=TreatmentExpansionCapExRule,
        doc="Treatment construction or capacity expansion cost",
    )

    def PipelineExpansionCapExDistanceBasedRule(model):
        constraint = model.v_C_PipelineCapEx == (
            sum(
                sum(
                    sum(
                        model.vb_y_Pipeline[l, l_tilde, d]
                        * model.p_kappa_Pipeline
                        * model.p_mu_Pipeline[d]
                        * model.p_lambda_Pipeline[l, l_tilde]
                        for l in model.s_L
                    )
                    for l_tilde in model.s_L
                )
                for d in model.s_D
            )
        )

        return process_constraint(constraint)

    def PipelineExpansionCapExCapacityBasedRule(model):
        constraint = model.v_C_PipelineCapEx == (
            sum(
                sum(
                    sum(
                        model.vb_y_Pipeline[l, l_tilde, d]
                        * model.p_kappa_Pipeline[l, l_tilde, d]
                        * model.p_delta_Pipeline[d]
                        for l in model.s_L
                    )
                    for l_tilde in model.s_L
                )
                for d in model.s_D
            )
        )

        return process_constraint(constraint)

    if model.config.pipeline_cost == PipelineCost.distance_based:
        model.PipelineExpansionCapEx = Constraint(
            rule=PipelineExpansionCapExDistanceBasedRule,
            doc="Pipeline construction or capacity expansion cost",
        )
    elif model.config.pipeline_cost == PipelineCost.capacity_based:
        model.PipelineExpansionCapEx = Constraint(
            rule=PipelineExpansionCapExCapacityBasedRule,
            doc="Pipeline construction or capacity expansion cost",
        )

    def LogicConstraintDisposalRule(model, k):
        constraint = sum(model.vb_y_Disposal[k, i] for i in model.s_I) <= 1
        return process_constraint(constraint)

    model.LogicConstraintDisposal = Constraint(
        model.s_K, rule=LogicConstraintDisposalRule, doc="Logic constraint disposal"
    )

    def LogicConstraintStorageRule(model, s):
        constraint = sum(model.vb_y_Storage[s, c] for c in model.s_C) <= 1
        return process_constraint(constraint)

    model.LogicConstraintStorage = Constraint(
        model.s_S, rule=LogicConstraintStorageRule, doc="Logic constraint storage"
    )

    def LogicConstraintTreatmentRule(model, r):
        if model.config.objective == Objectives.cost_surrogate:
            constraint = (
                sum(
                    sum(model.vb_y_Treatment[r, wt, j] for j in model.s_J)
                    for wt in model.s_WT
                )
                + model.vb_y_DesalSelected[r]
                <= 1
            )
            return process_constraint(constraint)
        else:
            constraint = (
                sum(
                    sum(model.vb_y_Treatment[r, wt, j] for j in model.s_J)
                    for wt in model.s_WT
                )
                <= 1
            )
            return process_constraint(constraint)

    model.LogicConstraintTreatmentAssignment = Constraint(
        model.s_R,
        rule=LogicConstraintTreatmentRule,
        doc="Treatment technology assignment",
    )

    def LogicConstraintDesalinationAssignmentRule(model, r):
        if model.p_chi_DesalinationSites[r]:
            constraint = (
                sum(
                    sum(model.vb_y_Treatment[r, wt, j] for j in model.s_J)
                    for wt in model.s_WT
                    if not model.p_chi_DesalinationTechnology[wt]
                )
                == 0
            )
            return process_constraint(constraint)
        else:
            return Constraint.Skip

    model.LogicConstraintDesalinationAssignment = Constraint(
        model.s_R,
        rule=LogicConstraintDesalinationAssignmentRule,
        doc="Logic constraint for flow if not desalination",
    )

    def LogicConstraintNoDesalinationAssignmentRule(model, r):
        if model.config.objective == Objectives.cost_surrogate:
            if not model.p_chi_DesalinationSites[r]:
                constraint = (
                    sum(
                        sum(model.vb_y_Treatment[r, wt, j] for j in model.s_J)
                        for wt in model.s_WT
                        if model.p_chi_DesalinationTechnology[wt]
                    )
                    + model.vb_y_DesalSelected[r]
                    == 0
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip
        else:
            if not model.p_chi_DesalinationSites[r]:
                constraint = (
                    sum(
                        sum(model.vb_y_Treatment[r, wt, j] for j in model.s_J)
                        for wt in model.s_WT
                        if model.p_chi_DesalinationTechnology[wt]
                    )
                    == 0
                )
                return process_constraint(constraint)
            else:
                return Constraint.Skip

    model.LogicConstraintNoDesalinationAssignment = Constraint(
        model.s_R,
        rule=LogicConstraintNoDesalinationAssignmentRule,
        doc="Logic constraint for flow if not desalination",
    )

    # TODO: make this more general by checking if there is water at t = 1
    # TODO: generalize to not set evaporation at all storage sites
    def EvaporationFlowRule(model, s, t):
        if t == model.s_T.first():
            constraint = model.v_F_StorageEvaporationStream[s, t] == 0
        else:
            constraint = model.v_F_StorageEvaporationStream[
                s, t
            ] == model.p_omega_EvaporationRate * sum(
                sum(model.vb_y_Treatment[r, "CB-EV", j] for j in model.s_J)
                for r in model.s_R
                if model.p_RSA[r, s]
            )
        return process_constraint(constraint)

    model.LogicConstraintEvaporationFlow = Constraint(
        model.s_S,
        model.s_T,
        rule=EvaporationFlowRule,
        doc="Logic constraint for flow if evaporation",
    )

    def LogicConstraintPipelineRule(model, l, l_tilde):
        if (l, l_tilde) in model.s_LLA:
            constraint = sum(model.vb_y_Pipeline[l, l_tilde, d] for d in model.s_D) <= 1
            return process_constraint(constraint)
        else:
            return Constraint.Skip

    model.LogicConstraintPipeline = Constraint(
        model.s_L,
        model.s_L,
        rule=LogicConstraintPipelineRule,
        doc="Logic constraint pipelines",
    )

    def CompletionsWaterDeliveriesRule(model, p, t):
        constraint = model.v_F_CompletionsDestination[p, t] == (
            sum(
                model.v_F_Piped[l, p, t]
                for l in (model.s_L - model.s_F)
                if (l, p) in model.s_LLA
            )
            + sum(model.v_F_Sourced[f, p, t] for f in model.s_F if model.p_FCA[f, p])
            + sum(
                model.v_F_Trucked[l, p, t]
                for l in (model.s_L - model.s_F)
                if (l, p) in model.s_LLT
            )
            + sum(model.v_F_Trucked[f, p, t] for f in model.s_F if model.p_FCT[f, p])
            - model.v_F_PadStorageIn[p, t]
            + model.v_F_PadStorageOut[p, t]
        )

        return process_constraint(constraint)

    model.CompletionsWaterDeliveries = Constraint(
        model.s_CP,
        model.s_T,
        rule=CompletionsWaterDeliveriesRule,
        doc="Completions water volume",
    )

    def SeismicActivityExceptionRule(model, k, t):
        constraint = (
            model.v_F_DisposalDestination[k, t]
            <= model.p_epsilon_DisposalOperatingCapacity[k, t] * model.v_D_Capacity[k]
        )
        return process_constraint(constraint)

    model.SeismicResponseArea = Constraint(
        model.s_K,
        model.s_T,
        rule=SeismicActivityExceptionRule,
        doc="Restrict flow within a seismic response area",
    )

    if (
        model.config.subsurface_risk
        == SubsurfaceRisk.exclude_over_and_under_pressured_wells
    ):

        def ExcludeUnderAndOverPressuredDisposalWellsRule(model, k):
            if model.subsurface.sites_included[k]:
                # Disposal is allowed at SWD k - skip
                return Constraint.Skip
            else:
                # Disposal is not allowed at SWD k - constrain to 0
                constraint = (
                    sum(model.v_F_DisposalDestination[k, t] for t in model.s_T) == 0
                )

            return process_constraint(constraint)

        model.ExcludeUnderAndOverPressuredDisposalWells = Constraint(
            model.s_K,
            rule=ExcludeUnderAndOverPressuredDisposalWellsRule,
            doc="Disallow disposal in over and under pressured wells",
        )

    if model.config.water_quality is WaterQuality.discrete:
        model = water_quality_discrete(model, df_parameters, df_sets)

    model = model_infeasibility_detection(model)
    return model


def set_objective(model, obj):
    """
    Activate the indicated objectve function for the model. The argument obj
    should be an instance of the Objectives class defined in this module.
    """
    # Deactivate all objective functions.
    model.objective_Cost.deactivate()
    model.objective_Reuse.deactivate()
    model.objective_Emissions.deactivate()
    if hasattr(model, "objective_CostSurrogate"):
        model.objective_CostSurrogate.deactivate()
    if model.do_subsurface_risk_calcs:
        model.objective_SubsurfaceRisk.deactivate()

    # Activate the objective function indicated by obj, and change the config
    # option accordingly.
    if obj == Objectives.cost:
        model.objective_Cost.activate()
        model.config.objective = Objectives.cost
    elif obj == Objectives.reuse:
        model.objective_Reuse.activate()
        model.config.objective = Objectives.reuse
    elif obj == Objectives.cost_surrogate:
        model.objective_CostSurrogate.activate()
        model.config.objective = Objectives.cost_surrogate
    elif obj == Objectives.subsurface_risk:
        if model.do_subsurface_risk_calcs:
            model.objective_SubsurfaceRisk.activate()
            model.config.objective = Objectives.subsurface_risk
        else:
            raise Exception("Subsurface risk objective has not been created")
    elif obj == Objectives.environmental:
        model.objective_Emissions.activate()
        model.config.objective = Objectives.environmental
    else:
        raise Exception("Objective not supported")


def pipeline_hydraulics(model):
    """
    The hydraulics module asssists in computing pressures at each node
    in the network accounting for pressure drop due to friction using
    Hazen-Williams equation and due to elevation change in the topology. This model
    consists of a pressure balance equation for each pipeline and bounds for
    pressure. The objective is to minimize the total cost of installing and operating pumps.
    This method adds a block for hydraulics with all necessary variables and constriants.
    Currently, there are three methods to solve the hydraulics block:
        1) post-process method: only the hydraulics block is solved for pressures
        2) co-optimize method: the hydraulics block is solved along with the network
        3) co-optimize linearized method: a linearized approximation of the co-optimize method
    """
    n_sections = 3
    Del_I = 70000 / n_sections
    cons_scaling_factor = 1e0

    # Create a block to add all variables and constraints for hydraulics within the model
    model.hydraulics = Block()
    mh = model.hydraulics

    # declaring variables and parameters required regardless of the hydraulics method
    mh.p_iota_HW_material_factor_pipeline = Param(
        initialize=130,
        mutable=True,
        units=pyunits.dimensionless,
        doc="Pipeline material factor for Hazen-Williams equation",
    )
    mh.p_rhog = Param(
        initialize=9.8 * 1,
        units=model.model_units["pressure"] / pyunits.meter,
        doc="g (m/s2) * density of PW (assumed to be 1000 kg/m3)",
    )
    mh.p_nu_PumpFixedCost = Param(
        initialize=1,
        mutable=True,
        units=model.model_units["currency"],
        doc="Fixed cost of adding a pump in kUSD",
    )
    mh.p_nu_ElectricityCost = Param(
        initialize=0.1e-3,
        mutable=True,
        doc="Cost of Electricity assumed in kUSD/kWh",
    )
    mh.p_eta_PumpEfficiency = Param(
        initialize=0.9,
        mutable=True,
        doc="Pumps Efficiency",
    )
    mh.p_eta_MotorEfficiency = Param(
        initialize=0.9,
        mutable=True,
        doc="Motor Efficiency of the Pump",
    )
    mh.p_xi_Min_AOP = Param(
        initialize=pyunits.convert_value(
            model.df_parameters["Hydraulics"]["min_allowable_pressure"],
            from_units=model.user_units["pressure"],
            to_units=model.model_units["pressure"],
        ),
        mutable=True,
        units=model.model_units["pressure"],
        doc="Minimum ALlowable Operating Pressure",
    )
    mh.p_xi_Max_AOP = Param(
        initialize=pyunits.convert_value(
            model.df_parameters["Hydraulics"]["max_allowable_pressure"],
            from_units=model.user_units["pressure"],
            to_units=model.model_units["pressure"],
        ),
        mutable=True,
        units=model.model_units["pressure"],
        doc="Maximum ALlowable Operating Pressure",
    )
    mh.p_Initial_Pipeline_Diameter = Param(
        model.s_L,
        model.s_L,
        default=pyunits.convert_value(
            0,
            from_units=model.user_units["diameter"],
            to_units=model.model_units["diameter"],
        ),
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["diameter"],
                to_units=model.model_units["diameter"],
            )
            for key, value in model.df_parameters["InitialPipelineDiameters"].items()
        },
        units=model.model_units["diameter"],
        doc="Initial pipeline diameter [inch]",
    )
    mh.p_upsilon_WellPressure = Param(
        model.s_P,
        model.s_T,
        default=0,
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["pressure"],
                to_units=model.model_units["pressure"],
            )
            for key, value in model.df_parameters["WellPressure"].items()
        },
        units=model.model_units["pressure"],
        doc="Well pressure at production or completions pad [pressure]",
    )
    # ------
    # The folllowing decision variables are intermediate variables that allow piecewise linearization of Hazen-William Equations

    mh.v_term = Var(
        model.s_LLA,
        model.s_T,
        within=NonNegativeReals,
        initialize=0,
        units=model.model_units["volume_time"],
        doc="Produced water quantity piped from location l to location l [volume/time] raised to 1.85",
    )

    # ---------------

    mh.vb_Y_Pump = Var(
        model.s_LLA,
        within=Binary,
        initialize=0,
        doc="Binary variable for fixed cost of Pump",
    )
    mh.v_PumpHead = Var(
        model.s_LLA,
        model.s_T,
        within=NonNegativeReals,
        initialize=0,
        units=pyunits.meter,
        doc="Pump Head added in the direction of flow, m",
    )
    mh.v_ValveHead = Var(
        model.s_LLA,
        model.s_T,
        within=NonNegativeReals,
        initialize=0,
        units=pyunits.meter,
        doc="Valve Head removed in the direction of flow, m",
    )
    mh.v_PumpCost = Var(
        model.s_LLA,
        within=NonNegativeReals,
        initialize=0,
        units=model.model_units["currency"],
        doc="Pump cost",
    )
    mh.v_Pressure = Var(
        model.s_L,
        model.s_T,
        within=NonNegativeReals,
        initialize=mh.p_xi_Min_AOP,
        bounds=(mh.p_xi_Min_AOP, None),
        units=model.model_units["pressure"],
        doc="Pressure at location l at time t in Pa",
    )
    mh.v_Z_HydrualicsCost = Var(
        within=Reals,
        units=model.model_units["currency"],
        doc="Total cost for Pumps and Valves [currency]",
    )

    # if the well pressure are known, i.e., for the production pads or the disposable wells, then fix them
    for p in model.s_P:
        for t in model.s_T:
            if value(mh.p_upsilon_WellPressure[p, t]) > 0:
                mh.v_Pressure[p, t].fix(mh.p_upsilon_WellPressure[p, t])

    # add all necessary constraints
    def MAOPressureRule(b, l1, t1):
        constraint = (
            b.v_Pressure[l1, t1] * cons_scaling_factor
            <= b.p_xi_Max_AOP * cons_scaling_factor
        )
        return process_constraint(constraint)

    mh.MAOPressure = Constraint(
        model.s_L - model.s_P,
        model.s_T,
        rule=MAOPressureRule,
        doc="Max allowable pressure rule",
    )

    def PumpHeadeRule(b, l1, l2):
        constraint = (
            sum(b.v_PumpHead[l1, l2, t] for t in model.s_T)
        ) * cons_scaling_factor <= (
            model.p_M_Flow * mh.vb_Y_Pump[l1, l2]
        ) * cons_scaling_factor
        return process_constraint(constraint)

    mh.PumpHeadCons = Constraint(
        model.s_LLA,
        rule=PumpHeadeRule,
        doc="Pump Head Constraint",
    )

    def HydraulicsCostRule(b):
        constraint = (
            mh.v_Z_HydrualicsCost * cons_scaling_factor
            == (sum((mh.v_PumpCost[key]) for key in model.s_LLA)) * cons_scaling_factor
        )
        return process_constraint(constraint)

    mh.HydraulicsCostEq = Constraint(
        rule=HydraulicsCostRule,
        doc="Total cost for pumps and valves rule",
    )

    if model.config.hydraulics == Hydraulics.post_process:
        """
        For the post process method, the pressure is computed using the
        Hazen-Williams equation in a separate stand alone method "_hazen_williams_head". In this method,
        the hydraulics block is solved alone for the objective of minimizing total cost of pumps.
        """
        mh.p_eff_pipe_diam = Param(
            model.s_LLA,
            default=0,
            initialize=0,
            mutable=True,
            units=model.model_units["diameter"],
            doc="Effective pipeline diameter when two or more pipelines exist between two locations [inch]",
        )
        mh.p_HW_loss = Param(
            model.s_LLA,
            model.s_T,
            default=0,
            initialize=0,
            within=NonNegativeReals,
            mutable=True,
            units=pyunits.meter,
            doc="Hazen-Williams Frictional loss, m",
        )
        for key in model.s_LLA:
            mh.p_eff_pipe_diam[key] = mh.p_Initial_Pipeline_Diameter[key] + value(
                sum(
                    model.vb_y_Pipeline[key, d]
                    * model.df_parameters["PipelineDiameterValues"][d]
                    for d in model.s_D
                )
            )

        # Compute Hazen-Williams head
        for t0 in model.s_T:
            for key in model.s_LLA:
                if value(model.v_F_Piped[key, t0]) > 0.01:
                    if value(mh.p_eff_pipe_diam[key]) > 0.1:
                        mh.p_HW_loss[key, t0] = _hazen_williams_head(
                            mh.p_iota_HW_material_factor_pipeline,
                            pyunits.convert(
                                model.p_lambda_Pipeline[key], to_units=pyunits.meter
                            ),
                            pyunits.convert(
                                mh.p_eff_pipe_diam[key],
                                to_units=pyunits.meter,
                            ),
                            pyunits.convert(
                                model.v_F_Piped[key, t0],
                                to_units=pyunits.m**3 / pyunits.s,
                            ),
                        )

        def NodePressureRule(b, l1, l2, t1):
            if value(model.v_F_Piped[l1, l2, t1]) > 0.01:
                constraint = (
                    b.v_Pressure[l1, t1] + model.p_zeta_Elevation[l1] * mh.p_rhog
                ) * cons_scaling_factor == (
                    b.v_Pressure[l2, t1]
                    + model.p_zeta_Elevation[l2] * mh.p_rhog
                    + b.p_HW_loss[l1, l2, t1] * mh.p_rhog
                    - b.v_PumpHead[l1, l2, t1] * mh.p_rhog
                    + b.v_ValveHead[l1, l2, t1] * mh.p_rhog
                ) * cons_scaling_factor
                return process_constraint(constraint)
            else:
                return Constraint.Skip

        mh.NodePressure = Constraint(
            model.s_LLA,
            model.s_T,
            rule=NodePressureRule,
            doc="Pressure at Node L",
        )

        def PumpCostRule(b, l1, l2):
            constraint = (
                b.v_PumpCost[l1, l2] * cons_scaling_factor
                == (
                    mh.p_nu_PumpFixedCost * mh.vb_Y_Pump[l1, l2]
                    + (
                        (mh.p_nu_ElectricityCost / 3.6e6)
                        * mh.p_rhog
                        * 1e3  # convert the kUSD/kWh to kUSD/Ws
                        * sum(
                            b.v_PumpHead[l1, l2, t]
                            * pyunits.convert_value(
                                value(model.v_F_Piped[l1, l2, t]),
                                from_units=model.model_units["volume_time"],
                                to_units=pyunits.meter**3 / pyunits.h,
                            )
                            for t in model.s_T
                        )
                    )
                )
                * cons_scaling_factor
            )
            return process_constraint(constraint)

        mh.PumpCostEq = Constraint(
            model.s_LLA,
            rule=PumpCostRule,
            doc="Capital Cost of Pump",
        )

        mh.objective = Objective(
            expr=(mh.v_Z_HydrualicsCost),
            sense=minimize,
            doc="Objective function for Hydraulics block",
        )

    elif model.config.hydraulics == Hydraulics.co_optimize:
        """
        For the co-optimize method, the hydraulics block is solved along with
        the network model to optimize the network in the presence of
        hydraulics constraints. The objective is to minimize total cost including
        the cost of pumps.
        """
        # In the co_optimize method the objective should include the cost of pumps. So,
        # deactivate the original objectives to add a modified objective in this method.
        model.objective_Cost.deactivate()
        model.objective_Reuse.deactivate()
        if hasattr(model, "objective_CostSurrogate"):
            model.objective_CostSurrogate.deactivate()
        if model.do_subsurface_risk_calcs:
            model.objective_SubsurfaceRisk.deactivate()

        # add necessary variables and constraints
        mh.v_HW_loss = Var(
            model.s_LLA,
            model.s_T,
            initialize=0,
            within=NonNegativeReals,
            units=pyunits.meter,
            doc="Hazen-Williams Frictional loss, m",
        )
        mh.v_eff_pipe_diam = Var(
            model.s_LLA,
            initialize=0,
            units=model.model_units["diameter"],
            doc="Diameter of pipeline between two locations [inch]",
        )

        def EffectiveDiameterRule(b, l1, l2, t1):
            constraint = mh.v_eff_pipe_diam[l1, l2] == mh.p_Initial_Pipeline_Diameter[
                l1, l2
            ] + sum(
                model.vb_y_Pipeline[l1, l2, d]
                * model.df_parameters["PipelineDiameterValues"][d]
                for d in model.s_D
            )
            return process_constraint(constraint)

        mh.EffectiveDiameter = Constraint(
            model.s_LLA,
            model.s_T,
            rule=EffectiveDiameterRule,
            doc="Pressure at Node L",
        )

        def HazenWilliamsRule(b, l1, l2, t1):
            constraint = (
                b.v_HW_loss[l1, l2, t1]
                * (
                    pyunits.convert(mh.v_eff_pipe_diam[l1, l2], to_units=pyunits.m)
                    ** 4.87
                )
            ) * cons_scaling_factor == (
                10.704
                * (
                    (
                        pyunits.convert(
                            model.v_F_Piped[l1, l2, t1],
                            to_units=pyunits.m**3 / pyunits.s,
                        )
                        / mh.p_iota_HW_material_factor_pipeline
                    )
                    ** 1.85
                )
                * (pyunits.convert(model.p_lambda_Pipeline[l1, l2], to_units=pyunits.m))
            ) * cons_scaling_factor
            return process_constraint(constraint)

        mh.HW_loss_equaltion = Constraint(
            model.s_LLA,
            model.s_T,
            rule=HazenWilliamsRule,
            doc="Pressure at Node L",
        )

        def NodePressureRule(b, l1, l2, t1):
            constraint = (
                b.v_Pressure[l1, t1]
                + model.p_zeta_Elevation[l1] * mh.p_rhog * cons_scaling_factor
                == (
                    b.v_Pressure[l2, t1]
                    + model.p_zeta_Elevation[l2] * mh.p_rhog
                    + b.v_HW_loss[l1, l2, t1] * mh.p_rhog
                    - b.v_PumpHead[l1, l2, t1] * mh.p_rhog
                    + b.v_ValveHead[l1, l2, t1] * mh.p_rhog
                )
                * cons_scaling_factor
            )
            return process_constraint(constraint)

        mh.NodePressure = Constraint(
            model.s_LLA,
            model.s_T,
            rule=NodePressureRule,
            doc="Pressure at Node L",
        )

        def PumpCostRule(b, l1, l2):
            constraint = (
                b.v_PumpCost[l1, l2] * cons_scaling_factor
                == (
                    mh.p_nu_PumpFixedCost * mh.vb_Y_Pump[l1, l2]
                    + (
                        (mh.p_nu_ElectricityCost / 3.6e6)
                        * mh.p_rhog
                        * 1e3  # convert the kUSD/kWh to kUSD/Ws
                        * sum(
                            b.v_PumpHead[l1, l2, t]
                            * pyunits.convert(
                                (model.v_F_Piped[l1, l2, t]),
                                to_units=pyunits.meter**3 / pyunits.h,
                            )
                            for t in model.s_T
                        )
                    )
                )
                * cons_scaling_factor
            )
            return process_constraint(constraint)

        mh.PumpCostEq = Constraint(
            model.s_LLA,
            rule=PumpCostRule,
            doc="Capital Cost of Pump",
        )

        if model.config.objective == Objectives.cost:
            obj_var = model.v_Z
        elif model.config.objective == Objectives.reuse:
            obj_var = model.v_Z_Reuse
        elif model.config.objective == Objectives.cost_surrogate:
            obj_var = model.v_Z_Surrogate
        elif model.config.objective == Objectives.subsurface_risk:
            obj_var = model.v_Z_SubsurfaceRisk
        elif model.config.objective == Objectives.environmental:
            obj_var = model.e_TotalEmissions
        else:
            raise Exception("Objective not supported")

        model.objective = Objective(
            expr=(obj_var + mh.v_Z_HydrualicsCost),
            sense=minimize,
            doc="Objective function",
        )

    elif model.config.hydraulics == Hydraulics.co_optimize_linearized:
        """
        For the co-optimize linearized method, the hydraulics block is solved along with
        the network model to optimize the network in the presence of
        hydraulics constraints. The objective is to minimize total cost including
        the cost of pumps.
        """
        # In the co_optimize method the objective should include the cost of pumps. So,
        # deactivate the original objectives to add a modified objective in this method.
        model.objective_Cost.deactivate()
        model.objective_Reuse.deactivate()
        if hasattr(model, "objective_CostSurrogate"):
            model.objective_CostSurrogate.deactivate()
        if model.do_subsurface_risk_calcs:
            model.objective_SubsurfaceRisk.deactivate()

        # Define sets for the piecewise linear approximation
        model.s_lamset = Set(initialize=list(range(n_sections + 1)))
        model.s_lamset2 = Set(initialize=list(range(n_sections)))
        model.s_zset = Set(initialize=list(range(n_sections)))

        # add necessary variables and constraints
        mh.v_HW_loss = Var(
            model.s_LLA,
            model.s_T,
            initialize=0,
            within=NonNegativeReals,
            units=pyunits.meter,
            doc="Hazen-Williams Frictional loss, m",
        )

        mh.v_variable_pump_cost = Var(
            model.s_LLA,
            model.s_T,
            initialize=0,
            within=NonNegativeReals,
        )

        mh.v_lambdas = Var(
            model.s_LLA,
            model.s_T,
            model.s_lamset,
            within=NonNegativeReals,
            initialize=0,
            doc="Convex combination multipliers",
        )

        mh.vb_z = Var(
            model.s_LLA,
            model.s_T,
            model.s_zset,
            within=Binary,
            initialize=0,
            doc="Convex combination binaries",
        )

        # Add the constraints, starting with the constraints that linearize (piecewise)
        # non-linear flow term in Hazen-William Equation

        def FlowEquationConvRule(b, l1, l2, t1):
            constraint = (
                model.v_F_Piped[l1, l2, t1] * cons_scaling_factor
                == sum(mh.v_lambdas[l1, l2, t1, k] * Del_I * k for k in model.s_lamset)
                * cons_scaling_factor
            )
            return process_constraint(constraint)

        mh.FlowEquationConv = Constraint(
            model.s_LLA,
            model.s_T,
            rule=FlowEquationConvRule,
            doc="Flow at an arc at a time",
        )

        def termEquationConvRule(b, l1, l2, t1):
            constraint = mh.v_term[l1, l2, t1] == sum(
                mh.v_lambdas[l1, l2, t1, k] * (k * Del_I * 1.84 * 10 ** (-6)) ** 1.85
                for k in model.s_lamset
            )
            return process_constraint(constraint)

        mh.termEquationConv = Constraint(
            model.s_LLA,
            model.s_T,
            rule=termEquationConvRule,
            doc="Value of flow to the power 1.85 at the selected flow",
        )

        def EnforceZeroRule(b, i, l1, l2, t1):
            if i == 0:
                constraint = mh.v_lambdas[l1, l2, t1, i] <= mh.vb_z[l1, l2, t1, i]
            elif i == len(model.s_lamset) - 1:
                constraint = mh.v_lambdas[l1, l2, t1, i] <= mh.vb_z[l1, l2, t1, i - 1]
            else:
                constraint = (
                    mh.v_lambdas[l1, l2, t1, i]
                    <= mh.vb_z[l1, l2, t1, i] + mh.vb_z[l1, l2, t1, i - 1]
                )
            return process_constraint(constraint)

        mh.EnforceZero = Constraint(
            model.s_lamset,
            model.s_LLA,
            model.s_T,
            rule=EnforceZeroRule,
            doc="Put appropriate lambda to zero",
        )

        def SumOneRule(b, l1, l2, t1):
            constraint = (
                sum(mh.v_lambdas[l1, l2, t1, j] for j in model.s_lamset)
                * cons_scaling_factor
                == 1 * cons_scaling_factor
            )
            return process_constraint(constraint)

        mh.SumOne = Constraint(
            model.s_LLA,
            model.s_T,
            rule=SumOneRule,
            doc="Lambdas add up to 1",
        )

        def SumOne2Rule(b, l1, l2, t1):
            constraint = (
                sum(mh.vb_z[l1, l2, t1, j] for j in model.s_zset) * cons_scaling_factor
                == 1 * cons_scaling_factor
            )
            return process_constraint(constraint)

        mh.SumOne2 = Constraint(
            model.s_LLA,
            model.s_T,
            rule=SumOne2Rule,
            doc="Lambdas add up to 1",
        )

        # Now define the Hazen William equation in terms of the intermediate variables.
        # v_term2(defined below) gives the product friction pressure drop with binary variable selecting pipe dia

        def HazenWilliamsRule(b, l1, l2, t1):
            # if (l2, l1) in model.s_LLA:
            constraint = (
                (6 * 0.0254) ** 4.87 * b.v_HW_loss[l1, l2, t1]
            ) * cons_scaling_factor == (
                10.704
                * (
                    mh.v_term[l1, l2, t1]
                    / (mh.p_iota_HW_material_factor_pipeline) ** 1.85
                )
                * (pyunits.convert(model.p_lambda_Pipeline[l1, l2], to_units=pyunits.m))
            ) * cons_scaling_factor

            return process_constraint(constraint)

        mh.HW_loss_equaltion = Constraint(
            model.s_LLA,
            model.s_T,
            rule=HazenWilliamsRule,
            doc="Pressure at Node L",
        )

        M_1 = 10**8

        def NodePressure1Rule(b, l1, l2, t1):
            constraint = (
                b.v_Pressure[l1, t1] + model.p_zeta_Elevation[l1] * mh.p_rhog
            ) * cons_scaling_factor >= (
                b.v_Pressure[l2, t1]
                + model.p_zeta_Elevation[l2] * mh.p_rhog
                + b.v_HW_loss[l1, l2, t1] * mh.p_rhog
                - b.v_PumpHead[l1, l2, t1] * mh.p_rhog
                + b.v_ValveHead[l1, l2, t1] * mh.p_rhog
                - M_1 * (1 - model.vb_y_Flow[l1, l2, t1]) * mh.p_rhog
            ) * cons_scaling_factor
            return process_constraint(constraint)

        mh.NodePressure1 = Constraint(
            model.s_LLA,
            model.s_T,
            rule=NodePressure1Rule,
            doc="Pressure at Node L",
        )

        def NodePressure2Rule(b, l1, l2, t1):
            constraint = (
                b.v_Pressure[l1, t1]
                + model.p_zeta_Elevation[l1] * mh.p_rhog * cons_scaling_factor
                <= (
                    b.v_Pressure[l2, t1]
                    + model.p_zeta_Elevation[l2] * mh.p_rhog
                    + b.v_HW_loss[l1, l2, t1] * mh.p_rhog
                    - b.v_PumpHead[l1, l2, t1] * mh.p_rhog
                    + b.v_ValveHead[l1, l2, t1] * mh.p_rhog
                    + M_1 * (1 - model.vb_y_Flow[l1, l2, t1]) * mh.p_rhog
                )
                * cons_scaling_factor
            )
            return process_constraint(constraint)

        mh.NodePressure2 = Constraint(
            model.s_LLA,
            model.s_T,
            rule=NodePressure2Rule,
            doc="Pressure at Node L",
        )

        def VariablePumpCostRule(b, l1, l2, t, i):
            binary_string = bin(i)[2:].zfill(len(model.s_zset))
            binary_list = [int(bit) for bit in binary_string]
            constraint = (
                b.v_variable_pump_cost[l1, l2, t] * cons_scaling_factor
                >= (
                    (
                        (mh.p_nu_ElectricityCost / 3.6e6)
                        * mh.p_rhog
                        * 1e3  # convert the kUSD/kWh to kUSD/Ws
                        * b.v_PumpHead[l1, l2, t]
                        * Del_I
                        * i
                        * 1.84
                        * 10 ** (-6)
                        * 3600
                    )
                    - 20000 * (1 - mh.vb_z[l1, l2, t, i])
                )
                * cons_scaling_factor
            )
            return process_constraint(constraint)

        mh.VariablePumpCost = Constraint(
            model.s_LLA,
            model.s_T,
            model.s_lamset2,
            rule=VariablePumpCostRule,
            doc="Capital Cost of Pump",
        )

        def PumpCostRule(b, l1, l2):
            constraint = (
                b.v_PumpCost[l1, l2] * cons_scaling_factor
                >= (
                    mh.p_nu_PumpFixedCost * mh.vb_Y_Pump[l1, l2]
                    + sum(mh.v_variable_pump_cost[l1, l2, t] for t in model.s_T)
                )
                * cons_scaling_factor
            )
            return process_constraint(constraint)

        mh.PumpCostEq = Constraint(
            model.s_LLA,
            rule=PumpCostRule,
            doc="Capital Cost of Pump",
        )

        if model.config.objective == Objectives.cost:
            obj_var = model.v_Z
        elif model.config.objective == Objectives.reuse:
            obj_var = model.v_Z_Reuse
        elif model.config.objective == Objectives.cost_surrogate:
            obj_var = model.v_Z_Surrogate
        elif model.config.objective == Objectives.subsurface_risk:
            obj_var = model.v_Z_SubsurfaceRisk
        elif model.config.objective == Objectives.environmental:
            obj_var = model.e_TotalEmissions
        else:
            raise Exception("Objective not supported")

        model.objective = Objective(
            expr=(obj_var + mh.v_Z_HydrualicsCost),
            sense=minimize,
            doc="Objective function",
        )

    return model


def _hazen_williams_head(mat_factor, length, diameter, flow):
    """
    Computes Hazen-Williams (HW) head in a pipeline

    Input Args
    ----------
    mat_factor: pipeline material factor for HW equation
    length : length of pipeline segment in m.
    diameter : diameter of pipeline segment in m.
    flow : water flow through the pipeline segment in m3/s.

    Returns
    -------
    hw_friction_head : frictional head loss based on Hazen-Williams rule in m.

    """

    temp_1 = length / (diameter**4.87)
    temp_2 = (flow / mat_factor) ** 1.85
    hw_friction_head = 10.704 * temp_2 * temp_1
    return hw_friction_head


def water_quality(model):
    # region Fix solved Strategic Model variables
    for var in model.component_objects(Var):
        for index in var:
            # Check if the variable is indexed
            if index is None:
                # Check if the value can reasonably be assumed to be non-zero
                if abs(var.value) > 0.0000001:
                    var.fix()
                # Otherwise, fix to 0
                else:
                    var.fix(0)
            elif index is not None:
                # Check if the value can reasonably be assumed to be non-zero
                if var[index].value and abs(var[index].value) > 0.0000001:
                    var[index].fix()
                # Otherwise, fix to 0
                else:
                    var[index].fix(0)
    # endregion

    # Create block for calculating quality at each location in the model
    model.quality = Block()

    # region Add sets, parameters and constraints

    # Create a set for Completions Pad storage by appending the storage label to each item in the CompletionsPads Set
    storage_label = "-storage"
    model.df_sets["CompletionsPadsStorage"] = [
        p + storage_label for p in model.df_sets["CompletionsPads"]
    ]
    model.quality.s_CP_Storage = Set(
        initialize=model.df_sets["CompletionsPadsStorage"],
        doc="Completions Pad Storage Tanks",
    )

    # Create a set for water quality at Completions Pads intermediate flows (i.e. the blended trucked and piped water to pad)
    intermediate_label = "-intermediate"
    model.df_sets["CompletionsPadsIntermediate"] = [
        p + intermediate_label for p in model.df_sets["CompletionsPads"]
    ]
    model.quality.s_CP_Intermediate = Set(
        initialize=model.df_sets["CompletionsPadsIntermediate"],
        doc="Completions Pad Intermediate Flows",
    )
    # Create a set for water quality tracked at the intermediate node between treatment facility and treated water end points
    treated_water_label = "-PostTreatmentTreatedWaterNode"
    model.df_sets["TreatedWaterNodes"] = [
        r + treated_water_label for r in model.df_sets["TreatmentSites"]
    ]
    model.quality.s_R_TreatedWaterNodes = Set(
        initialize=model.df_sets["TreatedWaterNodes"],
        doc="Treated Water Node",
    )

    residual_water_label = "-PostTreatmentResidualNode"
    model.df_sets["ResidualWaterNodes"] = [
        r + residual_water_label for r in model.df_sets["TreatmentSites"]
    ]
    model.quality.s_R_ResidualWaterNodes = Set(
        initialize=model.df_sets["ResidualWaterNodes"],
        doc="Residual Water Node",
    )

    # Create a set of locations to track water quality over
    model.quality.s_WQL = Set(
        initialize=(
            model.s_L
            | model.quality.s_CP_Storage
            | model.quality.s_CP_Intermediate
            | model.quality.s_R_TreatedWaterNodes
            | model.quality.s_R_ResidualWaterNodes
        ),
        doc="Locations with tracked water quality",
    )

    # Quality at pad
    model.quality.p_nu_pad = Param(
        model.s_P,
        model.s_QC,
        default=0,
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["concentration"],
                to_units=model.model_units["concentration"],
            )
            for key, value in model.df_parameters["PadWaterQuality"].items()
        },
        units=model.model_units["concentration"],
        doc="Water Quality at pad [concentration]",
    )
    # Quality of Sourced Water
    model.quality.p_nu_externalwater = Param(
        model.s_F,
        model.s_QC,
        default=0,
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["concentration"],
                to_units=model.model_units["concentration"],
            )
            for key, value in model.df_parameters["ExternalWaterQuality"].items()
        },
        units=model.model_units["concentration"],
        doc="Water Quality of externally sourced water [concentration]",
    )
    # Initial water quality at storage site
    model.quality.p_xi_StorageSite = Param(
        model.s_S,
        model.s_QC,
        default=0,
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["concentration"],
                to_units=model.model_units["concentration"],
            )
            for key, value in model.df_parameters["StorageInitialWaterQuality"].items()
        },
        units=model.model_units["concentration"],
        doc="Initial Water Quality at storage site [concentration]",
    )
    # Initial water quality at completions pad storage tank
    model.quality.p_xi_PadStorage = Param(
        model.s_CP,
        model.s_QC,
        default=0,
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["concentration"],
                to_units=model.model_units["concentration"],
            )
            for key, value in model.df_parameters[
                "PadStorageInitialWaterQuality"
            ].items()
        },
        units=model.model_units["concentration"],
        doc="Initial Water Quality at completions pad storage site [concentration]",
    )
    # Add variable to track water quality at each location over time
    model.quality.v_Q = Var(
        model.quality.s_WQL,
        model.s_QC,
        model.s_T,
        within=NonNegativeReals,
        initialize=0,
        units=model.model_units["concentration"],
        doc="Water quality at location [concentration]",
    )
    # v_X is solely used to make sure model has an objective value
    model.quality.v_X = Var(
        within=Reals,
        units=model.model_units["concentration"],
        doc="Water quality objective value ",
    )
    # endregion

    # region Disposal
    # Material Balance
    def DisposalWaterQualityRule(b, k, qc, t):
        constraint = (
            sum(
                b.parent_block().v_F_Piped[n, k, t] * b.v_Q[n, qc, t]
                for n in b.parent_block().s_N
                if b.parent_block().p_NKA[n, k]
            )
            + sum(
                b.parent_block().v_F_Piped[s, k, t] * b.v_Q[s, qc, t]
                for s in b.parent_block().s_S
                if b.parent_block().p_SKA[s, k]
            )
            + sum(
                b.parent_block().v_F_Trucked[s, k, t] * b.v_Q[s, qc, t]
                for s in b.parent_block().s_S
                if b.parent_block().p_SKT[s, k]
            )
            + sum(
                b.parent_block().v_F_Trucked[p, k, t] * b.p_nu_pad[p, qc]
                for p in b.parent_block().s_PP
                if b.parent_block().p_PKT[p, k]
            )
            + sum(
                b.parent_block().v_F_Trucked[p, k, t] * b.p_nu_pad[p, qc]
                for p in b.parent_block().s_CP
                if b.parent_block().p_CKT[p, k]
            )
            + sum(
                b.parent_block().v_F_Trucked[r, k, t] * b.v_Q[r, qc, t]
                for r in b.parent_block().s_R
                if b.parent_block().p_RKT[r, k]
            )
            == b.v_Q[k, qc, t] * b.parent_block().v_F_DisposalDestination[k, t]
        )
        return process_constraint(constraint)

    model.quality.DisposalWaterQuality = Constraint(
        model.s_K,
        model.s_QC,
        model.s_T,
        rule=DisposalWaterQualityRule,
        doc="Disposal water quality rule",
    )
    # endregion

    # region Storage
    def StorageSiteWaterQualityRule(b, s, qc, t):
        if t == b.parent_block().s_T.first():
            constraint = b.parent_block().p_lambda_Storage[s] * b.p_xi_StorageSite[
                s, qc
            ] + sum(
                b.parent_block().v_F_Piped[n, s, t] * b.v_Q[n, qc, t]
                for n in b.parent_block().s_N
                if b.parent_block().p_NSA[n, s]
            ) + sum(
                b.parent_block().v_F_Piped[r, s, t]
                * b.v_Q[r + treated_water_label, qc, t]
                for r in b.parent_block().s_R
                if b.parent_block().p_RSA[r, s]
            ) + sum(
                b.parent_block().v_F_Trucked[p, s, t] * b.p_nu_pad[p, qc]
                for p in b.parent_block().s_PP
                if b.parent_block().p_PST[p, s]
            ) + sum(
                b.parent_block().v_F_Trucked[p, s, t] * b.p_nu_pad[p, qc]
                for p in b.parent_block().s_CP
                if b.parent_block().p_CST[p, s]
            ) == b.v_Q[
                s, qc, t
            ] * (
                b.parent_block().v_L_Storage[s, t]
                + sum(
                    b.parent_block().v_F_Piped[s, n, t]
                    for n in b.parent_block().s_N
                    if b.parent_block().p_SNA[s, n]
                )
                + sum(
                    b.parent_block().v_F_Piped[s, p, t]
                    for p in b.parent_block().s_CP
                    if b.parent_block().p_SCA[s, p]
                )
                + sum(
                    b.parent_block().v_F_Piped[s, k, t]
                    for k in b.parent_block().s_K
                    if b.parent_block().p_SKA[s, k]
                )
                + sum(
                    b.parent_block().v_F_Piped[s, r, t]
                    for r in b.parent_block().s_R
                    if b.parent_block().p_SRA[s, r]
                )
                + sum(
                    b.parent_block().v_F_Piped[s, o, t]
                    for o in b.parent_block().s_O
                    if b.parent_block().p_SOA[s, o]
                )
                + sum(
                    b.parent_block().v_F_Trucked[s, p, t]
                    for p in b.parent_block().s_CP
                    if b.parent_block().p_SCT[s, p]
                )
                + sum(
                    b.parent_block().v_F_Trucked[s, k, t]
                    for k in b.parent_block().s_K
                    if b.parent_block().p_SKT[s, k]
                )
                + b.parent_block().v_F_StorageEvaporationStream[s, t]
            )
        else:
            constraint = b.parent_block().v_L_Storage[
                s, b.parent_block().s_T.prev(t)
            ] * b.v_Q[s, qc, b.parent_block().s_T.prev(t)] + sum(
                b.parent_block().v_F_Piped[n, s, t] * b.v_Q[n, qc, t]
                for n in b.parent_block().s_N
                if b.parent_block().p_NSA[n, s]
            ) + sum(
                b.parent_block().v_F_Piped[r, s, t]
                * b.v_Q[r + treated_water_label, qc, t]
                for r in b.parent_block().s_R
                if b.parent_block().p_RSA[r, s]
            ) + sum(
                b.parent_block().v_F_Trucked[p, s, t] * b.p_nu_pad[p, qc]
                for p in b.parent_block().s_PP
                if b.parent_block().p_PST[p, s]
            ) + sum(
                b.parent_block().v_F_Trucked[p, s, t] * b.p_nu_pad[p, qc]
                for p in b.parent_block().s_CP
                if b.parent_block().p_CST[p, s]
            ) == b.v_Q[
                s, qc, t
            ] * (
                b.parent_block().v_L_Storage[s, t]
                + sum(
                    b.parent_block().v_F_Piped[s, n, t]
                    for n in b.parent_block().s_N
                    if b.parent_block().p_SNA[s, n]
                )
                + sum(
                    b.parent_block().v_F_Piped[s, p, t]
                    for p in b.parent_block().s_CP
                    if b.parent_block().p_SCA[s, p]
                )
                + sum(
                    b.parent_block().v_F_Piped[s, k, t]
                    for k in b.parent_block().s_K
                    if b.parent_block().p_SKA[s, k]
                )
                + sum(
                    b.parent_block().v_F_Piped[s, r, t]
                    for r in b.parent_block().s_R
                    if b.parent_block().p_SRA[s, r]
                )
                + sum(
                    b.parent_block().v_F_Piped[s, o, t]
                    for o in b.parent_block().s_O
                    if b.parent_block().p_SOA[s, o]
                )
                + sum(
                    b.parent_block().v_F_Trucked[s, p, t]
                    for p in b.parent_block().s_CP
                    if b.parent_block().p_SCT[s, p]
                )
                + sum(
                    b.parent_block().v_F_Trucked[s, k, t]
                    for k in b.parent_block().s_K
                    if b.parent_block().p_SKT[s, k]
                )
                + b.parent_block().v_F_StorageEvaporationStream[s, t]
            )
        return process_constraint(constraint)

    model.quality.StorageSiteWaterQuality = Constraint(
        model.s_S,
        model.s_QC,
        model.s_T,
        rule=StorageSiteWaterQualityRule,
        doc="Storage site water quality rule",
    )
    # endregion

    # region Treatment
    def TreatmentFeedWaterQualityRule(b, r, qc, t):
        constraint = (
            sum(
                b.parent_block().v_F_Piped[n, r, t] * b.v_Q[n, qc, t]
                for n in b.parent_block().s_N
                if b.parent_block().p_NRA[n, r]
            )
            + sum(
                b.parent_block().v_F_Piped[s, r, t] * b.v_Q[s, qc, t]
                for s in b.parent_block().s_S
                if b.parent_block().p_SRA[s, r]
            )
            + sum(
                b.parent_block().v_F_Trucked[p, r, t] * b.p_nu_pad[p, qc]
                for p in b.parent_block().s_PP
                if b.parent_block().p_PRT[p, r]
            )
            + sum(
                b.parent_block().v_F_Trucked[p, r, t] * b.p_nu_pad[p, qc]
                for p in b.parent_block().s_CP
                if b.parent_block().p_CRT[p, r]
            )
        ) == b.v_Q[r, qc, t] * b.parent_block().v_F_TreatmentFeed[r, t]

        return process_constraint(constraint)

    model.quality.TreatmentFeedWaterQuality = Constraint(
        model.s_R,
        model.s_QC,
        model.s_T,
        rule=TreatmentFeedWaterQualityRule,
        doc="Treatment Feed water quality",
    )

    def TreatmentWaterQualityRule(b, r, qc, t):
        constraint = (
            b.v_Q[r, qc, t] * b.parent_block().v_F_TreatmentFeed[r, t]
            == b.v_Q[r + treated_water_label, qc, t]
            * b.parent_block().v_F_TreatedWater[r, t]
            + b.v_Q[r + residual_water_label, qc, t]
            * b.parent_block().v_F_ResidualWater[r, t]
        )

        return process_constraint(constraint)

    model.quality.TreatmentWaterQuality = Constraint(
        model.s_R,
        model.s_QC,
        model.s_T,
        rule=TreatmentWaterQualityRule,
        doc="Treatment water quality",
    )

    def TreatedWaterQualityConcentrationBasedLHSRule(b, r, wt, qc, t):
        if model.config.objective == Objectives.cost_surrogate:
            if b.parent_block().p_chi_DesalinationSites[r]:
                epsilon_value = 0.99
                treatment_selection = b.parent_block().vb_y_DesalSelected[r]
            else:
                epsilon_value = b.parent_block().p_epsilon_TreatmentRemoval[r, wt, qc]
                treatment_selection = sum(
                    b.parent_block().vb_y_Treatment[r, wt, j]
                    for j in b.parent_block().s_J
                )

            constraint = (
                b.v_Q[r, qc, t] * (1 - epsilon_value)
                + b.parent_block().p_M_Concentration * (1 - treatment_selection)
                >= b.v_Q[r + treated_water_label, qc, t]
            )

            return process_constraint(constraint)
        else:
            constraint = (
                b.v_Q[r, qc, t]
                * (1 - b.parent_block().p_epsilon_TreatmentRemoval[r, wt, qc])
                + b.parent_block().p_M_Concentration
                * (
                    1
                    - sum(
                        b.parent_block().vb_y_Treatment[r, wt, j]
                        for j in b.parent_block().s_J
                    )
                )
                >= b.v_Q[r + treated_water_label, qc, t]
            )

            return process_constraint(constraint)

    def TreatedWaterQualityConcentrationBasedRHSRule(b, r, wt, qc, t):
        if model.config.objective == Objectives.cost_surrogate:
            if b.parent_block().p_chi_DesalinationSites[r]:
                epsilon_value = 0.99
                treatment_selection = b.parent_block().vb_y_DesalSelected[r]
            else:
                epsilon_value = b.parent_block().p_epsilon_TreatmentRemoval[r, wt, qc]
                treatment_selection = sum(
                    b.parent_block().vb_y_Treatment[r, wt, j]
                    for j in b.parent_block().s_J
                )

            constraint = (
                b.v_Q[r, qc, t] * (1 - epsilon_value)
                - b.parent_block().p_M_Concentration * (1 - treatment_selection)
                <= b.v_Q[r + treated_water_label, qc, t]
            )

            return process_constraint(constraint)
        else:
            constraint = (
                b.v_Q[r, qc, t]
                * (1 - b.parent_block().p_epsilon_TreatmentRemoval[r, wt, qc])
                - b.parent_block().p_M_Concentration
                * (
                    1
                    - sum(
                        b.parent_block().vb_y_Treatment[r, wt, j]
                        for j in b.parent_block().s_J
                    )
                )
                <= b.v_Q[r + treated_water_label, qc, t]
            )

            return process_constraint(constraint)

    def TreatedWaterQualityLoadBasedLHSRule(b, r, wt, qc, t):
        if model.config.objective == Objectives.cost_surrogate:
            if b.parent_block().p_chi_DesalinationSites[r]:
                epsilon_value = 0.99
                treatment_selection = b.parent_block().vb_y_DesalSelected[r]
            else:
                epsilon_value = b.parent_block().p_epsilon_TreatmentRemoval[r, wt, qc]
                treatment_selection = sum(
                    b.parent_block().vb_y_Treatment[r, wt, j]
                    for j in b.parent_block().s_J
                )

            constraint = (
                b.v_Q[r, qc, t]
                * b.parent_block().v_F_TreatmentFeed[r, t]
                * (1 - epsilon_value)
                + b.parent_block().p_M_Flow_Conc * (1 - treatment_selection)
                >= b.v_Q[r + treated_water_label, qc, t]
                * b.parent_block().v_F_TreatedWater[r, t]
            )

            return process_constraint(constraint)
        else:
            constraint = (
                b.v_Q[r, qc, t]
                * b.parent_block().v_F_TreatmentFeed[r, t]
                * (1 - b.parent_block().p_epsilon_TreatmentRemoval[r, wt, qc])
                + b.parent_block().p_M_Flow_Conc
                * (
                    1
                    - sum(
                        b.parent_block().vb_y_Treatment[r, wt, j]
                        for j in b.parent_block().s_J
                    )
                )
                >= b.v_Q[r + treated_water_label, qc, t]
                * b.parent_block().v_F_TreatedWater[r, t]
            )

            return process_constraint(constraint)

    def TreatedWaterQualityLoadBasedRHSRule(b, r, wt, qc, t):
        if model.config.objective == Objectives.cost_surrogate:
            if b.parent_block().p_chi_DesalinationSites[r]:
                epsilon_value = 0.99
                treatment_selection = b.parent_block().vb_y_DesalSelected[r]
            else:
                epsilon_value = b.parent_block().p_epsilon_TreatmentRemoval[r, wt, qc]
                treatment_selection = sum(
                    b.parent_block().vb_y_Treatment[r, wt, j]
                    for j in b.parent_block().s_J
                )

            constraint = (
                b.v_Q[r, qc, t]
                * b.parent_block().v_F_TreatmentFeed[r, t]
                * (1 - epsilon_value)
                - b.parent_block().p_M_Flow_Conc * (1 - treatment_selection)
                <= b.v_Q[r + treated_water_label, qc, t]
                * b.parent_block().v_F_TreatedWater[r, t]
            )

            return process_constraint(constraint)
        else:
            constraint = (
                b.v_Q[r, qc, t]
                * b.parent_block().v_F_TreatmentFeed[r, t]
                * (1 - b.parent_block().p_epsilon_TreatmentRemoval[r, wt, qc])
                - b.parent_block().p_M_Flow_Conc
                * (
                    1
                    - sum(
                        b.parent_block().vb_y_Treatment[r, wt, j]
                        for j in b.parent_block().s_J
                    )
                )
                <= b.v_Q[r + treated_water_label, qc, t]
                * b.parent_block().v_F_TreatedWater[r, t]
            )

            return process_constraint(constraint)

    if (
        model.config.removal_efficiency_method
        == RemovalEfficiencyMethod.concentration_based
    ):
        model.quality.TreatmentWaterQualityLHS = Constraint(
            model.s_R,
            model.s_WT,
            model.s_QC,
            model.s_T,
            rule=TreatedWaterQualityConcentrationBasedLHSRule,
            doc="Treatment water quality with concentration based removal efficiency",
        )
        model.quality.TreatmentWaterQualityRHS = Constraint(
            model.s_R,
            model.s_WT,
            model.s_QC,
            model.s_T,
            rule=TreatedWaterQualityConcentrationBasedRHSRule,
            doc="Treatment water quality with concentration based removal efficiency",
        )
    elif model.config.removal_efficiency_method == RemovalEfficiencyMethod.load_based:
        model.quality.TreatmentWaterQualityLHS = Constraint(
            model.s_R,
            model.s_WT,
            model.s_QC,
            model.s_T,
            rule=TreatedWaterQualityLoadBasedLHSRule,
            doc="Treatment water quality with load based removal efficiency",
        )
        model.quality.TreatmentWaterQualityRHS = Constraint(
            model.s_R,
            model.s_WT,
            model.s_QC,
            model.s_T,
            rule=TreatedWaterQualityLoadBasedRHSRule,
            doc="Treatment water quality with load based removal efficiency",
        )

    # endregion

    # region Network
    def NetworkNodeWaterQualityRule(b, n, qc, t):
        constraint = sum(
            b.parent_block().v_F_Piped[p, n, t] * b.p_nu_pad[p, qc]
            for p in b.parent_block().s_PP
            if b.parent_block().p_PNA[p, n]
        ) + sum(
            b.parent_block().v_F_Piped[p, n, t] * b.p_nu_pad[p, qc]
            for p in b.parent_block().s_CP
            if b.parent_block().p_CNA[p, n]
        ) + sum(
            b.parent_block().v_F_Piped[s, n, t] * b.v_Q[s, qc, t]
            for s in b.parent_block().s_S
            if b.parent_block().p_SNA[s, n]
        ) + sum(
            b.parent_block().v_F_Piped[n_tilde, n, t] * b.v_Q[n_tilde, qc, t]
            for n_tilde in b.parent_block().s_N
            if b.parent_block().p_NNA[n_tilde, n]
        ) + sum(
            b.parent_block().v_F_Piped[r, n, t] * b.v_Q[r, qc, t]
            for r in b.parent_block().s_R
            if b.parent_block().p_RNA[r, n]
        ) == b.v_Q[
            n, qc, t
        ] * (
            sum(
                b.parent_block().v_F_Piped[n, n_tilde, t]
                for n_tilde in b.parent_block().s_N
                if b.parent_block().p_NNA[n, n_tilde]
            )
            + sum(
                b.parent_block().v_F_Piped[n, p, t]
                for p in b.parent_block().s_CP
                if b.parent_block().p_NCA[n, p]
            )
            + sum(
                b.parent_block().v_F_Piped[n, k, t]
                for k in b.parent_block().s_K
                if b.parent_block().p_NKA[n, k]
            )
            + sum(
                b.parent_block().v_F_Piped[n, r, t]
                for r in b.parent_block().s_R
                if b.parent_block().p_NRA[n, r]
            )
            + sum(
                b.parent_block().v_F_Piped[n, s, t]
                for s in b.parent_block().s_S
                if b.parent_block().p_NSA[n, s]
            )
            + sum(
                b.parent_block().v_F_Piped[n, o, t]
                for o in b.parent_block().s_O
                if b.parent_block().p_NOA[n, o]
            )
        )
        return process_constraint(constraint)

    model.quality.NetworkWaterQuality = Constraint(
        model.s_N,
        model.s_QC,
        model.s_T,
        rule=NetworkNodeWaterQualityRule,
        doc="Network water quality",
    )
    # endregion

    # region Beneficial Reuse
    def BeneficialReuseWaterQuality(b, o, qc, t):
        constraint = (
            sum(
                b.parent_block().v_F_Piped[n, o, t] * b.v_Q[n, qc, t]
                for n in b.parent_block().s_N
                if b.parent_block().p_NOA[n, o]
            )
            + sum(
                b.parent_block().v_F_Piped[s, o, t] * b.v_Q[s, qc, t]
                for s in b.parent_block().s_S
                if b.parent_block().p_SOA[s, o]
            )
            + sum(
                b.parent_block().v_F_Trucked[p, o, t] * b.p_nu_pad[p, qc]
                for p in b.parent_block().s_PP
                if b.parent_block().p_POT[p, o]
            )
            == b.v_Q[o, qc, t] * b.parent_block().v_F_BeneficialReuseDestination[o, t]
        )
        return process_constraint(constraint)

    model.quality.BeneficialReuseWaterQuality = Constraint(
        model.s_O,
        model.s_QC,
        model.s_T,
        rule=BeneficialReuseWaterQuality,
        doc="Beneficial reuse water quality",
    )
    # endregion

    # region Completions Pad

    # Water that is Piped and Trucked to a completions pad is mixed and split into two output streams.
    # Stream (1) goes to the completions pad and stream (2) is input to the completions storage.
    # This is the intermediate step.
    # Finally, water that meets completions demand comes from two inputs.
    # The first input is output stream (1) from the intermediate step.
    # The second is outgoing flow from the storage tank.

    def CompletionsPadIntermediateWaterQuality(b, p, qc, t):
        constraint = sum(
            b.parent_block().v_F_Piped[n, p, t] * b.v_Q[n, qc, t]
            for n in b.parent_block().s_N
            if b.parent_block().p_NCA[n, p]
        ) + sum(
            b.parent_block().v_F_Piped[p_tilde, p, t] * b.v_Q[p_tilde, qc, t]
            for p_tilde in b.parent_block().s_PP
            if b.parent_block().p_PCA[p_tilde, p]
        ) + sum(
            b.parent_block().v_F_Piped[s, p, t] * b.v_Q[s, qc, t]
            for s in b.parent_block().s_S
            if b.parent_block().p_SCA[s, p]
        ) + sum(
            b.parent_block().v_F_Piped[p_tilde, p, t] * b.v_Q[p_tilde, qc, t]
            for p_tilde in b.parent_block().s_CP
            if b.parent_block().p_CCA[p_tilde, p]
        ) + sum(
            b.parent_block().v_F_Piped[r, p, t] * b.v_Q[r + treated_water_label, qc, t]
            for r in b.parent_block().s_R
            if b.parent_block().p_RCA[r, p]
        ) + sum(
            b.parent_block().v_F_Sourced[f, p, t] * b.p_nu_externalwater[f, qc]
            for f in b.parent_block().s_F
            if b.parent_block().p_FCA[f, p]
        ) + sum(
            b.parent_block().v_F_Trucked[p_tilde, p, t] * b.v_Q[p_tilde, qc, t]
            for p_tilde in b.parent_block().s_PP
            if b.parent_block().p_PCT[p_tilde, p]
        ) + sum(
            b.parent_block().v_F_Trucked[p_tilde, p, t] * b.v_Q[p_tilde, qc, t]
            for p_tilde in b.parent_block().s_CP
            if b.parent_block().p_CCT[p_tilde, p]
        ) + sum(
            b.parent_block().v_F_Trucked[s, p, t] * b.v_Q[s, qc, t]
            for s in b.parent_block().s_S
            if b.parent_block().p_SCT[s, p]
        ) + sum(
            b.parent_block().v_F_Trucked[f, p, t] * b.p_nu_externalwater[f, qc]
            for f in b.parent_block().s_F
            if b.parent_block().p_FCT[f, p]
        ) == b.v_Q[
            p + intermediate_label, qc, t
        ] * (
            b.parent_block().v_F_PadStorageIn[p, t]
            + b.parent_block().v_F_CompletionsDestination[p, t]
        )
        return process_constraint(constraint)

    model.quality.CompletionsPadIntermediateWaterQuality = Constraint(
        model.s_CP,
        model.s_QC,
        model.s_T,
        rule=CompletionsPadIntermediateWaterQuality,
        doc="Completions pad intermediate node water quality",
    )

    def CompletionsPadWaterQuality(b, p, qc, t):
        constraint = (
            b.parent_block().v_F_PadStorageOut[p, t] * b.v_Q[p + storage_label, qc, t]
            + b.parent_block().v_F_CompletionsDestination[p, t]
            * b.v_Q[p + intermediate_label, qc, t]
            == b.v_Q[p, qc, t] * b.parent_block().p_gamma_Completions[p, t]
        )
        return process_constraint(constraint)

    model.quality.CompletionsPadWaterQuality = Constraint(
        model.s_CP,
        model.s_QC,
        model.s_T,
        rule=CompletionsPadWaterQuality,
        doc="Completions pad water quality",
    )
    # endregion

    # region Completion Pad Storage
    def CompletionsPadStorageWaterQuality(b, p, qc, t):
        if t == b.parent_block().s_T.first():
            constraint = b.p_xi_PadStorage[
                p, qc
            ] * b.parent_block().p_lambda_PadStorage[p] + b.v_Q[
                p + intermediate_label, qc, t
            ] * b.parent_block().v_F_PadStorageIn[
                p, t
            ] == b.v_Q[
                p + storage_label, qc, t
            ] * (
                b.parent_block().v_L_PadStorage[p, t]
                + b.parent_block().v_F_PadStorageOut[p, t]
            )
        else:
            constraint = b.v_Q[
                p + storage_label, qc, b.parent_block().s_T.prev(t)
            ] * b.parent_block().v_L_PadStorage[
                p, b.parent_block().s_T.prev(t)
            ] + b.v_Q[
                p + intermediate_label, qc, t
            ] * b.parent_block().v_F_PadStorageIn[
                p, t
            ] == b.v_Q[
                p + storage_label, qc, t
            ] * (
                b.parent_block().v_L_PadStorage[p, t]
                + b.parent_block().v_F_PadStorageOut[p, t]
            )
        return process_constraint(constraint)

    model.quality.CompletionsPadStorageWaterQuality = Constraint(
        model.s_CP,
        model.s_QC,
        model.s_T,
        rule=CompletionsPadStorageWaterQuality,
        doc="Completions pad storage water quality",
    )
    # endregion

    # Define Objective
    def ObjectiveFunctionRule(b):
        return b.v_X == sum(
            sum(
                sum(b.v_Q[p, qc, t] for p in b.parent_block().s_P)
                for qc in b.parent_block().s_QC
            )
            for t in b.parent_block().s_T
        )

    model.quality.ObjectiveFunction = Constraint(
        rule=ObjectiveFunctionRule, doc="Objective function water quality"
    )

    model.quality.objective = Objective(
        expr=model.quality.v_X, sense=minimize, doc="Objective function"
    )

    return model


def discretize_water_quality(df_parameters, df_sets, discrete_qualities) -> dict:
    discrete_quality = dict()

    for quality_component in df_sets["WaterQualityComponents"]:
        # Find the minimum and maximum quality for the quality component
        qualities_for_component_for_pad = [
            value
            for key, value in df_parameters["PadWaterQuality"].items()
            if key[1] == quality_component
        ]
        qualities_for_component_for_storage = [
            value
            for key, value in df_parameters["StorageInitialWaterQuality"].items()
            if key[1] == quality_component
        ]
        qualities_for_component = (
            qualities_for_component_for_pad + qualities_for_component_for_storage
        )
        min_quality = min(qualities_for_component)
        max_quality = max(qualities_for_component)
        # Discretize linear between the min and max quality based on the number of discrete qualities.
        for i, value in enumerate(
            np.linspace(min_quality, max_quality, len(discrete_qualities))
        ):
            discrete_quality[(quality_component, discrete_qualities[i])] = float(value)
    return discrete_quality


def discrete_water_quality_list(steps=6) -> list:
    discrete_qualities = []
    # Create list ["Q0", "Q1", ... , "QN"] qualities based on the number of steps.
    for i in range(0, steps):
        discrete_qualities.append("Q{0}".format(i))
    return discrete_qualities


def get_max_value_for_parameter(parameter):
    return max([x.value for x in parameter.values()])


def water_quality_discrete(model, df_parameters, df_sets):
    # Add sets, parameters and constraints

    # Create a set for Completions Pad storage by appending "-storage" to each item in the CompletionsPads Set
    storage_label = "-storage"
    df_sets["CompletionsPadsStorage"] = [
        p + storage_label for p in df_sets["CompletionsPads"]
    ]
    model.s_CP_Storage = Set(
        initialize=df_sets["CompletionsPadsStorage"],
        doc="Completions Pad Storage Tanks",
    )

    # Create a set for water quality tracked at the intermediate node between treatment facility and treated water end points
    treatment_intermediate_label = "-PostTreatmentIntermediateNode"
    model.df_sets["TreatedWaterIntermediateNodes"] = [
        r + treatment_intermediate_label for r in model.df_sets["TreatmentSites"]
    ]
    model.s_R_TreatedWaterIntermediateNode = Set(
        initialize=model.df_sets["TreatedWaterIntermediateNodes"],
        doc="Treated Water Node",
    )

    # Create a set for water quality at Completions Pads intermediate flows (i.e. the blended trucked and piped water to pad)
    intermediate_label = "-intermediate"
    df_sets["CompletionsPadsIntermediate"] = [
        p + intermediate_label for p in df_sets["CompletionsPads"]
    ]
    model.s_CP_Intermediate = Set(
        initialize=df_sets["CompletionsPadsIntermediate"],
        doc="Completions Pad Intermediate Flows",
    )

    # Quality at pad
    model.p_nu_pad = Param(
        model.s_P,
        model.s_QC,
        default=0,
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["concentration"],
                to_units=model.model_units["concentration"],
            )
            for key, value in model.df_parameters["PadWaterQuality"].items()
        },
        units=model.model_units["concentration"],
        doc="Water Quality at pad [concentration]",
    )
    # Quality of Sourced Water
    model.p_nu_externalwater = Param(
        model.s_F,
        model.s_QC,
        default=0,
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["concentration"],
                to_units=model.model_units["concentration"],
            )
            for key, value in model.df_parameters["ExternalWaterQuality"].items()
        },
        units=model.model_units["concentration"],
        doc="Water Quality of externally sourced water [concentration]",
    )
    # Initial water quality at storage site
    model.p_xi_StorageSite = Param(
        model.s_S,
        model.s_QC,
        default=0,
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["concentration"],
                to_units=model.model_units["concentration"],
            )
            for key, value in model.df_parameters["StorageInitialWaterQuality"].items()
        },
        units=model.model_units["concentration"],
        doc="Initial Water Quality at storage site [concentration]",
    )
    # Initial water quality at completions pad storage tank
    model.p_xi_PadStorage = Param(
        model.s_CP,
        model.s_QC,
        default=0,
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["concentration"],
                to_units=model.model_units["concentration"],
            )
            for key, value in model.df_parameters[
                "PadStorageInitialWaterQuality"
            ].items()
        },
        units=model.model_units["concentration"],
        doc="Initial Water Quality at storage site [concentration]",
    )

    # region discretization

    # Create list of discretized qualities
    discrete_quality_list = discrete_water_quality_list(6)

    # Create set with the list of discretized qualities
    model.s_Q = Set(initialize=discrete_quality_list, doc="Discrete water qualities")

    discrete_water_qualities = discretize_water_quality(
        df_parameters, df_sets, discrete_quality_list
    )
    # Initialize values for each discrete quality
    model.p_discrete_quality = Param(
        model.s_QC,
        model.s_Q,
        initialize={
            key: pyunits.convert_value(
                float(value),
                from_units=model.user_units["concentration"],
                to_units=model.model_units["concentration"],
            )
            for key, value in discrete_water_qualities.items()
        },
        units=model.model_units["concentration"],
        doc="Discretization of water components",
    )

    # For the discretization we need a upperbound for the maximum number of trucks for each truck flow
    model.p_max_number_of_trucks = Param(
        initialize=500,
        mutable=True,
        doc="Max number of trucks. Needed for upperbound on v_F_Trucked",
    )

    # Create sets for location to location arcs where the quality for the from location is variable.
    # This excludes the production pads and external water sources because the quality is known.
    model.s_NonPLP = Set(
        initialize=[
            NonFromPPipelines
            for NonFromPPipelines in model.s_LLA
            if not NonFromPPipelines[0] in (model.s_P | model.s_F)
        ],
        doc="location-to-location with discrete quality piping arcs",
    )
    model.s_NonPLT = Set(
        initialize=[
            NonFromPTrucks
            for NonFromPTrucks in model.s_LLT
            if not NonFromPTrucks[0] in (model.s_P | model.s_F)
        ],
        doc="location-to-location with discrete quality trucking arcs",
    )

    # All locations where the quality is variable. This excludes the production pads and external water sources
    model.s_QL = Set(
        initialize=(
            model.s_K
            | model.s_S
            | model.s_R
            | model.s_O
            | model.s_N
            | model.s_CP_Storage
            | model.s_CP_Intermediate
            | model.s_R_TreatedWaterIntermediateNode
        ),
        doc="Locations with discrete quality",
    )

    def SetZToMax(model, l, t, qc, q):
        # Set initial value for discrete quality to max value. This is for setting initial solution.
        if q == discrete_quality_list[-1]:
            return 1
        return 0

    model.v_DQ = Var(
        model.s_QL,
        model.s_T,
        model.s_QC,
        model.s_Q,
        within=Binary,
        initialize=SetZToMax,
        doc="Discrete quality at location ql at time t for component w",
    )

    model.OnlyOneDiscreteQualityPerLocation = Constraint(
        model.s_QL,
        model.s_T,
        model.s_QC,
        rule=lambda model, l, t, qc: sum(model.v_DQ[l, t, qc, q] for q in model.s_Q)
        == 1,
        doc="Only one discrete quality can be chosen",
    )

    def DiscretizePipeFlowQuality(model):
        model.v_F_DiscretePiped = Var(
            model.s_NonPLP,
            model.s_T,
            model.s_QC,
            model.s_Q,
            within=NonNegativeReals,
            units=model.model_units["volume_time"],
            initialize=0,
            doc="Produced water quantity piped from location l to location l for each quality component qc and discretized quality q [volume/time]",
        )

        model.DiscreteMaxPipeFlow = Constraint(
            model.s_NonPLP,
            model.s_T,
            model.s_QC,
            model.s_Q,
            rule=lambda model, l, l_tilde, t, qc, q: model.v_F_DiscretePiped[
                l, l_tilde, t, qc, q
            ]
            <= (
                model.p_sigma_Pipeline[l, l_tilde]
                + get_max_value_for_parameter(model.p_delta_Pipeline)
            )
            * model.v_DQ[l, t, qc, q],
            doc="Only one flow can be non-zero for quality component qc and all discretized quality q",
        )

        model.SumDiscreteFlowsIsFlowPiped = Constraint(
            model.s_NonPLP,
            model.s_T,
            model.s_QC,
            rule=lambda model, l, l_tilde, t, qc: sum(
                model.v_F_DiscretePiped[l, l_tilde, t, qc, q] for q in model.s_Q
            )
            == model.v_F_Piped[l, l_tilde, t],
            doc="Sum for each flow for component qc equals the produced water quantity piped from location l to location l ",
        )

    def DiscretizeTruckedFlowQuality(model):
        model.v_F_DiscreteTrucked = Var(
            model.s_NonPLT,
            model.s_T,
            model.s_QC,
            model.s_Q,
            within=NonNegativeReals,
            units=model.model_units["volume_time"],
            initialize=0,
            doc="Produced water quantity trucked from location l to location l for each quality component qc and discretized quality q [volume/time]",
        )

        model.DiscreteMaxTruckedFlow = Constraint(
            model.s_NonPLT,
            model.s_T,
            model.s_QC,
            model.s_Q,
            rule=lambda model, l, l_tilde, t, qc, q: model.v_F_DiscreteTrucked[
                l, l_tilde, t, qc, q
            ]
            <= (model.p_delta_Truck * model.p_max_number_of_trucks)
            * model.v_DQ[l, t, qc, q],
            doc="Only one flow can be non-zero for quality component qc and all discretized quality q",
        )

        model.SumDiscreteFlowsIsFlowTrucked = Constraint(
            model.s_NonPLT,
            model.s_T,
            model.s_QC,
            rule=lambda model, l, l_tilde, t, qc: sum(
                model.v_F_DiscreteTrucked[l, l_tilde, t, qc, q] for q in model.s_Q
            )
            == model.v_F_Trucked[l, l_tilde, t],
            doc="Sum for each flow for component qc equals the produced water quantity trucked from location l to location l",
        )

    def DiscretizeDisposalDestinationQuality(model):
        model.v_F_DiscreteDisposalDestination = Var(
            model.s_K,
            model.s_T,
            model.s_QC,
            model.s_Q,
            within=NonNegativeReals,
            units=model.model_units["volume_time"],
            doc="Produced water quantity at disposal k for each quality component qc and discretized quality q [volume/time]",
        )

        model.DiscreteMaxDisposalDestination = Constraint(
            model.s_K,
            model.s_T,
            model.s_QC,
            model.s_Q,
            rule=lambda model, k, t, qc, q: model.v_F_DiscreteDisposalDestination[
                k, t, qc, q
            ]
            <= (
                model.p_sigma_Disposal[k]
                + get_max_value_for_parameter(model.p_delta_Disposal)
            )
            * model.v_DQ[k, t, qc, q],
            doc="Only one quantity at disposal can be non-zero for quality component qc and all discretized quality q",
        )

        model.SumDiscreteDisposalDestinationIsDisposalDestination = Constraint(
            model.s_K,
            model.s_T,
            model.s_QC,
            rule=lambda model, k, t, qc: sum(
                model.v_F_DiscreteDisposalDestination[k, t, qc, q] for q in model.s_Q
            )
            == model.v_F_DisposalDestination[k, t],
            doc="The sum of discretized quality q for disposal destination k equals the disposal destination k",
        )

    def DiscretizeOutStorageQuality(model):
        model.v_F_DiscreteFlowOutStorage = Var(
            model.s_S,
            model.s_T,
            model.s_QC,
            model.s_Q,
            within=NonNegativeReals,
            units=model.model_units["volume_time"],
            doc="Produced water quantity out of storage site s for each quality component qc and discretized quality q [volume/time]",
        )

        model.DiscreteMaxOutStorageFlow = Constraint(
            model.s_S,
            model.s_T,
            model.s_QC,
            model.s_Q,
            rule=lambda model, s, t, qc, q: model.v_F_DiscreteFlowOutStorage[
                s, t, qc, q
            ]
            <= (
                model.p_sigma_Storage[s]
                + sum(
                    model.p_sigma_Pipeline[s, n]
                    + get_max_value_for_parameter(model.p_delta_Pipeline)
                    for n in model.s_N
                    if model.p_SNA[s, n]
                )
                + sum(
                    model.p_sigma_Pipeline[s, p]
                    + get_max_value_for_parameter(model.p_delta_Pipeline)
                    for p in model.s_CP
                    if model.p_SCA[s, p]
                )
                + sum(
                    model.p_sigma_Pipeline[s, k]
                    + get_max_value_for_parameter(model.p_delta_Pipeline)
                    for k in model.s_K
                    if model.p_SKA[s, k]
                )
                + sum(
                    model.p_sigma_Pipeline[s, r]
                    + get_max_value_for_parameter(model.p_delta_Pipeline)
                    for r in model.s_R
                    if model.p_SRA[s, r]
                )
                + sum(
                    model.p_sigma_Pipeline[s, o]
                    + get_max_value_for_parameter(model.p_delta_Pipeline)
                    for o in model.s_O
                    if model.p_SOA[s, o]
                )
                + sum(
                    (model.p_delta_Truck * model.p_max_number_of_trucks)
                    for p in model.s_CP
                    if model.p_SCT[s, p]
                )
                + sum(
                    (model.p_delta_Truck * model.p_max_number_of_trucks)
                    for k in model.s_K
                    if model.p_SKT[s, k]
                )
            )
            * model.v_DQ[s, t, qc, q],
            doc="Only one outflow for storage site s can be non-zero for quality component qc and all discretized quality q",
        )

        model.SumDiscreteFlowsIsFlowOutStorage = Constraint(
            model.s_S,
            model.s_T,
            model.s_QC,
            rule=lambda model, s, t, qc: sum(
                model.v_F_DiscreteFlowOutStorage[s, t, qc, q] for q in model.s_Q
            )
            == (
                model.v_L_Storage[s, t]
                + sum(model.v_F_Piped[s, n, t] for n in model.s_N if model.p_SNA[s, n])
                + sum(model.v_F_Piped[s, p, t] for p in model.s_CP if model.p_SCA[s, p])
                + sum(model.v_F_Piped[s, k, t] for k in model.s_K if model.p_SKA[s, k])
                + sum(model.v_F_Piped[s, r, t] for r in model.s_R if model.p_SRA[s, r])
                + sum(model.v_F_Piped[s, o, t] for o in model.s_O if model.p_SOA[s, o])
                + sum(
                    model.v_F_Trucked[s, p, t] for p in model.s_CP if model.p_SCT[s, p]
                )
                + sum(
                    model.v_F_Trucked[s, k, t] for k in model.s_K if model.p_SKT[s, k]
                )
                + model.v_F_StorageEvaporationStream[s, t]
            ),
            doc="The sum of discretized outflows at storage site s equals the total outflow for storage site s",
        )

    def DiscretizeStorageQuality(model):
        model.v_L_DiscreteStorage = Var(
            model.s_S,
            model.s_T,
            model.s_QC,
            model.s_Q,
            within=NonNegativeReals,
            units=model.model_units["volume"],
            doc="Produced water quantity at storage site s for each quality component qc and discretized quality q [volume]",
        )

        model.DiscreteMaxStorage = Constraint(
            model.s_S,
            model.s_T,
            model.s_QC,
            model.s_Q,
            rule=lambda model, s, t, qc, q: model.v_L_DiscreteStorage[s, t, qc, q]
            <= (
                model.p_sigma_Storage[s]
                + get_max_value_for_parameter(model.p_delta_Storage)
            )
            * model.v_DQ[s, t, qc, q],
            doc="Only one quantity for storage site s can be non-zero for quality component qc and all discretized quality q",
        )

        model.SumDiscreteStorageIsStorage = Constraint(
            model.s_S,
            model.s_T,
            model.s_QC,
            rule=lambda model, s, t, qc: sum(
                model.v_L_DiscreteStorage[s, t, qc, q] for q in model.s_Q
            )
            == model.v_L_Storage[s, t],
            doc="The sum of discretized quantities at storage site s equals the total quantity for storage site s",
        )

    def DiscretizeTreatmentQuality(model):
        model.v_F_DiscreteFlowTreatment = Var(
            model.s_R,
            model.s_T,
            model.s_QC,
            model.s_Q,
            within=NonNegativeReals,
            units=model.model_units["volume_time"],
            doc="Produced water quantity at treatment site r for each quality component qc and discretized quality q [volume/time]",
        )

        model.DiscreteMaxTreatmentFlow = Constraint(
            model.s_R,
            model.s_T,
            model.s_QC,
            model.s_Q,
            rule=lambda model, r, t, qc, q: model.v_F_DiscreteFlowTreatment[r, t, qc, q]
            <= (
                get_max_value_for_parameter(model.p_sigma_Treatment)
                + get_max_value_for_parameter(model.p_delta_Treatment)
            )
            * model.v_DQ[r, t, qc, q],
            doc="Only one quantity for treatment site r can be non-zero for quality component qc and all discretized quality q",
        )

        model.SumDiscreteFlowsIsFlowTreatment = Constraint(
            model.s_R,
            model.s_T,
            model.s_QC,
            rule=lambda model, r, t, qc: sum(
                model.v_F_DiscreteFlowTreatment[r, t, qc, q] for q in model.s_Q
            )
            == (model.v_F_ResidualWater[r, t] + model.v_F_TreatedWater[r, t]),
            doc="The sum of discretized quantities at treatment site r equals the total quantity for treatment site r",
        )

    def DiscretizeFlowOutNodeQuality(model):
        model.v_F_DiscreteFlowOutNode = Var(
            model.s_N,
            model.s_T,
            model.s_QC,
            model.s_Q,
            within=NonNegativeReals,
            units=model.model_units["volume_time"],
            doc="Produced water quantity out of node n for each quality component qc and discretized quality q [volume/time]",
        )

        model.DiscreteMaxOutNodeFlow = Constraint(
            model.s_N,
            model.s_T,
            model.s_QC,
            model.s_Q,
            rule=lambda model, n, t, qc, q: model.v_F_DiscreteFlowOutNode[n, t, qc, q]
            <= (
                sum(
                    model.p_sigma_Pipeline[n, n_tilde]
                    + get_max_value_for_parameter(model.p_delta_Pipeline)
                    for n_tilde in model.s_N
                    if model.p_NNA[n, n_tilde]
                )
                + sum(
                    model.p_sigma_Pipeline[n, p]
                    + get_max_value_for_parameter(model.p_delta_Pipeline)
                    for p in model.s_CP
                    if model.p_NCA[n, p]
                )
                + sum(
                    model.p_sigma_Pipeline[n, k]
                    + get_max_value_for_parameter(model.p_delta_Pipeline)
                    for k in model.s_K
                    if model.p_NKA[n, k]
                )
                + sum(
                    model.p_sigma_Pipeline[n, r]
                    + get_max_value_for_parameter(model.p_delta_Pipeline)
                    for r in model.s_R
                    if model.p_NRA[n, r]
                )
                + sum(
                    model.p_sigma_Pipeline[n, s]
                    + get_max_value_for_parameter(model.p_delta_Pipeline)
                    for s in model.s_S
                    if model.p_NSA[n, s]
                )
                + sum(
                    model.p_sigma_Pipeline[n, o]
                    + get_max_value_for_parameter(model.p_delta_Pipeline)
                    for o in model.s_O
                    if model.p_NOA[n, o]
                )
            )
            * model.v_DQ[n, t, qc, q],
            doc="Only one outflow for node n can be non-zero for quality component qc and all discretized quality q",
        )

        model.SumDiscreteFlowsIsFlowOutNode = Constraint(
            model.s_N,
            model.s_T,
            model.s_QC,
            rule=lambda model, n, t, qc: sum(
                model.v_F_DiscreteFlowOutNode[n, t, qc, q] for q in model.s_Q
            )
            == (
                sum(
                    model.v_F_Piped[n, n_tilde, t]
                    for n_tilde in model.s_N
                    if model.p_NNA[n, n_tilde]
                )
                + sum(model.v_F_Piped[n, p, t] for p in model.s_CP if model.p_NCA[n, p])
                + sum(model.v_F_Piped[n, k, t] for k in model.s_K if model.p_NKA[n, k])
                + sum(model.v_F_Piped[n, r, t] for r in model.s_R if model.p_NRA[n, r])
                + sum(model.v_F_Piped[n, s, t] for s in model.s_S if model.p_NSA[n, s])
                + sum(model.v_F_Piped[n, o, t] for o in model.s_O if model.p_NOA[n, o])
            ),
            doc="The sum of discretized outflows at node n equals the total outflow for node n",
        )

    def DiscretizeBeneficialReuseQuality(model):
        model.v_F_DiscreteBRDestination = Var(
            model.s_O,
            model.s_T,
            model.s_QC,
            model.s_Q,
            within=NonNegativeReals,
            units=model.model_units["volume_time"],
            doc="Produced water quantity at beneficial reuse destination o for each quality component qc and discretized quality q [volume/time]",
        )

        model.DiscreteMaxBeneficialReuseFlow = Constraint(
            model.s_O,
            model.s_T,
            model.s_QC,
            model.s_Q,
            rule=lambda model, o, t, qc, q: model.v_F_DiscreteBRDestination[o, t, qc, q]
            <= (
                sum(
                    model.p_sigma_Pipeline[n, o]
                    + get_max_value_for_parameter(model.p_delta_Pipeline)
                    for n in model.s_N
                    if model.p_NOA[n, o]
                )
                + sum(
                    model.p_sigma_Pipeline[s, o]
                    + get_max_value_for_parameter(model.p_delta_Pipeline)
                    for s in model.s_S
                    if model.p_SOA[s, o]
                )
                + sum(
                    (model.p_delta_Truck * model.p_max_number_of_trucks)
                    for p in model.s_PP
                    if model.p_POT[p, o]
                )
            )
            * model.v_DQ[o, t, qc, q],
            doc="Only one quantity for beneficial reuse destination o can be non-zero for quality component qc and all discretized quality q",
        )

        model.SumDiscreteFlowsIsFlowBeneficialReuse = Constraint(
            model.s_O,
            model.s_T,
            model.s_QC,
            rule=lambda model, o, t, qc: sum(
                model.v_F_DiscreteBRDestination[o, t, qc, q] for q in model.s_Q
            )
            == model.v_F_BeneficialReuseDestination[o, t],
            doc="The sum of discretized quantities at beneficial reuse destination o equals the total quantity for beneficial reuse destination o",
        )

    def DiscretizeCompletionsPadIntermediateQuality(model):
        model.v_F_DiscreteFlowCPIntermediate = Var(
            model.s_CP,
            model.s_T,
            model.s_QC,
            model.s_Q,
            within=NonNegativeReals,
            units=model.model_units["volume_time"],
            doc="Produced water quantity flowing out of intermediate at completion pad cp for each quality component qc and discretized quality q [volume/time]",
        )

        model.DiscreteMaxCompletionsPadIntermediateFlow = Constraint(
            model.s_CP,
            model.s_T,
            model.s_QC,
            model.s_Q,
            rule=lambda model, p, t, qc, q: model.v_F_DiscreteFlowCPIntermediate[
                p, t, qc, q
            ]
            <= (model.p_gamma_Completions[p, t] + model.p_sigma_PadStorage[p])
            * model.v_DQ[p + intermediate_label, t, qc, q],
            doc="Only one quantity for flowing out of intermediate at completion pad cp can be non-zero for quality component qc and all discretized quality q",
        )

        model.SumDiscreteFlowsIsFlowCompletionsPadIntermediate = Constraint(
            model.s_CP,
            model.s_T,
            model.s_QC,
            rule=lambda model, p, t, qc: sum(
                model.v_F_DiscreteFlowCPIntermediate[p, t, qc, q] for q in model.s_Q
            )
            == model.v_F_PadStorageIn[p, t] + model.v_F_CompletionsDestination[p, t],
            doc="The sum of discretized quantities for flowing out of intermediate at completion pad cp equals the total quantity for flowing out of intermediate at completion pad cp",
        )

    def DiscretizeCompletionsPadStorageQuality(model):
        model.v_F_DiscreteFlowCPStorage = Var(
            model.s_CP,
            model.s_T,
            model.s_QC,
            model.s_Q,
            within=NonNegativeReals,
            units=model.model_units["volume_time"],
            doc="Produced water quantity at pad storage at completion pad cp for each quality component qc and discretized quality q [volume/time]",
        )

        model.DiscreteMaxCompletionsPadStorageFlow = Constraint(
            model.s_CP,
            model.s_T,
            model.s_QC,
            model.s_Q,
            rule=lambda model, p, t, qc, q: model.v_F_DiscreteFlowCPStorage[p, t, qc, q]
            <= (model.p_gamma_Completions[p, t] + model.p_sigma_PadStorage[p])
            * model.v_DQ[p + storage_label, t, qc, q],
            doc="Only one quantity at pad storage at completion pad cp can be non-zero for quality component qc and all discretized quality q",
        )

        model.SumDiscreteFlowsIsFlowCompletionsPadStorage = Constraint(
            model.s_CP,
            model.s_T,
            model.s_QC,
            rule=lambda model, p, t, qc: sum(
                model.v_F_DiscreteFlowCPStorage[p, t, qc, q] for q in model.s_Q
            )
            == model.v_L_PadStorage[p, t] + model.v_F_PadStorageOut[p, t],
            doc="The sum of discretized quantities at pad storage at completion pad cp equals the total quantity at pad storage at completion pad cp",
        )

    def DiscretizePadStorageQuality(model):
        model.v_L_DiscretePadStorage = Var(
            model.s_CP,
            model.s_T,
            model.s_QC,
            model.s_Q,
            within=NonNegativeReals,
            units=model.model_units["volume"],
            doc="Produced water quantity at pad storage for completion pad cp for each quality component qc and discretized quality q [volume/time]",
        )

        model.DiscreteMaxPadStorage = Constraint(
            model.s_CP,
            model.s_T,
            model.s_QC,
            model.s_Q,
            rule=lambda model, p, t, qc, q: model.v_L_DiscretePadStorage[p, t, qc, q]
            <= (model.p_sigma_PadStorage[p]) * model.v_DQ[p + storage_label, t, qc, q],
            doc="Only one quantity at pad storage for completion pad cp can be non-zero for quality component qc and all discretized quality q",
        )

        model.SumDiscretePadStorageIsPadStorage = Constraint(
            model.s_CP,
            model.s_T,
            model.s_QC,
            rule=lambda model, p, t, qc: sum(
                model.v_L_DiscretePadStorage[p, t, qc, q] for q in model.s_Q
            )
            == model.v_L_PadStorage[p, t],
            doc="The sum of discretized quantities at pad storage for completion pad cp equals the total quantity at pad storage for completion pad cp",
        )

    def DiscretizeFlowOutPadStorageQuality(model):
        model.v_F_DiscreteFlowOutPadStorage = Var(
            model.s_CP,
            model.s_T,
            model.s_QC,
            model.s_Q,
            within=NonNegativeReals,
            units=model.model_units["volume_time"],
            doc="Produced water quantity out of padstorage at completion pad cp for each quality component qc and discretized quality q [volume/time]",
        )

        model.DiscreteMaxFlowOutPadStorage = Constraint(
            model.s_CP,
            model.s_T,
            model.s_QC,
            model.s_Q,
            rule=lambda model, p, t, qc, q: model.v_F_DiscreteFlowOutPadStorage[
                p, t, qc, q
            ]
            <= (model.p_sigma_PadStorage[p]) * model.v_DQ[p + storage_label, t, qc, q],
            doc="Only one outflow for padstorage at completion pad cp can be non-zero for quality component qc and all discretized quality q",
        )

        model.SumDiscreteFlowOutPadStorageIsFlowOutPadStorage = Constraint(
            model.s_CP,
            model.s_T,
            model.s_QC,
            rule=lambda model, p, t, qc: sum(
                model.v_F_DiscreteFlowOutPadStorage[p, t, qc, q] for q in model.s_Q
            )
            == model.v_F_PadStorageOut[p, t],
            doc="The sum of discretized outflows at padstorage at completion pad cp equals the total outflow for padstorage at completion pad cp",
        )

    def DiscretizeFlowInPadStorageQuality(model):
        model.v_F_DiscreteFlowInPadStorage = Var(
            model.s_CP,
            model.s_T,
            model.s_QC,
            model.s_Q,
            within=NonNegativeReals,
            units=model.model_units["volume_time"],
            doc="Produced water quantity flowing in at padstorage at completion pad cp for each quality component qc and discretized quality q [volume/time]",
        )

        model.DiscreteMaxFlowInPadStorage = Constraint(
            model.s_CP,
            model.s_T,
            model.s_QC,
            model.s_Q,
            rule=lambda model, p, t, qc, q: model.v_F_DiscreteFlowInPadStorage[
                p, t, qc, q
            ]
            <= (model.p_sigma_PadStorage[p])
            * model.v_DQ[p + intermediate_label, t, qc, q],
            doc="Only one inflow for padstorage at completion pad cp can be non-zero for quality component qc and all discretized quality q",
        )

        model.SumDiscreteFlowInPadStorageIsFlowInPadStorage = Constraint(
            model.s_CP,
            model.s_T,
            model.s_QC,
            rule=lambda model, p, t, qc: sum(
                model.v_F_DiscreteFlowInPadStorage[p, t, qc, q] for q in model.s_Q
            )
            == model.v_F_PadStorageIn[p, t],
            doc="The sum of discretized inflows at padstorage at completion pad cp equals the total inflows for padstorage at completion pad cp",
        )

    def DiscretizeCompletionsDestinationQuality(model):
        model.v_F_DiscreteCPDestination = Var(
            model.s_CP,
            model.s_T,
            model.s_QC,
            model.s_Q,
            within=NonNegativeReals,
            units=model.model_units["volume_time"],
            doc="Produced water quantity flowing in from intermediate at completion pad cp for each quality component qc and discretized quality q [volume/time]",
        )

        model.DiscreteMaxCompletionsDestination = Constraint(
            model.s_CP,
            model.s_T,
            model.s_QC,
            model.s_Q,
            rule=lambda model, p, t, qc, q: model.v_F_DiscreteCPDestination[p, t, qc, q]
            <= (model.p_gamma_Completions[p, t])
            * model.v_DQ[p + intermediate_label, t, qc, q],
            doc="Only one quantity for flowing in from intermediate at completion pad cp can be non-zero for quality component qc and all discretized quality q",
        )

        model.SumDiscreteCompletionsDestinationIsCompletionsDestination = Constraint(
            model.s_CP,
            model.s_T,
            model.s_QC,
            rule=lambda model, p, t, qc: sum(
                model.v_F_DiscreteCPDestination[p, t, qc, q] for q in model.s_Q
            )
            == model.v_F_CompletionsDestination[p, t],
            doc="The sum of discretized quantities for flowing in from intermediate at completion pad cp equals the total quantity for flowing in from intermediate at completion pad cp",
        )

    # Create all discretization variables and constraints
    DiscretizePipeFlowQuality(model)
    DiscretizeTruckedFlowQuality(model)
    DiscretizeDisposalDestinationQuality(model)
    DiscretizeOutStorageQuality(model)
    DiscretizeStorageQuality(model)
    DiscretizeTreatmentQuality(model)
    DiscretizeFlowOutNodeQuality(model)
    DiscretizeBeneficialReuseQuality(model)

    DiscretizeCompletionsPadIntermediateQuality(model)
    DiscretizeCompletionsPadStorageQuality(model)
    DiscretizePadStorageQuality(model)
    DiscretizeFlowOutPadStorageQuality(model)
    DiscretizeFlowInPadStorageQuality(model)
    DiscretizeCompletionsDestinationQuality(model)

    # endregion
    # region Disposal
    # Material Balance
    def DisposalWaterQualityRule(b, k, qc, t):
        return sum(
            sum(
                model.v_F_DiscretePiped[n, k, t, qc, q]
                * model.p_discrete_quality[qc, q]
                for q in model.s_Q
            )
            for n in model.s_N
            if model.p_NKA[n, k]
        ) + sum(
            model.v_F_Piped[s, k, t] * model.p_xi[s, qc]
            for s in model.s_S
            if model.p_SKA[s, k]
        ) + sum(
            model.v_F_Trucked[s, k, t] * model.p_xi[s, qc]
            for s in model.s_S
            if model.p_SKT[s, k]
        ) + sum(
            model.v_F_Trucked[p, k, t] * b.p_nu_pad[p, qc]
            for p in model.s_PP
            if model.p_PKT[p, k]
        ) + sum(
            model.v_F_Trucked[p, k, t] * b.p_nu_pad[p, qc]
            for p in model.s_CP
            if model.p_CKT[p, k]
        ) + sum(
            sum(
                model.v_F_DiscreteTrucked[r, k, t, qc, q]
                * model.p_discrete_quality[qc, q]
                for q in model.s_Q
            )
            for r in model.s_R
            if model.p_RKT[r, k]
        ) <= sum(
            model.v_F_DiscreteDisposalDestination[k, t, qc, q]
            * model.p_discrete_quality[qc, q]
            for q in model.s_Q
        )

    model.DisposalWaterQuality = Constraint(
        model.s_K,
        model.s_QC,
        model.s_T,
        rule=DisposalWaterQualityRule,
        doc="Disposal water quality rule",
    )
    # endregion

    # region Storage
    def StorageSiteWaterQualityRule(b, s, qc, t):
        if t == model.s_T.first():
            return model.p_lambda_Storage[s] * b.p_xi_StorageSite[s, qc] + sum(
                sum(
                    model.v_F_DiscretePiped[n, s, t, qc, q]
                    * model.p_discrete_quality[qc, q]
                    for q in model.s_Q
                )
                for n in model.s_N
                if model.p_NSA[n, s]
            ) + sum(
                sum(
                    model.v_F_DiscretePiped[r, s, t, qc, q]
                    * model.p_discrete_quality[qc, q]
                    for q in model.s_Q
                )
                for r in model.s_R
                if model.p_RSA[r, s]
            ) + sum(
                model.v_F_Trucked[p, s, t] * b.p_nu_pad[p, qc]
                for p in model.s_PP
                if model.p_PST[p, s]
            ) + sum(
                model.v_F_Trucked[p, s, t] * b.p_nu_pad[p, qc]
                for p in model.s_CP
                if model.p_CST[p, s]
            ) <= sum(
                model.v_F_DiscreteFlowOutStorage[s, t, qc, q]
                * model.p_discrete_quality[qc, q]
                for q in model.s_Q
            )
        else:
            return sum(
                model.v_L_DiscreteStorage[s, model.s_T.prev(t), qc, q]
                * model.p_discrete_quality[qc, q]
                for q in model.s_Q
            ) + sum(
                sum(
                    model.v_F_DiscretePiped[n, s, t, qc, q]
                    * model.p_discrete_quality[qc, q]
                    for q in model.s_Q
                )
                for n in model.s_N
                if model.p_NSA[n, s]
            ) + sum(
                sum(
                    model.v_F_DiscretePiped[r, s, t, qc, q]
                    * model.p_discrete_quality[qc, q]
                    for q in model.s_Q
                )
                for r in model.s_R
                if model.p_RSA[r, s]
            ) + sum(
                model.v_F_Trucked[p, s, t] * b.p_nu_pad[p, qc]
                for p in model.s_PP
                if model.p_PST[p, s]
            ) + sum(
                model.v_F_Trucked[p, s, t] * b.p_nu_pad[p, qc]
                for p in model.s_CP
                if model.p_CST[p, s]
            ) <= sum(
                model.v_F_DiscreteFlowOutStorage[s, t, qc, q]
                * model.p_discrete_quality[qc, q]
                for q in model.s_Q
            )

    model.StorageSiteWaterQuality = Constraint(
        model.s_S,
        model.s_QC,
        model.s_T,
        rule=StorageSiteWaterQualityRule,
        doc="Storage site water quality rule",
    )
    # endregion

    # region Treatment
    def TreatmentWaterQualityRule(b, r, qc, t):
        return (
            sum(
                sum(
                    model.v_F_DiscretePiped[n, r, t, qc, q]
                    * model.p_discrete_quality[qc, q]
                    for q in model.s_Q
                )
                for n in model.s_N
                if model.p_NRA[n, r]
            )
            + sum(
                sum(
                    model.v_F_DiscretePiped[s, r, t, qc, q]
                    * model.p_discrete_quality[qc, q]
                    for q in model.s_Q
                )
                for s in model.s_S
                if model.p_SRA[s, r]
            )
            + sum(
                model.v_F_Trucked[p, r, t] * b.p_nu_pad[p, qc]
                for p in model.s_PP
                if model.p_PRT[p, r]
            )
            + sum(
                model.v_F_Trucked[p, r, t] * b.p_nu_pad[p, qc]
                for p in model.s_CP
                if model.p_CRT[p, r]
            )
        ) <= sum(
            model.v_F_DiscreteFlowTreatment[r, t, qc, q]
            * model.p_discrete_quality[qc, q]
            for q in model.s_Q
        )

    model.TreatmentWaterQuality = Constraint(
        model.s_R,
        model.s_QC,
        model.s_T,
        rule=TreatmentWaterQualityRule,
        doc="Treatment water quality",
    )
    # endregion

    # region Network """
    def NetworkNodeWaterQualityRule(b, n, qc, t):
        return sum(
            model.v_F_Piped[p, n, t] * b.p_nu_pad[p, qc]
            for p in model.s_PP
            if model.p_PNA[p, n]
        ) + sum(
            model.v_F_Piped[p, n, t] * b.p_nu_pad[p, qc]
            for p in model.s_CP
            if model.p_CNA[p, n]
        ) + sum(
            sum(
                model.v_F_DiscretePiped[s, n, t, qc, q]
                * model.p_discrete_quality[qc, q]
                for q in model.s_Q
            )
            for s in model.s_S
            if model.p_SNA[s, n]
        ) + sum(
            sum(
                model.v_F_DiscretePiped[n_tilde, n, t, qc, q]
                * model.p_discrete_quality[qc, q]
                for q in model.s_Q
            )
            for n_tilde in model.s_N
            if model.p_NNA[n_tilde, n]
        ) <= sum(
            model.v_F_DiscreteFlowOutNode[n, t, qc, q] * model.p_discrete_quality[qc, q]
            for q in model.s_Q
        )

    model.NetworkWaterQuality = Constraint(
        model.s_N,
        model.s_QC,
        model.s_T,
        rule=NetworkNodeWaterQualityRule,
        doc="Network water quality",
    )
    # endregion

    # region Beneficial Reuse
    def BeneficialReuseWaterQuality(b, o, qc, t):
        return sum(
            sum(
                model.v_F_DiscretePiped[n, o, t, qc, q]
                * model.p_discrete_quality[qc, q]
                for q in model.s_Q
            )
            for n in model.s_N
            if model.p_NOA[n, o]
        ) + sum(
            sum(
                model.v_F_DiscretePiped[s, o, t, qc, q]
                * model.p_discrete_quality[qc, q]
                for q in model.s_Q
            )
            for s in model.s_S
            if model.p_SOA[s, o]
        ) + sum(
            model.v_F_Trucked[p, o, t] * b.p_nu_pad[p, qc]
            for p in model.s_PP
            if model.p_POT[p, o]
        ) <= sum(
            model.v_F_DiscreteBRDestination[o, t, qc, q]
            * model.p_discrete_quality[qc, q]
            for q in model.s_Q
        )

    model.BeneficialReuseWaterQuality = Constraint(
        model.s_O,
        model.s_QC,
        model.s_T,
        rule=BeneficialReuseWaterQuality,
        doc="Beneficial reuse water quality",
    )
    # endregion

    # region Completions Pad

    # Water that is Piped and Trucked to a completions pad is mixed and split into two output streams.
    # Stream (1) goes to the completions pad and stream (2) is input to the completions storage.
    # This is the intermediate step.
    # Finally, water that meets completions demand comes from two inputs.
    # The first input is output stream (1) from the intermediate step.
    # The second is outgoing flow from the storage tank.

    def CompletionsPadIntermediateWaterQuality(b, p, qc, t):
        return sum(
            sum(
                model.v_F_DiscretePiped[n, p, t, qc, q]
                * model.p_discrete_quality[qc, q]
                for q in model.s_Q
            )
            for n in model.s_N
            if model.p_NCA[n, p]
        ) + sum(
            model.v_F_Piped[p_tilde, p, t] * b.p_nu_pad[p, qc]
            for p_tilde in model.s_PP
            if model.p_PCA[p_tilde, p]
        ) + sum(
            sum(
                model.v_F_DiscretePiped[s, p, t, qc, q]
                * model.p_discrete_quality[qc, q]
                for q in model.s_Q
            )
            for s in model.s_S
            if model.p_SCA[s, p]
        ) + sum(
            model.v_F_Piped[p_tilde, p, t] * b.p_nu_pad[p, qc]
            for p_tilde in model.s_CP
            if model.p_CCA[p_tilde, p]
        ) + sum(
            sum(
                model.v_F_DiscretePiped[r, p, t, qc, q]
                * model.p_discrete_quality[qc, q]
                for q in model.s_Q
            )
            for r in model.s_R
            if model.p_RCA[r, p]
        ) + sum(
            model.v_F_Sourced[f, p, t] * b.p_nu_externalwater[f, qc]
            for f in model.s_F
            if model.p_FCA[f, p]
        ) + sum(
            model.v_F_Trucked[p_tilde, p, t] * b.p_nu_pad[p, qc]
            for p_tilde in model.s_PP
            if model.p_PCT[p_tilde, p]
        ) + sum(
            model.v_F_Trucked[p_tilde, p, t] * b.p_nu_pad[p, qc]
            for p_tilde in model.s_CP
            if model.p_CCT[p_tilde, p]
        ) + sum(
            sum(
                model.v_F_DiscreteTrucked[s, p, t, qc, q]
                * model.p_discrete_quality[qc, q]
                for q in model.s_Q
            )
            for s in model.s_S
            if model.p_SCT[s, p]
        ) + sum(
            model.v_F_Trucked[f, p, t] * b.p_nu_externalwater[f, qc]
            for f in model.s_F
            if model.p_FCT[f, p]
        ) <= sum(
            model.v_F_DiscreteFlowCPIntermediate[p, t, qc, q]
            * model.p_discrete_quality[qc, q]
            for q in model.s_Q
        )

    model.CompletionsPadIntermediateWaterQuality = Constraint(
        model.s_CP,
        model.s_QC,
        model.s_T,
        rule=CompletionsPadIntermediateWaterQuality,
        doc="Completions pad water quality",
    )

    # The flow to the completion pad is given, so the quality can be continuous.
    model.v_Q_CompletionPad = Var(
        model.s_CP,
        model.s_QC,
        model.s_T,
        within=NonNegativeReals,
        initialize=0,
        units=model.model_units["concentration"],
        doc="Water quality at completion pad [concentration]",
    )

    def CompletionsPadWaterQuality(b, p, qc, t):
        return (
            sum(
                model.v_F_DiscreteFlowOutPadStorage[p, t, qc, q]
                * model.p_discrete_quality[qc, q]
                for q in model.s_Q
            )
            + sum(
                model.v_F_DiscreteCPDestination[p, t, qc, q]
                * model.p_discrete_quality[qc, q]
                for q in model.s_Q
            )
            == model.v_Q_CompletionPad[p, qc, t] * model.p_gamma_Completions[p, t]
        )

    model.CompletionsPadWaterQuality = Constraint(
        model.s_CP,
        model.s_QC,
        model.s_T,
        rule=CompletionsPadWaterQuality,
        doc="Completions pad water quality",
    )
    # endregion

    # region Completion Pad Storage
    def CompletionsPadStorageWaterQuality(b, p, qc, t):
        if t == model.s_T.first():
            return b.p_xi_PadStorage[p, qc] * model.p_lambda_PadStorage[p] + sum(
                model.v_F_DiscreteFlowInPadStorage[p, t, qc, q]
                * model.p_discrete_quality[qc, q]
                for q in model.s_Q
            ) <= sum(
                model.v_F_DiscreteFlowCPStorage[p, t, qc, q]
                * model.p_discrete_quality[qc, q]
                for q in model.s_Q
            )
        else:
            return sum(
                model.v_L_DiscretePadStorage[p, model.s_T.prev(t), qc, q]
                * model.p_discrete_quality[qc, q]
                for q in model.s_Q
            ) + sum(
                model.v_F_DiscreteFlowInPadStorage[p, t, qc, q]
                * model.p_discrete_quality[qc, q]
                for q in model.s_Q
            ) <= sum(
                model.v_F_DiscreteFlowCPStorage[p, t, qc, q]
                * model.p_discrete_quality[qc, q]
                for q in model.s_Q
            )

    model.CompletionsPadStorageWaterQuality = Constraint(
        model.s_CP,
        model.s_QC,
        model.s_T,
        rule=CompletionsPadStorageWaterQuality,
        doc="Completions pad storage water quality",
    )
    # endregion

    model.v_ObjectiveWithQuality = Var(
        within=Reals,
        doc="Obj value including minimizing quality at completion pads",
    )

    def ObjectiveFunctionQualityRule(model):
        if model.config.objective == Objectives.cost:
            obj_var = model.v_Z
        elif model.config.objective == Objectives.reuse:
            obj_var = model.v_Z_Reuse
        elif model.config.objective == Objectives.cost_surrogate:
            obj_var = model.v_Z_Surrogate
        elif model.config.objective == Objectives.subsurface_risk:
            obj_var = model.v_Z_SubsurfaceRisk
        elif model.config.objective == Objectives.environmental:
            obj_var = model.e_TotalEmissions
        else:
            raise Exception("Objective not supported")

        return (
            model.v_ObjectiveWithQuality
            == obj_var
            + sum(
                sum(
                    sum(model.v_Q_CompletionPad[p, qc, t] for p in model.s_CP)
                    for t in model.s_T
                )
                for qc in model.s_QC
            )
            / 1000
        )

    model.ObjectiveFunctionQuality = Constraint(
        rule=ObjectiveFunctionQualityRule, doc="Objective function water quality"
    )

    if model.config.objective == Objectives.cost:
        model.objective_Cost.set_value(expr=model.v_ObjectiveWithQuality)
    elif model.config.objective == Objectives.reuse:
        model.objective_Reuse.set_value(expr=model.v_ObjectiveWithQuality)
    elif model.config.objective == Objectives.cost_surrogate:
        model.objective_CostSurrogate.set_value(expr=model.v_ObjectiveWithQuality)
    elif model.config.objective == Objectives.subsurface_risk:
        model.objective_SubsurfaceRisk.set_value(expr=model.v_ObjectiveWithQuality)
    else:
        raise Exception("Objective not supported")

    return model


def postprocess_water_quality_calculation(model, opt):
    # Add water quality formulation to input solved model
    water_quality_model = water_quality(model)

    # Calculate water quality. The following conditional is used to avoid errors when
    # using Gurobi solver
    if opt.options["solver"] == "CPLEX":
        opt.solve(
            water_quality_model.quality,
            tee=True,
            add_options=["gams_model.optfile=1;"],
        )
    elif opt.type == "gurobi_direct":
        opt.solve(water_quality_model.quality, tee=True, save_results=False)
    else:
        opt.solve(water_quality_model.quality, tee=True)

    return water_quality_model


def scale_model(model, scaling_factor=1000000):
    model.scaling_factor = Suffix(direction=Suffix.EXPORT)

    # Scaling variables
    model.scaling_factor[model.v_Z] = 1 / scaling_factor
    model.scaling_factor[model.v_Z_Reuse] = 1 / scaling_factor
    if hasattr(model, "v_Z_Surrogate"):
        model.scaling_factor[model.v_Z_Surrogate] = 1 / scaling_factor
    if model.do_subsurface_risk_calcs:
        model.scaling_factor[model.v_Z_SubsurfaceRisk] = 1 / scaling_factor
    model.scaling_factor[model.v_C_Disposal] = 1 / scaling_factor
    model.scaling_factor[model.v_C_DisposalCapEx] = 1 / scaling_factor
    model.scaling_factor[model.v_C_Piped] = 1 / scaling_factor
    model.scaling_factor[model.v_C_PipelineCapEx] = 1 / scaling_factor
    model.scaling_factor[model.v_C_Reuse] = 1 / scaling_factor
    model.scaling_factor[model.v_C_Slack] = 1 / (scaling_factor * 100)
    model.scaling_factor[model.v_C_Sourced] = 1 / scaling_factor
    model.scaling_factor[model.v_C_Storage] = 1 / scaling_factor
    model.scaling_factor[model.v_C_StorageCapEx] = 1 / scaling_factor
    model.scaling_factor[model.v_C_TotalDisposal] = 1 / scaling_factor
    model.scaling_factor[model.v_C_TotalPiping] = 1 / scaling_factor
    model.scaling_factor[model.v_C_TotalStorage] = 1 / scaling_factor
    model.scaling_factor[model.v_C_TotalReuse] = 1 / scaling_factor
    model.scaling_factor[model.v_C_TotalSourced] = 1 / scaling_factor
    model.scaling_factor[model.v_C_TotalTreatment] = 1 / scaling_factor
    model.scaling_factor[model.v_C_TotalTrucking] = 1 / scaling_factor
    model.scaling_factor[model.v_C_Treatment] = 1 / scaling_factor
    model.scaling_factor[model.v_C_TreatmentCapEx] = 1 / scaling_factor
    model.scaling_factor[model.v_C_Trucked] = 1 / scaling_factor
    model.scaling_factor[model.v_D_Capacity] = 1 / scaling_factor
    model.scaling_factor[model.v_F_Capacity] = 1 / scaling_factor
    model.scaling_factor[model.v_F_DisposalDestination] = 1 / scaling_factor
    model.scaling_factor[model.v_F_PadStorageIn] = 1 / scaling_factor
    model.scaling_factor[model.v_F_PadStorageOut] = 1 / scaling_factor
    model.scaling_factor[model.v_F_Piped] = 1 / scaling_factor
    model.scaling_factor[model.v_F_ReuseDestination] = 1 / scaling_factor
    model.scaling_factor[model.v_F_StorageEvaporationStream] = 1 / scaling_factor
    model.scaling_factor[model.v_F_TreatmentFeed] = 1 / scaling_factor
    model.scaling_factor[model.v_F_TreatmentFeedTech] = 1 / scaling_factor
    model.scaling_factor[model.v_F_ResidualWater] = 1 / scaling_factor
    model.scaling_factor[model.v_F_TreatedWater] = 1 / scaling_factor
    model.scaling_factor[model.v_F_BeneficialReuseDestination] = 1 / scaling_factor
    model.scaling_factor[model.v_F_CompletionsDestination] = 1 / scaling_factor
    model.scaling_factor[model.v_F_Sourced] = 1 / scaling_factor
    model.scaling_factor[model.v_F_TotalDisposed] = 1 / scaling_factor
    model.scaling_factor[model.v_F_TotalReused] = 1 / scaling_factor
    model.scaling_factor[model.v_F_TotalBeneficialReuse] = 1 / scaling_factor
    model.scaling_factor[model.v_F_TotalSourced] = 1 / scaling_factor
    model.scaling_factor[model.v_F_TotalTrucked] = 1 / scaling_factor
    model.scaling_factor[model.v_F_Trucked] = 1 / scaling_factor
    model.scaling_factor[model.v_L_PadStorage] = 1 / scaling_factor
    model.scaling_factor[model.v_L_Storage] = 1 / scaling_factor
    model.scaling_factor[model.v_R_Storage] = 1 / scaling_factor
    model.scaling_factor[model.v_C_BeneficialReuse] = 1 / scaling_factor
    model.scaling_factor[model.v_R_BeneficialReuse] = 1 / scaling_factor
    model.scaling_factor[model.v_R_TotalStorage] = 1 / scaling_factor
    model.scaling_factor[model.v_C_TotalBeneficialReuse] = 1 / scaling_factor
    model.scaling_factor[model.v_R_TotalBeneficialReuse] = 1 / scaling_factor
    model.scaling_factor[model.v_S_DisposalCapacity] = 1000 / scaling_factor
    model.scaling_factor[model.v_S_Flowback] = 1000 / scaling_factor
    model.scaling_factor[model.v_S_FracDemand] = 1000 / scaling_factor
    model.scaling_factor[model.v_S_PipelineCapacity] = 1000 / scaling_factor
    model.scaling_factor[model.v_S_Production] = 1000 / scaling_factor
    model.scaling_factor[model.v_S_BeneficialReuseCapacity] = 1000 / scaling_factor
    model.scaling_factor[model.v_S_TreatmentCapacity] = 1000 / scaling_factor
    model.scaling_factor[model.v_S_StorageCapacity] = 1000 / scaling_factor
    model.scaling_factor[model.v_T_Capacity] = 1 / scaling_factor
    model.scaling_factor[model.v_X_Capacity] = 1 / scaling_factor

    if model.config.water_quality is WaterQuality.discrete:
        model.scaling_factor[model.v_F_DiscretePiped] = 1 / (scaling_factor)
        model.scaling_factor[model.v_F_DiscreteTrucked] = 1 / (scaling_factor)
        model.scaling_factor[model.v_F_DiscreteDisposalDestination] = 1 / (
            scaling_factor
        )
        model.scaling_factor[model.v_F_DiscreteFlowOutStorage] = 1 / (scaling_factor)
        model.scaling_factor[model.v_L_DiscreteStorage] = 1 / (scaling_factor)
        model.scaling_factor[model.v_F_DiscreteFlowTreatment] = 1 / (scaling_factor)
        model.scaling_factor[model.v_F_DiscreteFlowOutNode] = 1 / (scaling_factor)
        model.scaling_factor[model.v_F_DiscreteBRDestination] = 1 / (scaling_factor)

        model.scaling_factor[model.v_F_DiscreteFlowCPIntermediate] = 1 / (
            scaling_factor
        )
        model.scaling_factor[model.v_F_DiscreteFlowCPStorage] = 1 / (scaling_factor)
        model.scaling_factor[model.v_L_DiscretePadStorage] = 1 / (scaling_factor)
        model.scaling_factor[model.v_F_DiscreteFlowOutPadStorage] = 1 / (scaling_factor)
        model.scaling_factor[model.v_F_DiscreteFlowInPadStorage] = 1 / (scaling_factor)
        model.scaling_factor[model.v_F_DiscreteCPDestination] = 1 / (scaling_factor)
        model.scaling_factor[model.v_Q_CompletionPad] = 1 / (scaling_factor)
        model.scaling_factor[model.v_ObjectiveWithQuality] = 1 / (scaling_factor)
        model.scaling_factor[model.ObjectiveFunctionQuality] = 1 / scaling_factor

    # Scaling constraints
    model.scaling_factor[model.ObjectiveFunctionCost] = 1 / scaling_factor
    model.scaling_factor[model.ObjectiveFunctionReuse] = 1 / scaling_factor
    if model.do_subsurface_risk_calcs:
        model.scaling_factor[model.ObjectiveFunctionSubsurfaceRisk] = 1 / scaling_factor
    if hasattr(model, "ObjectiveFunctionCostSurrogate"):
        model.scaling_factor[model.ObjectiveFunctionCostSurrogate] = 1 / scaling_factor
    model.scaling_factor[model.BeneficialReuseMinimum] = 1 / scaling_factor
    model.scaling_factor[model.BeneficialReuseCapacity] = 1 / scaling_factor
    model.scaling_factor[model.TotalBeneficialReuse] = 1 / scaling_factor
    # This constraints contains only binary variables
    model.scaling_factor[model.BidirectionalFlow1] = 1
    model.scaling_factor[model.BidirectionalFlow2] = 1 / scaling_factor
    model.scaling_factor[model.CompletionsPadDemandBalance] = 1 / scaling_factor
    model.scaling_factor[model.CompletionsPadStorageBalance] = 1 / scaling_factor
    model.scaling_factor[model.CompletionsPadStorageCapacity] = 1 / scaling_factor
    model.scaling_factor[model.CompletionsPadSupplyBalance] = 1 / scaling_factor
    model.scaling_factor[model.CompletionsPadTruckOffloadingCapacity] = (
        1 / scaling_factor
    )
    model.scaling_factor[model.CompletionsReuseCost] = 1 / scaling_factor
    model.scaling_factor[model.DisposalCapacity] = 1 / scaling_factor
    model.scaling_factor[model.DisposalCapacityExpansion] = 1 / scaling_factor
    model.scaling_factor[model.DisposalCost] = 1 / scaling_factor
    model.scaling_factor[model.DisposalDestinationDeliveries] = 1 / scaling_factor
    model.scaling_factor[model.DisposalExpansionCapEx] = 1 / scaling_factor
    model.scaling_factor[model.ExternalWaterSourcingCapacity] = 1 / scaling_factor
    model.scaling_factor[model.ExternalSourcingCost] = 1 / scaling_factor
    # This constraint contains only binary variables
    model.scaling_factor[model.LogicConstraintDisposal] = 1
    # This constraint contains only binary variables
    model.scaling_factor[model.LogicConstraintPipeline] = 1
    # This constraint contains only binary variables
    model.scaling_factor[model.LogicConstraintStorage] = 1
    # This constraint contains only binary variables
    model.scaling_factor[model.LogicConstraintTreatmentAssignment] = 1
    # This constraint contains only binary variables
    model.scaling_factor[model.LogicConstraintDesalinationAssignment] = 1
    # This constraint contains only binary variables
    model.scaling_factor[model.LogicConstraintNoDesalinationAssignment] = 1
    model.scaling_factor[model.NetworkBalance] = 1 / scaling_factor
    model.scaling_factor[model.PipelineCapacity] = 1 / scaling_factor
    model.scaling_factor[model.PipelineCapacityExpansion] = 1 / scaling_factor
    model.scaling_factor[model.PipelineExpansionCapEx] = 1 / scaling_factor
    model.scaling_factor[model.PipingCost] = 1 / scaling_factor
    model.scaling_factor[model.ProductionPadSupplyBalance] = 1 / scaling_factor
    model.scaling_factor[model.ReuseDestinationDeliveries] = 1 / scaling_factor
    model.scaling_factor[model.SlackCosts] = 1 / (scaling_factor**2)
    model.scaling_factor[model.BeneficialReuseDeliveries] = 1 / scaling_factor
    model.scaling_factor[model.CompletionsWaterDeliveries] = 1 / scaling_factor
    model.scaling_factor[model.StorageCapacity] = 1 / scaling_factor
    model.scaling_factor[model.StorageCapacityExpansion] = 1 / scaling_factor
    model.scaling_factor[model.StorageDepositCost] = 1 / scaling_factor
    model.scaling_factor[model.StorageExpansionCapEx] = 1 / scaling_factor
    model.scaling_factor[model.StorageSiteBalance] = 1 / scaling_factor
    model.scaling_factor[model.StorageSiteProcessingCapacity] = 1 / scaling_factor
    model.scaling_factor[model.StorageSiteTruckOffloadingCapacity] = 1 / scaling_factor
    model.scaling_factor[model.StorageWithdrawalCredit] = 1 / scaling_factor
    model.scaling_factor[model.BeneficialReuseCost] = 1 / scaling_factor
    model.scaling_factor[model.BeneficialReuseCredit] = 1 / scaling_factor
    model.scaling_factor[model.TerminalCompletionsPadStorageLevel] = 1 / scaling_factor
    model.scaling_factor[model.TerminalStorageLevel] = 1 / scaling_factor
    model.scaling_factor[model.TotalCompletionsReuseCost] = 1 / scaling_factor
    model.scaling_factor[model.TotalDisposalCost] = 1 / scaling_factor
    model.scaling_factor[model.TotalDisposalVolume] = 1 / scaling_factor
    model.scaling_factor[model.TotalExternalSourcingCost] = 1 / scaling_factor
    model.scaling_factor[model.TotalExternalSourcingVolume] = 1 / scaling_factor
    model.scaling_factor[model.TotalPipingCost] = 1 / scaling_factor
    model.scaling_factor[model.TotalReuseVolume] = 1 / scaling_factor
    model.scaling_factor[model.TotalStorageCost] = 1 / scaling_factor
    model.scaling_factor[model.TotalStorageWithdrawalCredit] = 1 / scaling_factor
    model.scaling_factor[model.TotalBeneficialReuseCost] = 1 / scaling_factor
    model.scaling_factor[model.TotalBeneficialReuseCredit] = 1 / scaling_factor
    model.scaling_factor[model.TotalTreatmentCost] = 1 / scaling_factor
    model.scaling_factor[model.TotalTruckingCost] = 1 / scaling_factor
    model.scaling_factor[model.TotalTruckingVolume] = 1 / scaling_factor
    model.scaling_factor[model.TreatmentFeedBalance] = 1 / scaling_factor
    model.scaling_factor[model.TreatmentFeedTechLHS] = 1 / scaling_factor
    model.scaling_factor[model.TreatmentFeedTechRHS] = 1 / scaling_factor
    model.scaling_factor[model.TreatmentBalance] = 1 / scaling_factor
    model.scaling_factor[model.TreatedWaterBalance] = 1 / scaling_factor
    model.scaling_factor[model.ResidualWaterBalance] = 1 / scaling_factor
    model.scaling_factor[model.TreatmentCapacity] = 1 / scaling_factor
    model.scaling_factor[model.TreatmentCapacityExpansion] = 1 / scaling_factor
    model.scaling_factor[model.TreatmentCostLHS] = 1 / scaling_factor
    model.scaling_factor[model.TreatmentCostRHS] = 1 / scaling_factor
    model.scaling_factor[model.ResidualWaterLHS] = 1 / scaling_factor
    model.scaling_factor[model.ResidualWaterRHS] = 1 / scaling_factor
    model.scaling_factor[model.TruckingCost] = 1 / (scaling_factor * 100)
    model.scaling_factor[model.TreatmentExpansionCapEx] = 1 / scaling_factor
    model.scaling_factor[model.LogicConstraintEvaporationFlow] = 1 / scaling_factor
    model.scaling_factor[model.SeismicResponseArea] = 1 / scaling_factor
    if (
        model.config.subsurface_risk
        == SubsurfaceRisk.exclude_over_and_under_pressured_wells
    ):
        model.scaling_factor[model.ExcludeUnderAndOverPressuredDisposalWells] = (
            1 / scaling_factor
        )

    if model.do_subsurface_risk_calcs:
        model.scaling_factor[model.subsurface.site_constraint] = 1

    if model.config.node_capacity == True:
        model.scaling_factor[model.NetworkCapacity] = 1 / scaling_factor

    if model.config.water_quality is WaterQuality.discrete:
        model.scaling_factor[model.OnlyOneDiscreteQualityPerLocation] = 1

        model.scaling_factor[model.DiscreteMaxPipeFlow] = 1 / scaling_factor
        model.scaling_factor[model.SumDiscreteFlowsIsFlowPiped] = 1 / scaling_factor

        model.scaling_factor[model.DiscreteMaxTruckedFlow] = 1 / scaling_factor
        model.scaling_factor[model.SumDiscreteFlowsIsFlowTrucked] = 1 / scaling_factor

        model.scaling_factor[model.DiscreteMaxDisposalDestination] = 1 / scaling_factor
        model.scaling_factor[
            model.SumDiscreteDisposalDestinationIsDisposalDestination
        ] = (1 / scaling_factor)

        model.scaling_factor[model.DiscreteMaxOutStorageFlow] = 1 / scaling_factor
        model.scaling_factor[model.SumDiscreteFlowsIsFlowOutStorage] = (
            1 / scaling_factor
        )

        model.scaling_factor[model.DiscreteMaxStorage] = 1 / scaling_factor
        model.scaling_factor[model.SumDiscreteStorageIsStorage] = 1 / scaling_factor

        model.scaling_factor[model.DiscreteMaxTreatmentFlow] = 1 / scaling_factor
        model.scaling_factor[model.SumDiscreteFlowsIsFlowTreatment] = 1 / scaling_factor

        model.scaling_factor[model.DiscreteMaxOutNodeFlow] = 1 / scaling_factor
        model.scaling_factor[model.SumDiscreteFlowsIsFlowOutNode] = 1 / scaling_factor

        model.scaling_factor[model.DiscreteMaxBeneficialReuseFlow] = 1 / scaling_factor
        model.scaling_factor[model.SumDiscreteFlowsIsFlowBeneficialReuse] = (
            1 / scaling_factor
        )

        model.scaling_factor[model.DiscreteMaxCompletionsPadIntermediateFlow] = (
            1 / scaling_factor
        )
        model.scaling_factor[model.SumDiscreteFlowsIsFlowCompletionsPadIntermediate] = (
            1 / scaling_factor
        )

        model.scaling_factor[model.DiscreteMaxCompletionsPadStorageFlow] = (
            1 / scaling_factor
        )
        model.scaling_factor[model.SumDiscreteFlowsIsFlowCompletionsPadStorage] = (
            1 / scaling_factor
        )

        model.scaling_factor[model.DiscreteMaxPadStorage] = 1 / scaling_factor
        model.scaling_factor[model.SumDiscretePadStorageIsPadStorage] = (
            1 / scaling_factor
        )

        model.scaling_factor[model.DiscreteMaxFlowOutPadStorage] = 1 / scaling_factor
        model.scaling_factor[model.SumDiscreteFlowOutPadStorageIsFlowOutPadStorage] = (
            1 / scaling_factor
        )

        model.scaling_factor[model.DiscreteMaxFlowInPadStorage] = 1 / scaling_factor
        model.scaling_factor[model.SumDiscreteFlowInPadStorageIsFlowInPadStorage] = (
            1 / scaling_factor
        )

        model.scaling_factor[model.DiscreteMaxCompletionsDestination] = (
            1 / scaling_factor
        )
        model.scaling_factor[
            model.SumDiscreteCompletionsDestinationIsCompletionsDestination
        ] = (1 / scaling_factor)

        model.scaling_factor[model.DisposalWaterQuality] = 1 / (scaling_factor * 100)
        model.scaling_factor[model.StorageSiteWaterQuality] = 1 / (scaling_factor * 100)
        model.scaling_factor[model.TreatmentWaterQuality] = 1 / (scaling_factor * 100)
        model.scaling_factor[model.NetworkWaterQuality] = 1 / (scaling_factor * 100)
        model.scaling_factor[model.BeneficialReuseWaterQuality] = 1 / (
            scaling_factor * 100
        )

        model.scaling_factor[model.CompletionsPadIntermediateWaterQuality] = 1 / (
            scaling_factor * 100
        )
        model.scaling_factor[model.CompletionsPadWaterQuality] = 1 / (
            scaling_factor * 100
        )
        model.scaling_factor[model.CompletionsPadStorageWaterQuality] = 1 / (
            scaling_factor * 100
        )

    scaled_model = TransformationFactory("core.scale_model").create_using(model)

    return scaled_model


def _preprocess_data(model):
    """
    This module pre-processess data to fit the optimization format.
    In this module the following data is preprocessed:
    - Pipeline Diameters [diameter] are converted to flow rate model [volume/time]
    - Pipeline Expension Cost is converted to model [currency/volume]
    parameter_list = [list of tabs that contain parameters]
    """
    if model.config.pipeline_capacity == PipelineCapacity.calculated:
        # Pipeline Capacity
        # Pipeline diameter is converted to pipeline capacity (volume/time) using
        # Hazen-Williams equation.
        # (https://en.wikipedia.org/wiki/Hazen%E2%80%93Williams_equation)
        # Required inputs are:
        # - pipeline diameter [inch]
        # - pipe roughness []
        # - max head loss

        # retrieve roughness and max head loss
        roughness = model.df_parameters["Hydraulics"]["roughness"]
        max_head_loss = model.df_parameters["Hydraulics"]["max_head_loss"]

        model.df_parameters["PipelineCapacityIncrements_Calculated"] = {}
        for key in model.df_parameters["PipelineDiameterValues"]:
            diameter_inches = pyunits.convert_value(
                model.df_parameters["PipelineDiameterValues"][key],
                from_units=model.user_units["diameter"],
                to_units=pyunits.inch,
            )
            flow_rate = (
                (1 / 10.67) ** (1 / 1.852)
                * roughness
                * (max_head_loss**0.54)
                * (diameter_inches * 0.0254) ** 2.63
            )

            # convert to volume/time:
            days_in_period = model.decision_period / pyunits.days
            # Make variable unitless
            days_in_period = pyunits.convert(
                days_in_period, to_units=pyunits.days / pyunits.days
            )
            flow_rate *= 6.28981 * (3600 * 24 * days_in_period)

            # add to parameter df.
            model.df_parameters["PipelineCapacityIncrements_Calculated"][
                key
            ] = flow_rate

    # Annualization rate
    # The annualization rate is used using a discount rate and the lifetime
    # expectancy of assets. It's calculated using the formula as described
    # on the following website:
    # http://www.energycommunity.org/webhelppro/Expressions/AnnualizedCost.htm

    discount_rate = model.df_parameters["Economics"]["discount_rate"]
    life = model.df_parameters["Economics"]["CAPEX_lifetime"]

    if life == 0:
        model.df_parameters["AnnualizationRate"] = 1
    elif discount_rate == 0:
        model.df_parameters["AnnualizationRate"] = 1 / life
    else:
        model.df_parameters["AnnualizationRate"] = discount_rate / (
            1 - (1 + discount_rate) ** -life
        )


def infrastructure_timing(model):
    # Store the start build time to a dictionary
    model.infrastructure_buildStart = {}
    # Store the lead time for built facilities to a dictionary
    model.infrastructure_leadTime = {}
    # Store time period for first use to a dictionary
    model.infrastructure_firstUse = {}
    # Due to tolerances, binaries may not exactly equal 1
    binary_epsilon = 0.1

    # Iterate through our built sites
    # Treatment - "vb_y_Treatment"
    treatment_data = model.vb_y_Treatment._data
    # Treatment Site - iterate through vb_y variables
    for i in treatment_data:
        # Get site name from data
        treatment_site = i[0]
        # add values to output dictionary
        if (
            treatment_data[i].value >= 1 - binary_epsilon
            and treatment_data[i].value <= 1 + binary_epsilon
            and model.p_delta_Treatment[(i[1], i[2])].value
            > 0  # selected capacity is nonzero
        ):
            # determine first time period that site is used
            # first use is time period where there is more volume to treatment than starting capacity
            for t in model.s_T:
                if (
                    sum(
                        model.v_F_Piped[l, treatment_site, t].value
                        for l in model.s_L
                        if (l, treatment_site) in model.s_LLA
                    )
                    + sum(
                        model.v_F_Trucked[l, treatment_site, t].value
                        for l in model.s_L
                        if (l, treatment_site) in model.s_LLT
                    )
                    > model.p_sigma_Treatment[treatment_site, i[1]].value
                ):
                    # Add first use to a dictionary
                    model.infrastructure_firstUse[treatment_site] = t
                    # Get the lead time rounded up to the nearest full time period
                    model.infrastructure_leadTime[treatment_site] = math.ceil(
                        model.p_tau_TreatmentExpansionLeadTime[i].value
                    )
                    break

    # Disposal - "vb_y_Disposal"
    disposal_data = model.vb_y_Disposal._data
    for i in disposal_data:
        # Get site name and selected capacity from data
        disposal_site = i[0]
        disposal_capacity = i[1]
        # add values to output dictionary
        if (
            disposal_data[i].value >= 1 - binary_epsilon
            and disposal_data[i].value <= 1 + binary_epsilon
            and model.p_delta_Disposal[disposal_site, disposal_capacity].value
            > 0  # selected capacity is nonzero
        ):
            # determine first time period that site is used
            # First use is time period where more water is sent to disposal than initial capacity
            for t in model.s_T:
                if (
                    model.v_F_DisposalDestination[disposal_site, t].value
                    > model.p_sigma_Disposal[disposal_site].value
                ):
                    # Add first use to a dictionary
                    model.infrastructure_firstUse[disposal_site] = t
                    # Get the lead time rounded up to the nearest full time period
                    model.infrastructure_leadTime[disposal_site] = math.ceil(
                        model.p_tau_DisposalExpansionLeadTime[i].value
                    )
                    break

    # Storage - "vb_y_Storage"
    storage_data = model.vb_y_Storage._data
    # Storage Site - iterate through vb_y variables
    for i in storage_data:
        # Get site name from data
        storage_site = i[0]
        # add values to output dictionary
        if (
            storage_data[i].value >= 1 - binary_epsilon
            and storage_data[i].value <= 1 + binary_epsilon
            and model.p_delta_Storage[i[1]].value > 0  # selected capacity is nonzero
        ):
            # determine first time period that site is used
            # First use is when the water level exceeds the initial storage capacity
            for t in model.s_T:
                if (
                    model.v_L_Storage[storage_site, t].value
                    > model.p_sigma_Storage[storage_site].value
                ):
                    # Add first use to a dictionary
                    model.infrastructure_firstUse[storage_site] = t
                    # Get the lead time rounded up to the nearest full time period
                    model.infrastructure_leadTime[storage_site] = math.ceil(
                        model.p_tau_StorageExpansionLeadTime[i].value
                    )
                    break

    # Pipeline - "vb_y_Pipeline"
    pipeline_data = model.vb_y_Pipeline._data
    for i in pipeline_data:
        # Get site name from data
        pipeline = (i[0], i[1])
        # add values to output dictionary
        if (
            pipeline_data[i].value >= 1 - binary_epsilon
            and pipeline_data[i].value <= 1 + binary_epsilon
            and model.p_delta_Pipeline[i[2]].value > 0  # selected capacity is nonzero
        ):
            # determine first time period that site is used
            # pipeline is first used when water is sent in either direction of pipeline at a volume above the initial capacity
            for t in model.s_T:
                above_initial_capacity = False
                # if the pipeline is defined as bidirectional then the aggregated initial capacity is available in both directions
                if pipeline[::-1] in model.s_LLA:
                    initial_capacity = (
                        model.p_sigma_Pipeline[pipeline].value
                        + model.p_sigma_Pipeline[pipeline[::-1]].value
                    )
                    if (
                        model.v_F_Piped[pipeline, t].value > initial_capacity
                        or model.v_F_Piped[pipeline[::-1], t].value > initial_capacity
                    ):
                        above_initial_capacity = True
                else:
                    initial_capacity = model.p_sigma_Pipeline[pipeline].value
                    if model.v_F_Piped[pipeline, t].value > initial_capacity:
                        above_initial_capacity = True

                if above_initial_capacity:
                    # Add first use to a dictionary
                    model.infrastructure_firstUse[pipeline] = t
                    # Get the lead time rounded up to the nearest full time period

                    if model.config.pipeline_cost == PipelineCost.distance_based:
                        model.infrastructure_leadTime[pipeline] = math.ceil(
                            model.p_tau_PipelineExpansionLeadTime.value
                            * model.p_lambda_Pipeline[pipeline].value
                        )
                    elif model.config.pipeline_cost == PipelineCost.capacity_based:
                        # Pipelines lead time may only be defined in one direction
                        model.infrastructure_leadTime[pipeline] = math.ceil(
                            max(
                                model.p_tau_PipelineExpansionLeadTime[i].value,
                                model.p_tau_PipelineExpansionLeadTime[
                                    pipeline[::-1], i[2]
                                ].value,
                            )
                        )
                    break

    # Calculate start build for all infrastructure
    # Convert the ordered set to a list for easier use
    s_T_list = list(model.s_T)
    for key, value in model.infrastructure_firstUse.items():
        # Find the index of time period in the list
        finish_index = s_T_list.index(value)
        start_index = finish_index - model.infrastructure_leadTime[key]
        # if start time is within time horizon, report time period
        if start_index >= 0:
            model.infrastructure_buildStart[key] = model.s_T.at(start_index + 1)
        # if start time is prior to time horizon, report # time period prior to start
        else:
            if abs(start_index) > 1:
                plural = "s"
            else:
                plural = ""

            model.infrastructure_buildStart[key] = (
                str(abs(start_index))
                + " "
                + model.decision_period.to_string()
                + plural
                + " prior to "
                + model.s_T.first()
            )


def subsurface_risk(model):
    model.subsurface = Block()
    m = model.subsurface

    maxmin = ["max", "min"]
    prox = ["orphan", "inactive", "EQ", "fault", "HP_LP"]
    prox_params = [
        "SWDProxPAWell",
        "SWDProxInactiveWell",
        "SWDProxEQ",
        "SWDProxFault",
        "SWDProxHpOrLpWell",
    ]
    prox_init = {}
    k = 0
    for i in prox_params:
        for j in model.s_K:
            prox_init[prox[k], j] = model.df_parameters[i][j]
        k += 1

    m.deep = model.df_parameters["SWDDeep"]
    m.pressure = model.df_parameters["SWDAveragePressure"]
    m.prox = Param(prox, model.s_K, initialize=prox_init)

    risk_factors = model.df_parameters["SWDRiskFactors"]
    risk_factor_set = ["distance", "severity"]
    dist_init = {}
    severity_init = {}
    for i in risk_factors.keys():
        match = re.search("distance", i)
        if match:
            for j in prox:
                match = re.search(j, i)
                if match:
                    dist_init[j] = risk_factors[i]
                    break
        match = re.search("severity", i)
        if match:
            for j in prox:
                match = re.search(j, i)
                if match:
                    severity_init[j] = risk_factors[i]
                    break
    pres_init = {
        "max": risk_factors["HP_threshold"],
        "min": risk_factors["LP_threshold"],
    }

    m.distance_risk_factors = Param(prox, initialize=dist_init, mutable=True)
    m.severity_risk_factors = Param(prox, initialize=severity_init, mutable=True)
    m.sum_risk_factor = Param(risk_factor_set, initialize=0, mutable=True)
    m.pressure_thresholds = Param(maxmin, initialize=pres_init)

    m.vb_y_dist = Var(model.s_K, prox, initialize=0, within=Binary)

    for site in model.s_K:
        for factor in prox:
            if factor in ("orphan", "inactive") and m.deep[site]:
                m.vb_y_dist[site, factor].fix(1)

    # Defining expressions
    def sum_risk_dist_rule(m):
        for i in prox:
            m.sum_risk_factor["distance"] += m.distance_risk_factors[i]
        return m.sum_risk_factor["distance"]

    m.e_sum_risk_dist = Expression(
        rule=sum_risk_dist_rule, doc="Sum of distance risk factors [dimensionless]"
    )

    def sum_risk_severity_rule(m):
        for i in prox:
            m.sum_risk_factor["severity"] += m.severity_risk_factors[i]
        return m.sum_risk_factor["severity"]

    m.e_sum_risk_severity = Expression(
        rule=sum_risk_severity_rule, doc="Sum of severity risk factors [dimensionless]"
    )

    def norm_risk_dist_rule(m, prox):
        return m.distance_risk_factors[prox] / m.e_sum_risk_dist

    m.e_norm_risk_dist = Expression(
        prox,
        rule=norm_risk_dist_rule,
        doc="Normalized distance risk factors [dimensionless]",
    )

    def norm_risk_severity_rule(m, prox):
        return m.severity_risk_factors[prox] / m.e_sum_risk_severity

    m.e_norm_risk_severity = Expression(
        prox,
        rule=norm_risk_severity_rule,
        doc="Normalized severity risk factors [dimensionless]",
    )

    def max_risk_fact_min_risk_rule(m):
        return sum(
            m.distance_risk_factors[i]
            * m.e_norm_risk_dist[i]
            * m.e_norm_risk_severity[i]
            for i in prox
        )

    m.e_max_risk_fact_min_risk = Expression(
        rule=max_risk_fact_min_risk_rule,
        doc="Maximum value for lowest risk [dimensionless]",
    )

    def site_rule_constraints(m, site, factor):
        if factor in ("orphan", "inactive") and m.deep[site]:
            return Constraint.Skip
        else:
            return (
                m.distance_risk_factors[factor] * m.vb_y_dist[site, factor]
                <= m.prox[factor, site]
            )

    m.site_constraint = Constraint(model.s_K, prox, rule=site_rule_constraints)

    def risk_metric_rule(m, site):
        return (
            1
            - sum(
                (
                    m.distance_risk_factors[factor] * m.vb_y_dist[site, factor]
                    + m.prox[factor, site] * (1 - m.vb_y_dist[site, factor])
                )
                * m.e_norm_risk_dist[factor]
                * m.e_norm_risk_severity[factor]
                for factor in prox
            )
            / m.e_max_risk_fact_min_risk
        )

    m.e_risk_metrics = Expression(
        model.s_K, rule=risk_metric_rule, doc="Overall SWD risk metric [dimensionless]"
    )

    m.sites_included = Param(
        model.s_K,
        initialize={
            k: m.pressure[k] >= m.pressure_thresholds["min"]
            and m.pressure[k] <= m.pressure_thresholds["max"]
            for k in model.s_K
        },
        doc="True/false are SWDs available for disposal based on average pressure in the vicinity of the well [boolean]",
    )

    m.objective = Objective(
        expr=sum(m.vb_y_dist[i, j] for i in model.s_K for j in prox),
        sense=maximize,
        doc="Objective function",
    )
    m.objective.deactivate()

    return model


def solve_discrete_water_quality(model, opt, scaled):
    # Discrete water quality method consists of 3 steps:
    # Step 1 - generate a feasible initial solution
    # Step 1a -- fix discrete water quality variables
    # Step 1b -- solve model, obtain optimal flows without considering quality
    # Step 1c -- fix or bound all non quality variables
    # Step 1d -- free discrete water quality variables
    # Step 1e -- solve model again for a feasible initial solution for discrete water quality
    # Step 2 - solve full discrete water quality
    # Step 2a -- free or remove bounds for all non quality variables
    # Step 2b -- call solver to solve whole model using previous solve as initial solution
    # Step 3 - Return solution

    # Step 1 - generate a feasible initial solution
    v_DQ = model.scaled_v_DQ if scaled else model.v_DQ
    # Step 1a - fix discrete water quality variables
    v_DQ.fix()
    # Step 1b - solve model, obtain optimal flows without considering quality
    if opt.options["solver"] == "CPLEX":
        opt.solve(
            model,
            tee=True,
            add_options=["gams_model.optfile=1;"],
        )
    else:
        opt.solve(model, tee=True)
    # Step 1c - fix or bound all non quality variables
    prefix = "scaled_" if scaled else ""
    discrete_variables_names = {
        prefix + "v_F_DiscretePiped",
        prefix + "v_F_DiscreteTrucked",
        prefix + "v_F_DiscreteDisposalDestination",
        prefix + "v_F_DiscreteFlowOutStorage",
        prefix + "v_L_DiscreteStorage",
        prefix + "v_F_DiscreteFlowTreatment",
        prefix + "v_F_DiscreteFlowOutNode",
        prefix + "v_F_DiscreteBRDestination",
        prefix + "v_F_DiscreteFlowCPIntermediate",
        prefix + "v_F_DiscreteFlowCPStorage",
        prefix + "v_L_DiscretePadStorage",
        prefix + "v_F_DiscreteFlowOutPadStorage",
        prefix + "v_F_DiscreteFlowInPadStorage",
        prefix + "v_F_DiscreteCPDestination",
        prefix + "v_Q_CompletionPad",
        prefix + "v_ObjectiveWithQuality",
    }
    for var in model.component_objects(Var):
        if var.name in discrete_variables_names:
            continue
        for index in var:
            index_var = var if index is None else var[index]
            value = index_var.value
            # Fix binary variables to their value and bound the continuous variables
            if index_var.domain is Binary:
                index_var.fix(round(value))
            else:
                index_var.setlb(0.99 * value)
                index_var.setub(1.01 * value)
    # Step 1d - free discrete water quality variables
    v_DQ.free()

    # Step 1e - solve model again for a feasible initial solution for discrete water quality
    print("\n")
    print("*" * 50)
    print(" " * 15, "Solving non-discrete water quality model")
    print("*" * 50)
    if opt.options["solver"] == "CPLEX":
        opt.solve(
            model,
            tee=True,
            add_options=["gams_model.optfile=1;"],
        )
    else:
        opt.solve(model, tee=True, warmstart=True)

    # Step 2 - solve full discrete water quality
    # Step 2a - free or remove bounds for all non quality variables
    for var in model.component_objects(Var):
        if var.name in discrete_variables_names:
            continue
        for index in var:
            index_var = var if index is None else var[index]
            value = index_var.value
            # unfix binary variables and unbound the continuous variables

            if index_var.domain is Binary:
                index_var.free()
            else:
                index_var.setlb(0)
                index_var.setub(None)

    # Step 2b - call solver to solve whole model using previous solve as initial solution
    print("\n")
    print("*" * 50)
    print(" " * 15, "Solving discrete water quality model")
    print("*" * 50)
    if opt.options["solver"] == "CPLEX":
        results = opt.solve(
            model,
            tee=True,
            warmstart=True,
            add_options=["gams_model.optfile=1;"],
        )
    else:
        results = opt.solve(model, tee=True, warmstart=True)

    # Step 3 - Return solution
    return results


def calc_new_pres(model_h, ps, l1, l2, t):
    D_eff = value(model_h.hydraulics.p_Initial_Pipeline_Diameter[l1, l2]) + sum(
        value(model_h.vb_y_Pipeline[l1, l2, d])
        * value(model_h.df_parameters["PipelineDiameterValues"][d])
        for d in model_h.s_D
    )
    if value(model_h.v_F_Piped[(l1, l2), t]) > 0.01:
        if D_eff > 0.1:
            HW_loss = (
                10.704
                * (
                    (
                        value(
                            pyunits.convert(
                                model_h.v_F_Piped[l1, l2, t],
                                to_units=pyunits.m**3 / pyunits.s,
                            )
                        )
                        / value(model_h.hydraulics.p_iota_HW_material_factor_pipeline)
                    )
                    ** 1.85
                )
                * value(
                    pyunits.convert(
                        model_h.p_lambda_Pipeline[l1, l2], to_units=pyunits.m
                    )
                )
            ) / ((D_eff * 0.0254) ** 4.87)
        else:
            HW_loss = 0
    else:
        HW_loss = 0
    P2 = ps
    (
        +value(model_h.p_zeta_Elevation[l1]) * value(model_h.hydraulics.p_rhog)
        - value(model_h.p_zeta_Elevation[l2]) * value(model_h.hydraulics.p_rhog)
        - value(model_h.hydraulics.v_HW_loss[l1, l2, t])
        * value(model_h.hydraulics.p_rhog)
        + value(model_h.hydraulics.v_PumpHead[l1, l2, t])
        * value(model_h.hydraulics.p_rhog)
        - value(model_h.hydraulics.v_ValveHead[l1, l2, t])
        * value(model_h.hydraulics.p_rhog)
    )

    return P2


def solve_model(model, options=None):
    """
    Solve the optimization model. options is a dictionary with the following options:

    `solver`: Either a string with solver name or a tuple of strings with several solvers to try and load in order. PARETO currently supports Gurobi (commercial), CPLEX (commercial) and CBC (free) solvers, but it might be possible to use other MILP solvers as well. Default = ("gurobi_direct", "gurobi", "gams:CPLEX", "cbc")

    `running_time`: Maximum solver running time in seconds. Default = 60

    `gap`: Solver gap. Default = 0

    `deactivate_slacks`: `True` to deactivate slack variables, `False` to use slack variables. Default = `True`

    `scale_model`: `True` to apply scaling to the model, `False` to not apply scaling. Default = `False`

    `scaling_factor`: Scaling factor to apply to the model (only relevant if `scale_model` is `True`). Default = 1000000

    `gurobi_numeric_focus`: The `NumericFocus` parameter to pass to the Gurobi solver. This parameter can be 1, 2, or 3, and per Gurobi, "settings 1-3 increasingly shift the focus towards more care in numerical computations, which can impact performance." This option is ignored if a solver other than Gurobi is used. Default = 1

    `only_subsurface_block`: If `True`, solve only the subsurface risk block and then return without solving the parent model. This option only has an affect if the subsurface risk block has been created. Default = `False`

    Returns the solver results object.
    """
    # default option values
    running_time = 60  # solver running time in seconds
    gap = 0  # solver gap
    deactivate_slacks = True  # yes/no to deactivate slack variables
    use_scaling = False  # yes/no to scale the model
    scaling_factor = 1000000  # scaling factor to apply to the model (only relevant if scaling is turned on)
    gurobi_numeric_focus = 1
    only_subsurface_block = False  # yes/no to only solve the subsurface risk block
    solver = (
        "gurobi_direct",
        "gurobi",
        "gams:CPLEX",
        "cbc",
    )  # solvers to try and load in order

    # raise an exception if options is neither None nor a user-provided dictionary
    if options is not None and not isinstance(options, dict):
        raise Exception("options must either be None or a dictionary")

    # Override any default values with user-specified options
    if options is not None:
        if "running_time" in options.keys():
            running_time = options["running_time"]
        if "gap" in options.keys():
            gap = options["gap"]
        if "deactivate_slacks" in options.keys():
            deactivate_slacks = options["deactivate_slacks"]
        if "scale_model" in options.keys():
            # Note - we can't use "scale_model" as a local variable name because
            # that is the name of the function that is called later to apply
            # scaling to the model. So use "use_scaling" instead
            use_scaling = options["scale_model"]
        if "scaling_factor" in options.keys():
            scaling_factor = options["scaling_factor"]
        if "solver" in options.keys():
            solver = options["solver"]
        if "gurobi_numeric_focus" in options.keys():
            gurobi_numeric_focus = options["gurobi_numeric_focus"]
        if "only_subsurface_block" in options.keys():
            only_subsurface_block = options["only_subsurface_block"]

    # Load solver
    opt = get_solver(*solver) if type(solver) is tuple else get_solver(solver)

    # The below code is not the best way to check for solver but this works.
    # Checks for CPLEX using gams.
    if opt.options["solver"] == "CPLEX":
        with open(f"{opt.options['solver']}.opt", "w") as f:
            f.write(
                f"$onecho > {opt.options['solver']}.opt\n optcr={gap}\n running_time={running_time} $offecho"
            )

    # Set maximum running time for solver
    set_timeout(opt, timeout_s=running_time)

    # Set solver gap
    if opt.type in ("gurobi_direct", "gurobi"):
        # Apply Gurobi specific options
        opt.options["mipgap"] = gap
        opt.options["NumericFocus"] = gurobi_numeric_focus
    elif opt.type in ("cbc"):
        # Apply CBC specific option
        opt.options["ratioGap"] = gap

    # Deactivate slack variables if necessary
    if deactivate_slacks:
        model.v_C_Slack.fix(0)
        model.v_S_FracDemand.fix(0)
        model.v_S_Production.fix(0)
        model.v_S_Flowback.fix(0)
        model.v_S_PipelineCapacity.fix(0)
        model.v_S_StorageCapacity.fix(0)
        model.v_S_DisposalCapacity.fix(0)
        model.v_S_TreatmentCapacity.fix(0)
        model.v_S_BeneficialReuseCapacity.fix(0)

    if model.do_subsurface_risk_calcs:
        print("\n")
        print("*" * 50)
        print(" " * 6, "Calculating subsurface risk metrics")
        print("*" * 50)

        # Certain indexes of model.subsurface.vb_y_dist need to be fixed to 1 for
        # the subsurface risk block to work properly
        for site in model.s_K:
            for factor in ["orphan", "inactive", "EQ", "fault", "HP_LP"]:
                model.subsurface.vb_y_dist[site, factor].unfix()
                if factor in ("orphan", "inactive") and model.subsurface.deep[site]:
                    model.subsurface.vb_y_dist[site, factor].fix(1)

        # Solve just the subsurface risk block
        model.subsurface.objective.activate()
        results_subsurface = opt.solve(model.subsurface, tee=True)
        model.subsurface.objective.deactivate()

        # Fix all indexes of vb_y_dist before proceeding with solving the rest of
        # the model
        for site in model.s_K:
            for factor in ["orphan", "inactive", "EQ", "fault", "HP_LP"]:
                model.subsurface.vb_y_dist[site, factor].fix()
        results_subsurface.write()

        # Return now if the user only wants to solve the subsurface risk block
        if only_subsurface_block:
            return results_subsurface
    else:
        if only_subsurface_block:
            print(
                "Subsurface risk block has not been created. Proceeding with solving network model."
            )

    if use_scaling:
        # Step 1: scale model
        scaled_model = scale_model(model, scaling_factor=scaling_factor)
        # Step 2: solve scaled mathematical model
        print("\n")
        print("*" * 50)
        print(" " * 15, "Solving scaled model")
        print("*" * 50)
        # Step 3: check model to be solved
        #       option 3.1 - full space model,
        #       option 3.2 - post process water quality,
        #       option 3.3 - discrete water quality,
        if model.config.water_quality is WaterQuality.discrete:
            # option 3.3:
            results = solve_discrete_water_quality(scaled_model, opt, scaled=True)
        elif model.config.water_quality is WaterQuality.post_process:
            # option 3.2:
            if opt.options["solver"] == "CPLEX":
                results = opt.solve(
                    scaled_model,
                    tee=True,
                    add_options=["gams_model.optfile=1;"],
                )
            else:
                results = opt.solve(scaled_model, tee=True)
            if results.solver.termination_condition != TerminationCondition.infeasible:
                TransformationFactory("core.scale_model").propagate_solution(
                    scaled_model, model
                )
                model = postprocess_water_quality_calculation(model, opt)
        else:
            # option 3.1:
            if opt.options["solver"] == "CPLEX":
                results = opt.solve(
                    scaled_model,
                    tee=True,
                    add_options=["gams_model.optfile=1;"],
                )
            else:
                opt.options["DualReductions"] = 0
                results = opt.solve(scaled_model, tee=True)

        # Step 4: propagate scaled model results to original model
        if results.solver.termination_condition != TerminationCondition.infeasible:
            # if model is optimal propagate scaled model results to original model
            TransformationFactory("core.scale_model").propagate_solution(
                scaled_model, model
            )
    else:
        # Step 1: solve unscaled mathematical model
        print("\n")
        print("*" * 50)
        print(" " * 15, "Solving unscaled model")
        print("*" * 50)
        # Step 2: check model to be solved
        #       option 2.1 - full space model,
        #       option 2.2 - post process water quality,
        #       option 2.3 - discrete water quality,
        if model.config.water_quality is WaterQuality.discrete:
            # option 2.3:
            results = solve_discrete_water_quality(model, opt, scaled=False)
        elif model.config.water_quality is WaterQuality.post_process:
            # option 2.2:
            if opt.options["solver"] == "CPLEX":
                results = opt.solve(
                    model,
                    tee=True,
                    add_options=["gams_model.optfile=1;"],
                )
            else:
                results = opt.solve(model, tee=True)
            if results.solver.termination_condition != TerminationCondition.infeasible:
                model = postprocess_water_quality_calculation(model, opt)
        else:
            # option 2.1:
            if opt.options["solver"] == "CPLEX":
                results = opt.solve(
                    model,
                    tee=True,
                    add_options=["gams_model.optfile=1;"],
                )
            else:
                opt.options["DualReductions"] = 0
                results = opt.solve(model, tee=True)

    if results.solver.termination_condition == TerminationCondition.infeasible:
        print(
            "WARNING: Model is infeasible. We recommend adding Slack variables to avoid infeasibilities\n, \
                however this is an indication that the input data should be revised. \
                This can be done by selecting 'deactivate_slacks': False in the options"
        )

    # For a given time t and beneficial reuse option o, if the beneficial reuse
    # minimum flow parameter is zero (p_sigma_BeneficialReuseMinimum[o, t] = 0)
    # and the optimal total flow to beneficial reuse is zero
    # (v_F_BeneficialReuseDestination[o, t] = 0), then it is arbitrary whether
    # the binary variable vb_y_BeneficialReuse[o, t] takes a value of 0 or 1. In
    # these cases it's preferred to report a value of 0 to the user, so change
    # the value of vb_y_BeneficialReuse[o, t] as necessary.
    for t in model.s_T:
        for o in model.s_O:
            if (
                value(model.p_sigma_BeneficialReuseMinimum[o, t]) < 1e-6
                and value(model.v_F_BeneficialReuseDestination[o, t]) < 1e-6
                and value(model.vb_y_BeneficialReuse[o, t] > 0)
            ):
                model.vb_y_BeneficialReuse[o, t].value = 0

    # post-process infrastructure buildout
    if model.config.infrastructure_timing == InfrastructureTiming.true:
        infrastructure_timing(model)

    results.write()

    if model.config.hydraulics != Hydraulics.false:
        model_h = pipeline_hydraulics(model)

        if model.config.hydraulics == Hydraulics.post_process:
            # In the post-process solve, only the hydraulics block is solved.

            mh = model_h.hydraulics
            # Calculate hydraulics. The following condition is used to avoid attribute error when
            # using gurobi_direct on hydraulics sub-block
            if opt.options["solver"] == "CPLEX":
                results_2 = opt.solve(
                    mh, tee=True, add_options=["gams_model.optfile=1;"]
                )
            elif opt.type == "gurobi_direct":
                results_2 = opt.solve(mh, tee=True, save_results=False)
            else:
                results_2 = opt.solve(mh, tee=True)

        elif model.config.hydraulics == Hydraulics.co_optimize:
            # Currently, this method is supported for only MINLP solvers accessed through GAMS.
            # The default solver is Baron and is set to find the first feasible solution.
            # If the user has SCIP, then the feasible solution from BARON is passed to SCIP, which is then solved to a gap of 0.3.
            # If the user do not have these solvers installed then it limits the use of co_optimize method at this time.
            # Ongoing work is geared to address this limitation and will soon be updated here.

            # Adding temporary variable bounds until the bounding method is implemented for the following Vars
            model_h.v_F_Piped.setub(1050)
            model_h.hydraulics.v_Pressure.setub(3.5e6)

            try:
                solver = SolverFactory("gams")
                mathoptsolver = "baron"
            except:
                print(
                    "Either GAMS or a license to BARON was not found. Please add GAMS to the path. If you do not have GAMS or BARON, \
                      please continue to use the post-process method for hydraulics at this time"
                )
            else:
                solver_options = {
                    "firstfeas": 1,
                }

                if not os.path.exists("temp"):
                    os.makedirs("temp")

                with open("temp/" + mathoptsolver + ".opt", "w") as f:
                    for k, v in solver_options.items():
                        f.write(str(k) + " " + str(v) + "\n")

                results_baron = solver.solve(
                    model_h,
                    tee=True,
                    keepfiles=True,
                    solver=mathoptsolver,
                    tmpdir="temp",
                    io_options=["gams_model.optfile=1;"],
                )
                try:
                    # second solve with SCIP
                    solver2 = SolverFactory("scip", solver_io="nl")
                    print("  ")
                    print(
                        "WARNING: A default relative optimality gap of 30%/ is set to obtain good solutions at this time"
                    )
                    print("  ")
                except:
                    print(
                        "A second solve with SCIP cannot be executed as SCIP was not found. Please add it to Path. \
                          If you do not haev SCIP, proceed with caution when using solution obtain from first solve using BARON"
                    )
                else:
                    results_2 = solver2.solve(
                        model_h, options={"limits/gap": 0.3}, tee=True
                    )
        elif model.config.hydraulics == Hydraulics.co_optimize_linearized:
            # Adding temporary variable bounds until the bounding method is implemented for the following Vars
            model_h.v_F_Piped.setub(1050)
            model_h.hydraulics.v_Pressure.setub(3.5e6)
            if opt.options["solver"] == "CPLEX":
                results_2 = opt.solve(
                    model_h,
                    tee=True,
                    keepfiles=True,
                    io_options=["gams_model.optfile=1;"],
                )
            else:
                results_2 = opt.solve(model_h, tee=True, keepfiles=True)

            # Check the feasibility of the results with regards to max pressure and node pressures

            # Navigate over all the times
            flagV = 0
            flagU = 0
            for t in model.s_T:
                Press_dict = {}
                for p in model.s_PP:
                    Press_dict[p] = value(model_h.hydraulics.v_Pressure[p, t])
                    while True:
                        pres_dict_keys = list(Press_dict.keys())
                        for l1, l2 in model.s_LLA:
                            if l1 in Press_dict.keys():
                                ps = Press_dict[l1]
                                this_p = calc_new_pres(model_h, ps, l1, l2, t)
                                Press_dict[l2] = this_p
                                if (
                                    this_p > value(model_h.hydraulics.p_xi_Max_AOP)
                                    and l2 in model.s_N
                                ):
                                    flagV = 1
                                    print(l2, "->", l2 in model.s_N)
                                    print(
                                        "\n\nThe Pressure is ",
                                        this_p,
                                        " and max is ",
                                        value(model_h.hydraulics.p_xi_Max_AOP),
                                    )
                                if this_p < 0 and l2 in model.s_N:
                                    flagU = 1
                        pres_dict_keys2 = list(Press_dict.keys())
                        if pres_dict_keys == pres_dict_keys2:
                            break

            if flagV:
                print("Violation of maximum pressure")
            elif flagU:
                print("Violation of minimum pressure")
            else:
                print("All pressures satisfied ")

        # Once the hydraulics block is solved, it is deactivated to retain the original MILP
        model_h.hydraulics.deactivate()

        results_2.write()
    return results
