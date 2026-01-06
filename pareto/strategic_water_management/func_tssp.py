import pyomo.environ as pyo
from pareto.strategic_water_management.strategic_produced_water_optimization import (
    WaterQuality,
    create_model,
    Objectives,
    solve_model,
    PipelineCost,
    PipelineCapacity,
    Hydraulics,
    RemovalEfficiencyMethod,
    InfrastructureTiming,
    DesalinationModel,
    SubsurfaceRisk,
)
from pareto.utilities.get_data import get_data
from pareto.utilities.results import (
    generate_report,
    PrintValues,
    OutputUnits,
    is_feasible,
    nostdout,
)
from pareto.utilities.visualize import plot_network
from importlib import resources
from pathlib import Path
from pyomo.core.base.reference import Reference

# ---- Load Data ---- #
with resources.path(
    "pareto.case_studies",
    "strategic_discap_sc1.xlsx",
) as fpath:
    # When set_list and parameter_list are not specified to get_data(), all tabs with valid PARETO input names are read
    [df_sets_sc1, df_parameters_sc1] = get_data(fpath, model_type="strategic")

with resources.path(
    "pareto.case_studies",
    "strategic_discap_sc2.xlsx",
) as fpath:
    # When set_list and parameter_list are not specified to get_data(), all tabs with valid PARETO input names are read
    [df_sets_sc2, df_parameters_sc2] = get_data(fpath, model_type="strategic")

with resources.path(
    "pareto.case_studies",
    "strategic_discap_sc3.xlsx",
) as fpath:
    # When set_list and parameter_list are not specified to get_data(), all tabs with valid PARETO input names are read
    [df_sets_sc3, df_parameters_sc3] = get_data(fpath, model_type="strategic")


# fpath1 = Path(
#     "C:/Users/Soumya/OneDrive - KeyLogic/Documents/project-pareto/pareto/case_studies_tssp/DisposalCap/strategic_discap_sc1.xlsx"
# )
# [df_sets_dtm, df_parameters_dtm] = get_data(fpath1, model_type="strategic")

# fpath2 = Path(
#     "C:/Users/Soumya/OneDrive - KeyLogic/Documents/project-pareto/pareto/case_studies_tssp/DisposalCap/strategic_discap_sc2.xlsx"
# )
# [df_sets_sc1, df_parameters_sc1] = get_data(fpath2, model_type="strategic")

# fpath3 = Path(
#     "C:/Users/Soumya/OneDrive - KeyLogic/Documents/project-pareto/pareto/case_studies_tssp/DisposalCap/strategic_discap_sc3.xlsx"
# )
# [df_sets_sc2, df_parameters_sc2] = get_data(fpath3, model_type="strategic")


