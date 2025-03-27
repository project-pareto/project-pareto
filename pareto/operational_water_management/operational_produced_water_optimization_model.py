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
# Title: OPERATIONAL Produced Water Optimization Model

import numpy as np
from pyomo.environ import (
    Var,
    Param,
    Set,
    ConcreteModel,
    Constraint,
    Objective,
    minimize,
    NonNegativeReals,
    Reals,
    Binary,
    units as pyunits,
)

from pyomo.core.base.constraint import simple_constraint_rule

from pyomo.common.config import ConfigBlock, ConfigValue, In, Bool

from pareto.utilities.units_support import units_setup
from pareto.utilities.build_utils import (
    build_sets,
    build_common_params,
    build_common_vars,
    build_common_constraints,
)
from pareto.utilities.enums import (
    ProdTank,
    WaterQuality,
)


# create config dictionary
CONFIG = ConfigBlock()

CONFIG.declare(
    "has_pipeline_constraints",
    ConfigValue(
        default=True,
        domain=Bool,
        description="build pipeline constraints",
        doc="""Indicates whether holdup terms should be constructed or not.
**default** - True.
**Valid values:** {
**True** - construct pipeline constraints,
**False** - do not construct pipeline constraints}""",
    ),
)

CONFIG.declare(
    "production_tanks",
    ConfigValue(
        default=ProdTank.individual,
        domain=In(ProdTank),
        description="production tank type selection",
        doc="Type of production tank arrangement (i.e., Individual, Equalized)",
    ),
)

CONFIG.declare(
    "water_quality",
    ConfigValue(
        default=WaterQuality.post_process,
        domain=In(WaterQuality),
        description="Water quality",
        doc="""Selection to include water quality
        ***default*** - WaterQuality.continuous
        **Valid Values:** - {
        **WaterQuality.false** - Exclude water quality from model,
        **WaterQuality.post_process** - Include water quality as post process
        **WaterQuality.discrete** - Include water quality as discrete values in model
        }""",
    ),
)