def build_stochastic_model():
    sm = pyo.ConcreteModel()
    sm.scenario1 = create_model(
        df_sets_sc1,
        df_parameters_sc1,
        default={
            "objective": Objectives.cost,
            "pipeline_cost": PipelineCost.distance_based,
            "pipeline_capacity": PipelineCapacity.input,
            "hydraulics": Hydraulics.false,
            "desalination_model": DesalinationModel.false,
            "node_capacity": True,
            "water_quality": WaterQuality.false,
            "removal_efficiency_method": RemovalEfficiencyMethod.concentration_based,
            "infrastructure_timing": InfrastructureTiming.true,
            "subsurface_risk": SubsurfaceRisk.false,
        },
    )
    sm.scenario2 = create_model(
        df_sets_sc2,
        df_parameters_sc2,
        default={
            "objective": Objectives.cost,
            "pipeline_cost": PipelineCost.distance_based,
            "pipeline_capacity": PipelineCapacity.input,
            "hydraulics": Hydraulics.false,
            "desalination_model": DesalinationModel.false,
            "node_capacity": True,
            "water_quality": WaterQuality.false,
            "removal_efficiency_method": RemovalEfficiencyMethod.concentration_based,
            "infrastructure_timing": InfrastructureTiming.true,
            "subsurface_risk": SubsurfaceRisk.false,
        },
    )
    sm.scenario3 = create_model(
        df_sets_sc3,
        df_parameters_sc3,
        default={
            "objective": Objectives.cost,
            "pipeline_cost": PipelineCost.distance_based,
            "pipeline_capacity": PipelineCapacity.input,
            "hydraulics": Hydraulics.false,
            "desalination_model": DesalinationModel.false,
            "node_capacity": True,
            "water_quality": WaterQuality.false,
            "removal_efficiency_method": RemovalEfficiencyMethod.concentration_based,
            "infrastructure_timing": InfrastructureTiming.true,
            "subsurface_risk": SubsurfaceRisk.false,
        },
    )
    # First stage variables
    sm.v_T_Capacity = pyo.Var(
        sm.scenario1.s_R,
        within=pyo.NonNegativeReals,
        units=sm.scenario1.model_units["volume_time"],
        doc="Treatment capacity at a treatment site [volume/time]",
    )

    def non_anticipativity_con11_rule(sm, r):
        return sm.v_T_Capacity[r] == sm.scenario1.v_T_Capacity[r]

    sm.non_anticipativity_con11 = pyo.Constraint(
        sm.scenario1.s_R, rule=non_anticipativity_con11_rule
    )

    def non_anticipativity_con12_rule(sm, r):
        return sm.v_T_Capacity[r] == sm.scenario1.v_T_Capacity[r]

    sm.non_anticipativity_con12 = pyo.Constraint(
        sm.scenario1.s_R, rule=non_anticipativity_con12_rule
    )

    def non_anticipativity_con13_rule(sm, r):
        return sm.v_T_Capacity[r] == sm.scenario1.v_T_Capacity[r]

    sm.non_anticipativity_con13 = pyo.Constraint(
        sm.scenario1.s_R, rule=non_anticipativity_con13_rule
    )

    sm.vb_y_Pipeline = pyo.Var(
        sm.scenario1.s_L,
        sm.scenario1.s_L,
        sm.scenario1.s_D,
        within=pyo.Binary,
        initialize=0,
        doc="New pipeline installed between one location and another location with specific diameter",
    )

    def non_anticipativity_con21_rule(sm, l, l_tilde, d):
        return (
            sm.vb_y_Pipeline[l, l_tilde, d] == sm.scenario1.vb_y_Pipeline[l, l_tilde, d]
        )

    sm.non_anticipativity_con21 = pyo.Constraint(
        sm.scenario1.s_L,
        sm.scenario1.s_L,
        sm.scenario1.s_D,
        rule=non_anticipativity_con21_rule,
    )

    def non_anticipativity_con22_rule(sm, l, l_tilde, d):
        return (
            sm.vb_y_Pipeline[l, l_tilde, d] == sm.scenario2.vb_y_Pipeline[l, l_tilde, d]
        )

    sm.non_anticipativity_con22 = pyo.Constraint(
        sm.scenario1.s_L,
        sm.scenario1.s_L,
        sm.scenario1.s_D,
        rule=non_anticipativity_con22_rule,
    )

    def non_anticipativity_con23_rule(sm, l, l_tilde, d):
        return (
            sm.vb_y_Pipeline[l, l_tilde, d] == sm.scenario3.vb_y_Pipeline[l, l_tilde, d]
        )

    sm.non_anticipativity_con23 = pyo.Constraint(
        sm.scenario1.s_L,
        sm.scenario1.s_L,
        sm.scenario1.s_D,
        rule=non_anticipativity_con23_rule,
    )

    sm.vb_y_Storage = pyo.Var(
        sm.scenario1.s_S,
        sm.scenario1.s_C,
        within=pyo.Binary,
        initialize=0,
        doc="New or additional storage capacity installed at storage site with specific storage capacity",
    )

    def non_anticipativity_con31_rule(sm, s, c):
        return sm.vb_y_Storage[s, c] == sm.scenario1.vb_y_Storage[s, c]

    sm.non_anticipativity_con31 = pyo.Constraint(
        sm.scenario1.s_S, sm.scenario1.s_C, rule=non_anticipativity_con31_rule
    )

    def non_anticipativity_con32_rule(sm, s, c):
        return sm.vb_y_Storage[s, c] == sm.scenario2.vb_y_Storage[s, c]

    sm.non_anticipativity_con32 = pyo.Constraint(
        sm.scenario1.s_S, sm.scenario1.s_C, rule=non_anticipativity_con32_rule
    )

    def non_anticipativity_con33_rule(sm, s, c):
        return sm.vb_y_Storage[s, c] == sm.scenario3.vb_y_Storage[s, c]

    sm.non_anticipativity_con33 = pyo.Constraint(
        sm.scenario1.s_S, sm.scenario1.s_C, rule=non_anticipativity_con33_rule
    )

    sm.vb_y_Treatment = pyo.Var(
        sm.scenario1.s_R,
        sm.scenario1.s_WT,
        sm.scenario1.s_J,
        within=pyo.Binary,
        initialize=0,
        doc="New or additional treatment capacity installed at treatment site with specific treatment capacity and treatment technology",
    )

    def non_anticipativity_con41_rule(sm, r, wt, j):
        return sm.vb_y_Treatment[r, wt, j] == sm.scenario1.vb_y_Treatment[r, wt, j]

    sm.non_anticipativity_con41 = pyo.Constraint(
        sm.scenario1.s_R,
        sm.scenario1.s_WT,
        sm.scenario1.s_J,
        rule=non_anticipativity_con41_rule,
    )

    def non_anticipativity_con42_rule(sm, r, wt, j):
        return sm.vb_y_Treatment[r, wt, j] == sm.scenario2.vb_y_Treatment[r, wt, j]

    sm.non_anticipativity_con42 = pyo.Constraint(
        sm.scenario1.s_R,
        sm.scenario1.s_WT,
        sm.scenario1.s_J,
        rule=non_anticipativity_con42_rule,
    )

    def non_anticipativity_con43_rule(sm, r, wt, j):
        return sm.vb_y_Treatment[r, wt, j] == sm.scenario3.vb_y_Treatment[r, wt, j]

    sm.non_anticipativity_con43 = pyo.Constraint(
        sm.scenario1.s_R,
        sm.scenario1.s_WT,
        sm.scenario1.s_J,
        rule=non_anticipativity_con43_rule,
    )

    sm.vb_y_Disposal = pyo.Var(
        sm.scenario1.s_K,
        sm.scenario1.s_I,
        within=pyo.Binary,
        initialize=0,
        doc="New or additional disposal capacity installed at disposal site with specific injection capacity",
    )

    def non_anticipativity_con51_rule(sm, k, i):
        return sm.vb_y_Disposal[k, i] == sm.scenario1.vb_y_Disposal[k, i]

    sm.non_anticipativity_con51 = pyo.Constraint(
        sm.scenario1.s_K, sm.scenario1.s_I, rule=non_anticipativity_con51_rule
    )

    def non_anticipativity_con52_rule(sm, k, i):
        return sm.vb_y_Disposal[k, i] == sm.scenario2.vb_y_Disposal[k, i]

    sm.non_anticipativity_con52 = pyo.Constraint(
        sm.scenario1.s_K, sm.scenario1.s_I, rule=non_anticipativity_con52_rule
    )

    def non_anticipativity_con53_rule(sm, k, i):
        return sm.vb_y_Disposal[k, i] == sm.scenario3.vb_y_Disposal[k, i]

    sm.non_anticipativity_con53 = pyo.Constraint(
        sm.scenario1.s_K, sm.scenario1.s_I, rule=non_anticipativity_con53_rule
    )

    sm.vb_y_BeneficialReuse = pyo.Var(
        sm.scenario1.s_O,
        sm.scenario1.s_T,
        within=pyo.Binary,
        initialize=0,
        doc="Beneficial reuse option selection",
    )

    def non_anticipativity_con61_rule(sm, o, t):
        return sm.vb_y_BeneficialReuse[o, t] == sm.scenario1.vb_y_BeneficialReuse[o, t]

    sm.non_anticipativity_con61 = pyo.Constraint(
        sm.scenario1.s_O, sm.scenario1.s_T, rule=non_anticipativity_con61_rule
    )

    def non_anticipativity_con62_rule(sm, o, t):
        return sm.vb_y_BeneficialReuse[o, t] == sm.scenario2.vb_y_BeneficialReuse[o, t]

    sm.non_anticipativity_con62 = pyo.Constraint(
        sm.scenario1.s_O, sm.scenario1.s_T, rule=non_anticipativity_con62_rule
    )

    def non_anticipativity_con63_rule(sm, o, t):
        return sm.vb_y_BeneficialReuse[o, t] == sm.scenario3.vb_y_BeneficialReuse[o, t]

    sm.non_anticipativity_con63 = pyo.Constraint(
        sm.scenario1.s_O, sm.scenario1.s_T, rule=non_anticipativity_con63_rule
    )

    sm.scenario1.objective_Cost.deactivate()
    sm.scenario2.objective_Cost.deactivate()
    sm.scenario3.objective_Cost.deactivate()

    sm.obj = pyo.Objective(
        expr=(1 / 3) * sm.scenario1.objective_Cost.expr
        + (1 / 3) * sm.scenario2.objective_Cost.expr
        + (1 / 3) * sm.scenario3.objective_Cost.expr
    )

    return sm


stochastic_model = build_stochastic_model()

options = {
    "deactivate_slacks": True,
    "scale_model": False,
    "scaling_factor": 1000,
    "running_time": 10000,
    "gap": 0.70,
}
# --- Handle slack variables for stochastic model ---
if "scenario1" in dir(stochastic_model):
    for scenario_name, scenario_block in stochastic_model.component_map(
        pyo.Block, active=True
    ).items():
        for vname in [
            "v_C_Slack",
            "v_S_FracDemand",
            "v_S_Production",
            "v_S_Flowback",
            "v_S_PipelineCapacity",
            "v_S_StorageCapacity",
            "v_S_DisposalCapacity",
            "v_S_TreatmentCapacity",
            "v_S_BeneficialReuseCapacity",
        ]:
            if hasattr(scenario_block, vname):
                getattr(scenario_block, vname).fix(0)

# Also add dummy placeholders at top-level to prevent PARETO errors
for vname in [
    "v_C_Slack",
    "v_S_FracDemand",
    "v_S_Production",
    "v_S_Flowback",
    "v_S_PipelineCapacity",
    "v_S_StorageCapacity",
    "v_S_DisposalCapacity",
    "v_S_TreatmentCapacity",
    "v_S_BeneficialReuseCapacity",
]:
    if not hasattr(stochastic_model, vname):
        setattr(stochastic_model, vname, pyo.Var(initialize=0))
        getattr(stochastic_model, vname).fix(0)