def create_model(df_sets, df_parameters, default={}):
    """
    create operational model
    Args: list with sets and parameters
    Return: mathematical model
    """

    model = ConcreteModel()
    # import config dictionary
    model.config = CONFIG(default)
    model.type = "operational"
    model.df_sets = df_sets
    model.df_parameters = df_parameters
    model.proprietary_data = df_parameters["proprietary_data"][0]

    # Setup units for model
    units_setup(model)

    model.proprietary_data = df_parameters["proprietary_data"][0]

    # Build sets #
    build_sets(model)

    # Build parameters #
    build_common_params(model)

    if model.config.production_tanks == ProdTank.individual:
        model.p_PAL = Param(
            model.s_P,
            model.s_A,
            default=0,
            initialize=df_parameters["PAL"],
            doc="Valid pad-to-tank links [-]",
        )
    elif model.config.production_tanks == ProdTank.equalized:
        model.p_PAL = Param(
            model.s_P, model.s_A, default=0, doc="Valid pad-to-tank links [-]"
        )
    else:
        raise Exception("storage type not supported")

    # TODO: For EXISTING/INITAL pipeline capacity (l,l_tilde)=(l_tilde=l); needs implemented!

    if model.config.production_tanks == ProdTank.individual:
        model.p_sigma_ProdTank = Param(
            model.s_P,
            model.s_A,
            default=pyunits.convert_value(
                500,
                from_units=pyunits.oil_bbl,
                to_units=model.model_units["volume"],
            ),
            units=model.model_units["volume"],
            doc="Production tank capacity [volume]",
        )
        model.p_lambda_ProdTank = Param(
            model.s_P,
            model.s_A,
            default=0,
            initialize={},
            units=model.model_units["volume"],
            doc="Initial water level in production tank [volume]",
        )
    elif model.config.production_tanks == ProdTank.equalized:
        model.p_sigma_ProdTank = Param(
            model.s_P,
            default=pyunits.convert_value(
                500,
                from_units=pyunits.oil_bbl,
                to_units=model.model_units["volume"],
            ),
            units=model.model_units["volume"],
            initialize=df_parameters["ProductionTankCapacity"],
            doc="Combined capacity equalized production tanks [volume]",
        )
        model.p_lambda_ProdTank = Param(
            model.s_P,
            default=0,
            initialize={},
            units=model.model_units["volume"],
            doc="Initial water level in equalized production tanks [volume]",
        )
    else:
        raise Exception("storage type not supported")

    model.p_sigma_Reuse = Param(
        model.s_O,
        default=0,
        initialize={},
        units=model.model_units["volume_time"],
        doc="Initial reuse capacity at reuse site [volume/time]",
    )
    model.p_sigma_MinTruckFlow = Param(
        default=0,
        initialize=pyunits.convert_value(
            model.df_parameters["MinTruckFlow"],
            from_units=model.user_units["volume_time"],
            to_units=model.model_units["volume_time"],
        ),
        units=model.model_units["volume_time"],
        doc="Minimum truck capacity [volume_time]",
    )
    model.p_sigma_MaxTruckFlow = Param(
        default=0,
        initialize=pyunits.convert_value(
            model.df_parameters["MaxTruckFlow"],
            from_units=model.user_units["volume_time"],
            to_units=model.model_units["volume_time"],
        ),
        units=model.model_units["volume_time"],
        doc="Maximum truck capacity [volume_time]",
    )

    model.p_pi_PadStorage = Param(
        model.s_CP,
        model.s_T,
        default=0,
        initialize={
            key: pyunits.convert_value(
                value,
                from_units=model.user_units["currency"],
                to_units=model.model_units["currency"],
            )
            for key, value in model.df_parameters["PadStorageCost"].items()
        },
        units=model.model_units["currency"],
        doc="Completions pad storage operational cost if used [currency]",
    )

    # Build variables #
    build_common_vars(model)

    model.v_Objective = Var(
        within=Reals,
        units=model.model_units["currency"],
        doc="Objective function variable [currency]",
    )

    model.v_F_UnusedTreatedWater = Var(
        model.s_R,
        model.s_T,
        within=NonNegativeReals,
        initialize=0,
        units=model.model_units["volume_time"],
        doc="Water leftover from the treatment process [volume/time]",
    )

    if model.config.production_tanks == ProdTank.individual:
        model.v_F_Drain = Var(
            model.s_P,
            model.s_A,
            model.s_T,
            within=NonNegativeReals,
            units=model.model_units["volume_time"],
            doc="Produced water drained from" " production tank [volume/time]",
        )
        model.v_L_ProdTank = Var(
            model.s_P,
            model.s_A,
            model.s_T,
            within=NonNegativeReals,
            units=model.model_units["volume"],
            doc="Water level in production tank [volume]",
        )
    elif model.config.production_tanks == ProdTank.equalized:
        model.v_F_Drain = Var(
            model.s_P,
            model.s_T,
            within=NonNegativeReals,
            units=model.model_units["volume_time"],
            doc="Produced water drained from" " production tank [volume/time]",
        )
        model.v_L_ProdTank = Var(
            model.s_P,
            model.s_T,
            within=NonNegativeReals,
            units=model.model_units["volume"],
            doc="Water level in production tank [volume]",
        )
    else:
        raise Exception("storage type not supported")

    model.v_B_Production = Var(
        model.s_P,
        model.s_T,
        within=NonNegativeReals,
        units=model.model_units["volume_time"],
        doc="Produced water for transport from pad [volume/time]",
    )
    model.v_C_PadStorage = Var(
        model.s_CP,
        model.s_T,
        within=NonNegativeReals,
        units=model.model_units["currency"],
        doc="Cost of storing produced water at completions pad storage [currency]",
    )

    model.v_C_TotalPadStorage = Var(
        within=NonNegativeReals,
        units=model.model_units["currency"],
        doc="Total cost of storing produced water at completions site [currency]",
    )

    model.v_F_TreatmentDestination = Var(
        model.s_R,
        model.s_T,
        within=NonNegativeReals,
        units=model.model_units["volume_time"],
        doc="Total deliveries to treatment site [volume/time]",
    )

    # Binary variables
    model.vb_z_PadStorage = Var(
        model.s_CP,
        model.s_T,
        within=Binary,
        initialize=0,
        doc="Completions pad storage use",
    )

    model.vb_y_Truck = Var(
        model.s_LLT,
        model.s_T,
        within=Binary,
        initialize=0,
        doc="Trucking between two locations",
    )

    # Define objective function #
    def ObjectiveFunctionRule(model):
        return model.v_Objective == (
            model.v_C_TotalSourced
            + model.v_C_TotalDisposal
            + model.v_C_TotalTreatment
            + model.v_C_TotalReuse
            + model.v_C_TotalPiping
            + model.v_C_TotalStorage
            + model.v_C_TotalPadStorage
            + model.v_C_TotalTrucking
            + model.v_C_Slack
            - model.v_R_TotalStorage
        )

    model.ObjectiveFunction = Constraint(
        rule=ObjectiveFunctionRule, doc="Objective function"
    )

    # Build constraints #
    build_common_constraints(model)

    def TrucksMaxCapacityRule(model, l, l_tilde, t):
        if (l, l_tilde) in model.s_LLT:
            return (
                model.v_F_Trucked[l, l_tilde, t]
                <= model.p_sigma_MaxTruckFlow * model.vb_y_Truck[l, l_tilde, t]
            )
        else:
            return Constraint.Skip

    model.TrucksMaxCapacity = Constraint(
        model.s_L,
        model.s_L,
        model.s_T,
        rule=TrucksMaxCapacityRule,
        doc="Maximum amount of water that can be transported by trucks",
    )

    def TrucksMinCapacityRule(model, l, l_tilde, t):
        if (l, l_tilde) in model.s_LLT:
            return (
                model.v_F_Trucked[l, l_tilde, t]
                >= model.p_sigma_MinTruckFlow * model.vb_y_Truck[l, l_tilde, t]
            )
        else:
            return Constraint.Skip

    model.TrucksMinCapacity = Constraint(
        model.s_L,
        model.s_L,
        model.s_T,
        rule=TrucksMinCapacityRule,
        doc="Minimum amount of water that can be transported by trucks",
    )

    if model.config.production_tanks == ProdTank.individual:

        def ProductionTankBalanceRule(model, p, a, t):
            if t == model.s_T.first():
                if p in model.s_P and a in model.s_A:
                    if model.p_PAL[p, a]:
                        return (
                            model.v_L_ProdTank[p, a, t]
                            == model.p_lambda_ProdTank[p, a]
                            + model.p_beta_Production[p, a, t]
                            + model.p_beta_Flowback[p, a, t]
                            - model.v_F_Drain[p, a, t]
                        )
                    else:
                        return Constraint.Skip
                else:
                    return Constraint.Skip
            else:
                if p in model.s_P and a in model.s_A:
                    if model.p_PAL[p, a]:
                        return (
                            model.v_L_ProdTank[p, a, t]
                            == model.v_L_ProdTank[p, a, model.s_T.prev(t)]
                            + model.p_beta_Production[p, a, t]
                            + model.p_beta_Flowback[p, a, t]
                            - model.v_F_Drain[p, a, t]
                        )
                    else:
                        return Constraint.Skip
                else:
                    return Constraint.Skip

        model.ProductionTankBalance = Constraint(
            model.s_P,
            model.s_A,
            model.s_T,
            rule=ProductionTankBalanceRule,
            doc="Production tank balance",
        )
    elif model.config.production_tanks == ProdTank.equalized:

        def ProductionTankBalanceRule(model, p, t):
            if t == model.s_T.first():
                if p in model.s_P:
                    return (
                        model.v_L_ProdTank[p, t]
                        == model.p_lambda_ProdTank[p]
                        + model.p_beta_Production[p, t]
                        + model.p_beta_Flowback[p, t]
                        - model.v_F_Drain[p, t]
                    )
                else:
                    return Constraint.Skip
            else:
                if p in model.s_P:
                    return (
                        model.v_L_ProdTank[p, t]
                        == model.v_L_ProdTank[p, model.s_T.prev(t)]
                        + model.p_beta_Production[p, t]
                        + model.p_beta_Flowback[p, t]
                        - model.v_F_Drain[p, t]
                    )
                else:
                    return Constraint.Skip

        model.ProductionTankBalance = Constraint(
            model.s_P,
            model.s_T,
            rule=ProductionTankBalanceRule,
            doc="Production tank balance",
        )
    else:
        raise Exception("storage type not supported")

    if model.config.production_tanks == ProdTank.individual:

        def ProductionTankCapacityRule(model, p, a, t):
            if p in model.s_P and a in model.s_A:
                if model.p_PAL[p, a]:
                    return model.v_L_ProdTank[p, a, t] <= model.p_sigma_ProdTank[p, a]
                else:
                    return Constraint.Skip
            else:
                return Constraint.Skip

        model.ProductionTankCapacity = Constraint(
            model.s_P,
            model.s_A,
            model.s_T,
            rule=ProductionTankCapacityRule,
            doc="Production tank capacity",
        )
    elif model.config.production_tanks == ProdTank.equalized:

        def ProductionTankCapacityRule(model, p, t):
            if p in model.s_P:
                return model.v_L_ProdTank[p, t] <= model.p_sigma_ProdTank[p]
            else:
                return Constraint.Skip

        model.ProductionTankCapacity = Constraint(
            model.s_P,
            model.s_T,
            rule=ProductionTankCapacityRule,
            doc="Production tank capacity",
        )
    else:
        raise Exception("storage type not supported")

    if model.config.production_tanks == ProdTank.individual:

        def TankToPadProductionBalanceRule(model, p, t):
            return (
                sum(model.v_F_Drain[p, a, t] for a in model.s_A if model.p_PAL[p, a])
                == model.v_B_Production[p, t]
            )

        model.TankToPadProductionBalance = Constraint(
            model.s_P,
            model.s_T,
            rule=TankToPadProductionBalanceRule,
            doc="Tank-to-pad production balance",
        )
    elif model.config.production_tanks == ProdTank.equalized:

        def TankToPadProductionBalanceRule(model, p, t):
            return model.v_F_Drain[p, t] == model.v_B_Production[p, t]

        model.TankToPadProductionBalance = Constraint(
            model.s_P,
            model.s_T,
            rule=TankToPadProductionBalanceRule,
            doc="Tank-to-pad production balance",
        )
    else:
        raise Exception("storage type not supported")

    if model.config.production_tanks == ProdTank.individual:

        def TerminalProductionTankLevelBalanceRule(model, p, a, t):
            if t == model.s_T.last():
                if p in model.s_P and a in model.s_A:
                    if model.p_PAL[p, a]:
                        return (
                            model.v_L_ProdTank[p, a, t] == model.p_lambda_ProdTank[p, a]
                        )
                    else:
                        return Constraint.Skip
                else:
                    return Constraint.Skip
            else:
                return Constraint.Skip

        model.TerminalProductionTankLevelBalance = Constraint(
            model.s_P,
            model.s_A,
            model.s_T,
            rule=TerminalProductionTankLevelBalanceRule,
            doc="Terminal production tank level balance",
        )
    elif model.config.production_tanks == ProdTank.equalized:

        def TerminalProductionTankLevelBalanceRule(model, p, t):
            if t == model.s_T.last():
                if p in model.s_P:
                    return model.v_L_ProdTank[p, t] == model.p_lambda_ProdTank[p]
                else:
                    return Constraint.Skip
            else:
                return Constraint.Skip

        model.TerminalProductionTankLevelBalance = Constraint(
            model.s_P,
            model.s_T,
            rule=TerminalProductionTankLevelBalanceRule,
            doc="Terminal production tank level balance",
        )
    else:
        raise Exception("storage type not supported")

    def TreatmentBalanceRule(model, r, t):
        return (
            model.p_epsilon_Treatment[r, "TDS"]
            * (
                sum(
                    model.v_F_Piped[l, r, t] for l in model.s_L if (l, r) in model.s_LLA
                )
                + sum(
                    model.v_F_Trucked[l, r, t]
                    for l in model.s_L
                    if (l, r) in model.s_LLT
                )
            )
            == sum(model.v_F_Piped[r, l, t] for l in model.s_L if (l, r) in model.s_LLA)
            + model.v_F_UnusedTreatedWater[r, t]
        )

    model.TreatmentBalance = Constraint(
        model.s_R,
        model.s_T,
        rule=simple_constraint_rule(TreatmentBalanceRule),
        doc="Treatment balance",
    )

    def BeneficialReuseCapacityRule(model, o, t):
        return (
            sum(model.v_F_Piped[l, o, t] for l in model.s_L if (l, o) in model.s_LLA)
            + sum(
                model.v_F_Trucked[l, o, t] for l in model.s_L if (l, o) in model.s_LLT
            )
            <= model.p_sigma_Reuse[o] + model.v_S_BeneficialReuseCapacity[o]
        )

    model.BeneficialReuseCapacity = Constraint(
        model.s_O,
        model.s_T,
        rule=BeneficialReuseCapacityRule,
        doc="Beneficial reuse capacity",
    )

    # COMMENT: Beneficial reuse capacity constraint has not been tested yet

    def TreatmentCostRule(model, r, t):
        return (
            model.v_C_Treatment[r, t]
            == (
                sum(
                    model.v_F_Piped[l, r, t] for l in model.s_L if (l, r) in model.s_LLA
                )
                + sum(
                    model.v_F_Trucked[l, r, t]
                    for l in model.s_L
                    if (l, r) in model.s_LLT
                )
            )
            * model.p_pi_Treatment[r]
        )

    model.TreatmentCost = Constraint(
        model.s_R, model.s_T, rule=TreatmentCostRule, doc="Treatment cost"
    )

    def PadStorageCostRule(model, p, t):
        return (
            model.v_C_PadStorage[p, t]
            == model.vb_z_PadStorage[p, t] * model.p_pi_PadStorage[p, t]
        )

    model.PadStorageCost = Constraint(
        model.s_CP,
        model.s_T,
        rule=PadStorageCostRule,
        doc="Completions pad storage cost",
    )

    def TotalPadStorageCostRule(model):
        return model.v_C_TotalPadStorage == sum(
            sum(model.v_C_PadStorage[p, t] for p in model.s_CP) for t in model.s_T
        )

    model.TotalPadStorageCost = Constraint(
        rule=TotalPadStorageCostRule, doc="Total completions pad storage cost"
    )

    def TreatmentDestinationDeliveriesRule(model, r, t):
        return model.v_F_TreatmentDestination[r, t] == sum(
            model.v_F_Piped[l, r, t] for l in model.s_L if (l, r) in model.s_LLA
        ) + sum(model.v_F_Trucked[l, r, t] for l in model.s_L if (l, r) in model.s_LLT)

    model.TreatmentDestinationDeliveries = Constraint(
        model.s_R,
        model.s_T,
        rule=TreatmentDestinationDeliveriesRule,
        doc="Treatment destinations volume",
    )

    # Define Objective and Solve Statement #

    model.objective = Objective(
        expr=model.v_Objective, sense=minimize, doc="Objective function"
    )

    if model.config.water_quality is WaterQuality.discrete:
        model = water_quality_discrete(model, df_parameters, df_sets)

    return model