# 1️⃣ Subsurface risk flag
if not hasattr(stochastic_model, "do_subsurface_risk_calcs"):
    stochastic_model.do_subsurface_risk_calcs = False

# 2️⃣ Dummy subsurface block
if not hasattr(stochastic_model, "subsurface"):
    stochastic_model.subsurface = pyo.Block()

sets_to_copy = [
    "s_R",
    "s_L",
    "s_D",
    "s_S",
    "s_C",
    "s_WT",
    "s_J",
    "s_K",
    "s_I",
    "s_O",
    "s_T",
]

for sname in sets_to_copy:
    if not hasattr(stochastic_model, sname):
        if hasattr(stochastic_model.scenario1, sname):
            setattr(
                stochastic_model,
                sname,
                pyo.Set(initialize=list(getattr(stochastic_model.scenario1, sname))),
            )
        else:
            setattr(stochastic_model, sname, pyo.Set(initialize=[]))

# 4️⃣ Optional flag used by solve_model()
if "only_subsurface_block" not in locals():
    only_subsurface_block = False


results = solve_model(model=stochastic_model, options=options)

with nostdout():
    feasibility_status = is_feasible(stochastic_model)

if not feasibility_status:
    print("\nModel results are not feasible and should not be trusted\n" + "-" * 60)
else:
    print("\nModel results validated and found to pass feasibility tests\n" + "-" * 60)


print("\nGenerating scenario-wise reports...\n" + "-" * 60)

scenarios = ["scenario1", "scenario2", "scenario3"]

for scen in scenarios:
    scenario_block = getattr(stochastic_model, scen)
    # Copy the solved first-stage decisions into the scenario block for reporting
    for vname in [
        "v_T_Capacity",
        "vb_y_Pipeline",
        "vb_y_Storage",
        "vb_y_Treatment",
        "vb_y_Disposal",
        "vb_y_BeneficialReuse",
    ]:
        if hasattr(stochastic_model, vname) and hasattr(scenario_block, vname):
            var_stoch = getattr(stochastic_model, vname)
            var_scen = getattr(scenario_block, vname)
            for idx in var_scen.index_set():
                if idx in var_stoch:
                    var_scen[idx].set_value(pyo.value(var_stoch[idx]))
    # Generate individual Excel report
    [_, results_dict] = generate_report(
        scenario_block,
        results_obj=results,
        is_print=PrintValues.essential,
        output_units=OutputUnits.user_units,
        fname=f"strategic_optimization_results_{scen}.xlsx",
    )