def water_quality(model):
    # Introduce parameter nu for water quality at each pad
    model.p_nu = Param(
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

    model.p_xi = Param(
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
        doc="Initial Water Quality at storage site [mg/L]",
    )
    # Introduce variable Q to track water quality at each location over time
    model.v_Q = Var(
        model.s_L,
        model.s_QC,
        model.s_T,
        within=NonNegativeReals,
        initialize=0,
        units=model.model_units["concentration"],
        doc="Water quality at location [mg/L]",
    )

    # Material Balance
    def DisposalWaterQualityRule(model, k, qc, t):
        return (
            sum(
                model.v_F_Piped[n, k, t] * model.v_Q[n, qc, t]
                for n in model.s_N
                if model.p_NKA[n, k]
            )
            + sum(
                model.v_F_Piped[s, k, t] * model.v_Q[s, qc, t]
                for s in model.s_S
                if model.p_SKA[s, k]
            )
            + sum(
                model.v_F_Piped[r, k, t] * model.v_Q[r, qc, t]
                for r in model.s_R
                if model.p_RKA[r, k]
            )
            + sum(
                model.v_F_Trucked[s, k, t] * model.v_Q[s, qc, t]
                for s in model.s_S
                if model.p_SKT[s, k]
            )
            + sum(
                model.v_F_Trucked[p, k, t] * model.v_Q[p, qc, t]
                for p in model.s_PP
                if model.p_PKT[p, k]
            )
            + sum(
                model.v_F_Trucked[p, k, t] * model.v_Q[p, qc, t]
                for p in model.s_CP
                if model.p_CKT[p, k]
            )
            + sum(
                model.v_F_Trucked[r, k, t] * model.v_Q[r, qc, t]
                for r in model.s_R
                if model.p_RKT[r, k]
            )
            == model.v_Q[k, qc, t] * model.v_F_DisposalDestination[k, t]
        )

    model.DisposalWaterQuality = Constraint(
        model.s_K,
        model.s_QC,
        model.s_T,
        rule=DisposalWaterQualityRule,
        doc="Disposal water quality rule",
    )

    def StorageSiteWaterQualityRule(model, s, qc, t):
        if t == model.s_T.first():
            return model.p_lambda_Storage[s] * model.p_xi[s, qc] + sum(
                model.v_F_Piped[n, s, t] * model.v_Q[n, qc, t]
                for n in model.s_N
                if model.p_NSA[n, s]
            ) + sum(
                model.v_F_Trucked[p, s, t] * model.v_Q[p, qc, t]
                for p in model.s_PP
                if model.p_PST[p, s]
            ) + sum(
                model.v_F_Trucked[p, s, t] * model.v_Q[p, qc, t]
                for p in model.s_CP
                if model.p_CST[p, s]
            ) == model.v_Q[
                s, qc, t
            ] * (
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
            )
        else:
            return model.v_L_Storage[s, model.s_T.prev(t)] * model.v_Q[
                s, qc, model.s_T.prev(t)
            ] + sum(
                model.v_F_Piped[n, s, t] * model.v_Q[n, qc, t]
                for n in model.s_N
                if model.p_NSA[n, s]
            ) + sum(
                model.v_F_Trucked[p, s, t] * model.v_Q[p, qc, t]
                for p in model.s_PP
                if model.p_PST[p, s]
            ) + sum(
                model.v_F_Trucked[p, s, t] * model.v_Q[p, qc, t]
                for p in model.s_CP
                if model.p_CST[p, s]
            ) == model.v_Q[
                s, qc, t
            ] * (
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
            )

    model.StorageSiteWaterQuality = Constraint(
        model.s_S,
        model.s_QC,
        model.s_T,
        rule=StorageSiteWaterQualityRule,
        doc="Storage site water quality rule",
    )

    # Treatment Facility
    def TreatmentWaterQualityRule(model, r, qc, t):
        return model.p_epsilon_Treatment[r, qc] * (
            sum(
                model.v_F_Piped[n, r, t] * model.v_Q[n, qc, t]
                for n in model.s_N
                if model.p_NRA[n, r]
            )
            + sum(
                model.v_F_Piped[s, r, t] * model.v_Q[s, qc, t]
                for s in model.s_S
                if model.p_SRA[s, r]
            )
            + sum(
                model.v_F_Trucked[p, r, t] * model.v_Q[p, qc, t]
                for p in model.s_PP
                if model.p_PRT[p, r]
            )
            + sum(
                model.v_F_Trucked[p, r, t] * model.v_Q[p, qc, t]
                for p in model.s_CP
                if model.p_CRT[p, r]
            )
        ) == model.v_Q[r, qc, t] * (
            sum(model.v_F_Piped[r, p, t] for p in model.s_CP if model.p_RCA[r, p])
            + model.v_F_UnusedTreatedWater[r, t]
        )

    model.TreatmentWaterQuality = Constraint(
        model.s_R,
        model.s_QC,
        model.s_T,
        rule=simple_constraint_rule(TreatmentWaterQualityRule),
        doc="Treatment water quality",
    )

    def NetworkNodeWaterQualityRule(model, n, qc, t):
        return sum(
            model.v_F_Piped[p, n, t] * model.v_Q[p, qc, t]
            for p in model.s_PP
            if model.p_PNA[p, n]
        ) + sum(
            model.v_F_Piped[p, n, t] * model.v_Q[p, qc, t]
            for p in model.s_CP
            if model.p_CNA[p, n]
        ) + sum(
            model.v_F_Piped[s, n, t] * model.v_Q[s, qc, t]
            for s in model.s_S
            if model.p_SNA[s, n]
        ) + sum(
            model.v_F_Piped[n_tilde, n, t] * model.v_Q[n_tilde, qc, t]
            for n_tilde in model.s_N
            if model.p_NNA[n_tilde, n]
        ) == model.v_Q[
            n, qc, t
        ] * (
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
        )

    model.NetworkWaterQuality = Constraint(
        model.s_N,
        model.s_QC,
        model.s_T,
        rule=NetworkNodeWaterQualityRule,
        doc="Network water quality",
    )

    def BeneficialReuseWaterQuality(model, o, qc, t):
        return (
            sum(
                model.v_F_Piped[n, o, t] * model.v_Q[n, qc, t]
                for n in model.s_N
                if model.p_NOA[n, o]
            )
            + sum(
                model.v_F_Piped[s, o, t] * model.v_Q[s, qc, t]
                for s in model.s_S
                if model.p_SOA[s, o]
            )
            + sum(
                model.v_F_Trucked[p, o, t] * model.v_Q[p, qc, t]
                for p in model.s_PP
                if model.p_POT[p, o]
            )
            == model.v_Q[o, qc, t] * model.v_F_BeneficialReuseDestination[o, t]
        )

    model.BeneficialReuseWaterQuality = Constraint(
        model.s_O,
        model.s_QC,
        model.s_T,
        rule=BeneficialReuseWaterQuality,
        doc="Beneficial reuse capacity",
    )

    # Fix variables
    # Fix variables: produced water flows, binary
    model.v_F_Piped.fix()
    model.v_F_Trucked.fix()
    model.v_F_Sourced.fix()
    model.v_F_PadStorageIn.fix()
    model.v_F_PadStorageOut.fix()
    model.v_L_Storage.fix()
    model.v_F_UnusedTreatedWater.fix()
    model.v_F_DisposalDestination.fix()
    model.v_F_BeneficialReuseDestination.fix()

    # Use p_nu to fix v_Q for pads
    for p in model.s_P:
        for qc in model.s_QC:
            for t in model.s_T:
                model.v_Q[p, qc, t].fix(model.p_nu[p, qc])

    return model


def postprocess_water_quality_calculation(model, df_sets, df_parameters, opt):
    # Add water quality formulation to input solved model
    water_quality_model = water_quality(model, df_sets, df_parameters)
    # Calculate water quality
    opt.solve(water_quality_model, tee=True)

    return water_quality_model


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
            discrete_quality[(quality_component, discrete_qualities[i])] = value
    return discrete_quality


def discrete_water_quality_list(steps=6) -> list:
    discrete_qualities = []
    # Create list ["Q0", "Q1", ... , "QN"] qualities based on the number of steps.
    for i in range(0, steps):
        discrete_qualities.append("Q{0}".format(i))
    return discrete_qualities


def water_quality_discrete(model, df_parameters, df_sets):
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
    # Quality of externally sourced water
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

    StorageInitialWaterQuality_convert_to_model = {
        key: pyunits.convert_value(
            value,
            from_units=model.user_units["concentration"],
            to_units=model.model_units["concentration"],
        )
        for key, value in model.df_parameters["StorageInitialWaterQuality"].items()
        if value
    }
    # Initial water quality at storage site
    model.p_xi_StorageSite = Param(
        model.s_S,
        model.s_QC,
        default=(
            max(StorageInitialWaterQuality_convert_to_model.values()) * 100
            if StorageInitialWaterQuality_convert_to_model
            else pyunits.convert_value(
                0,
                from_units=model.user_units["concentration"],
                to_units=model.model_units["concentration"],
            )
        ),
        initialize=StorageInitialWaterQuality_convert_to_model,
        units=model.model_units["concentration"],
        doc="Initial Water Quality at storage site [concentration]",
    )

    # Create list of discretized qualities
    discrete_quality_list = discrete_water_quality_list(6)

    # Create set with the list of discretized qualities
    model.s_Q = Set(initialize=discrete_quality_list, doc="Discrete water qualities")

    # Initialize values for each discrete quality
    model.p_discrete_quality = Param(
        model.s_QC,
        model.s_Q,
        initialize=discretize_water_quality(
            df_parameters, df_sets, discrete_quality_list
        ),
        units=model.model_units["concentration"],
        doc="Discretization of water components",
    )

    # For the discretization we need a upperbound for the maximum number of trucks for each truck flow
    model.p_max_number_of_trucks = Param(
        initialize=100,
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
        initialize=(model.s_K | model.s_S | model.s_R | model.s_O | model.s_N),
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
        doc="Discrete quality at location ql at time t for component qc",
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
            rule=lambda model, l1, l2, t, qc, q: model.v_F_DiscretePiped[
                l1, l2, t, qc, q
            ]
            <= model.p_sigma_Pipeline[l1, l2] * model.v_DQ[l1, t, qc, q],
            doc="Only one flow can be non-zero for quality component qc and all discretized quality q",
        )

        model.SumDiscreteFlowsIsFlowPiped = Constraint(
            model.s_NonPLP,
            model.s_T,
            model.s_QC,
            rule=lambda model, l1, l2, t, qc: sum(
                model.v_F_DiscretePiped[l1, l2, t, qc, q] for q in model.s_Q
            )
            == model.v_F_Piped[l1, l2, t],
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
            rule=lambda model, l1, l2, t, qc, q: model.v_F_DiscreteTrucked[
                l1, l2, t, qc, q
            ]
            <= (model.p_delta_Truck * model.p_max_number_of_trucks)
            * model.v_DQ[l1, t, qc, q],
            doc="Only one flow can be non-zero for quality component qc and all discretized quality q",
        )

        model.SumDiscreteFlowsIsFlowTrucked = Constraint(
            model.s_NonPLT,
            model.s_T,
            model.s_QC,
            rule=lambda model, l1, l2, t, qc: sum(
                model.v_F_DiscreteTrucked[l1, l2, t, qc, q] for q in model.s_Q
            )
            == model.v_F_Trucked[l1, l2, t],
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
            <= model.p_sigma_Disposal[k] * model.v_DQ[k, t, qc, q],
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
                    model.p_sigma_Pipeline[s, n] for n in model.s_N if model.p_SNA[s, n]
                )
                + sum(
                    model.p_sigma_Pipeline[s, p]
                    for p in model.s_CP
                    if model.p_SCA[s, p]
                )
                + sum(
                    model.p_sigma_Pipeline[s, k] for k in model.s_K if model.p_SKA[s, k]
                )
                + sum(
                    model.p_sigma_Pipeline[s, r] for r in model.s_R if model.p_SRA[s, r]
                )
                + sum(
                    model.p_sigma_Pipeline[s, o] for o in model.s_O if model.p_SOA[s, o]
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
            <= model.p_sigma_Storage[s] * model.v_DQ[s, t, qc, q],
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
            <= model.p_sigma_Treatment[r] * model.v_DQ[r, t, qc, q],
            doc="Only one quantity for treatment site r can be non-zero for quality component qc and all discretized quality q",
        )

        model.SumDiscreteFlowsIsFlowTreatment = Constraint(
            model.s_R,
            model.s_T,
            model.s_QC,
            rule=lambda model, r, t, qc: sum(
                model.v_F_DiscreteFlowTreatment[r, t, qc, q] for q in model.s_Q
            )
            == (
                sum(model.v_F_Piped[r, p, t] for p in model.s_CP if model.p_RCA[r, p])
                + sum(model.v_F_Piped[r, s, t] for s in model.s_S if model.p_RSA[r, s])
                + model.v_F_UnusedTreatedWater[r, t]
            ),
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
                    for n_tilde in model.s_N
                    if model.p_NNA[n, n_tilde]
                )
                + sum(
                    model.p_sigma_Pipeline[n, p]
                    for p in model.s_CP
                    if model.p_NCA[n, p]
                )
                + sum(
                    model.p_sigma_Pipeline[n, k] for k in model.s_K if model.p_NKA[n, k]
                )
                + sum(
                    model.p_sigma_Pipeline[n, r] for r in model.s_R if model.p_NRA[n, r]
                )
                + sum(
                    model.p_sigma_Pipeline[n, s] for s in model.s_S if model.p_NSA[n, s]
                )
                + sum(
                    model.p_sigma_Pipeline[n, o] for o in model.s_O if model.p_NOA[n, o]
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
        model.v_F_DiscreteBeneficialReuseDestination = Var(
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
            rule=lambda model, o, t, qc, q: model.v_F_DiscreteBeneficialReuseDestination[
                o, t, qc, q
            ]
            <= (
                sum(
                    model.p_sigma_Pipeline[n, o] for n in model.s_N if model.p_NOA[n, o]
                )
                + sum(
                    model.p_sigma_Pipeline[s, o] for s in model.s_S if model.p_SOA[s, o]
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
                model.v_F_DiscreteBeneficialReuseDestination[o, t, qc, q]
                for q in model.s_Q
            )
            == model.v_F_BeneficialReuseDestination[o, t],
            doc="The sum of discretized quantities at beneficial reuse destination o equals the total quantity for beneficial reuse destination o",
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
            sum(
                model.v_F_DiscretePiped[r, k, t, qc, q]
                * model.p_discrete_quality[qc, q]
                for q in model.s_Q
            )
            for r in model.s_R
            if model.p_RKA[r, k]
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
        return model.p_epsilon_Treatment[r, qc] * (
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
            model.v_F_DiscreteBeneficialReuseDestination[o, t, qc, q]
            * model.p_discrete_quality[qc, q]
            for q in model.s_Q
        )

    model.BeneficialReuseWaterQuality = Constraint(
        model.s_O,
        model.s_QC,
        model.s_T,
        rule=BeneficialReuseWaterQuality,
        doc="Beneficial reuse capacity",
    )
    # endregion

    return model
