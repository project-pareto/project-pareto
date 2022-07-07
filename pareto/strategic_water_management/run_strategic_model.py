#####################################################################################################
# PARETO was produced under the DOE Produced Water Application for Beneficial Reuse Environmental
# Impact and Treatment Optimization (PARETO), and is copyright (c) 2021 by the software owners: The
# Regents of the University of California, through Lawrence Berkeley National Laboratory, et al. All
# rights reserved.
#
# NOTICE. This Software was developed under funding from the U.S. Department of Energy and the
# U.S. Government consequently retains certain rights. As such, the U.S. Government has been granted
# for itself and others acting on its behalf a paid-up, nonexclusive, irrevocable, worldwide license
# in the Software to reproduce, distribute copies to the public, prepare derivative works, and perform
# publicly and display publicly, and to permit other to do so.
#####################################################################################################

from pareto.strategic_water_management.strategic_produced_water_optimization import (
    create_model,
    Objectives,
    solve_model,
    PipelineCost,
    PipelineCapacity,
    IncludeNodeCapacity,
)
from pareto.utilities.get_data import get_data
from pareto.utilities.results import generate_report, PrintValues, OutputUnits
from importlib import resources

# This emulates what the pyomo command-line tools does
# Tabs in the input Excel spreadsheet
set_list = [
    "ProductionPads",
    "ProductionTanks",
    "CompletionsPads",
    "SWDSites",
    "FreshwaterSources",
    "StorageSites",
    "TreatmentSites",
    "ReuseOptions",
    "NetworkNodes",
    "PipelineDiameters",
    "StorageCapacities",
    "InjectionCapacities",
    "TreatmentCapacities",
]
parameter_list = [
    "Units",
    "PNA",
    "CNA",
    "CCA",
    "NNA",
    "NCA",
    "NKA",
    "NRA",
    "NSA",
    "FCA",
    "RCA",
    "RNA",
    "SNA",
    "PCT",
    "PKT",
    "FCT",
    "CST",
    "CCT",
    "CKT",
    "TruckingTime",
    "CompletionsDemand",
    "PadRates",
    "FlowbackRates",
    "NodeCapacities",
    "InitialPipelineCapacity",
    "InitialDisposalCapacity",
    "InitialTreatmentCapacity",
    "FreshwaterSourcingAvailability",
    "PadOffloadingCapacity",
    "CompletionsPadStorage",
    "DisposalOperationalCost",
    "TreatmentOperationalCost",
    "ReuseOperationalCost",
    "PipelineOperationalCost",
    "FreshSourcingCost",
    "TruckingHourlyCost",
    "PipelineDiameterValues",
    "DisposalCapacityIncrements",
    "InitialStorageCapacity",
    "StorageCapacityIncrements",
    "TreatmentCapacityIncrements",
    "TreatmentEfficiency",
    "DisposalExpansionCost",
    "StorageExpansionCost",
    "TreatmentExpansionCost",
    "PipelineCapexDistanceBased",
    "PipelineCapexCapacityBased",
    "PipelineCapacityIncrements",
    "PipelineExpansionDistance",
    "Hydraulics",
    "Economics",
    "PadWaterQuality",
    "StorageInitialWaterQuality",
    "PadStorageInitialWaterQuality",
]

# user needs to provide the path to the case study data file
# for example: 'C:\\user\\Documents\\myfile.xlsx'
# note the double backslashes '\\' in that path reference
with resources.path(
    "pareto.case_studies",
    # "input_data_generic_strategic_case_study_LAYFLAT_FULL.xlsx",
    "small_strategic_case_study.xlsx",
) as fpath:
    [df_sets, df_parameters] = get_data(fpath, set_list, parameter_list)

# create mathematical model
"""Valid values of config arguments for the default parameter in the create_model() call
 objective: [Objectives.cost, Objectives.reuse]
 pipeline_cost: [PipelineCost.distance_based, PipelineCost.capacity_based]
 pipeline_capacity: [PipelineCapacity.input, PipelineCapacity.calculated]
 node_capacity: [IncludeNodeCapacity.True, IncludeNodeCapacity.False]"""
strategic_model = create_model(
    df_sets,
    df_parameters,
    default={
        "objective": Objectives.cost,
        "pipeline_cost": PipelineCost.distance_based,
        "pipeline_capacity": PipelineCapacity.input,
        "node_capacity": IncludeNodeCapacity.true,
    },
)

options = {
    "deactivate_slacks": True,
    "scale_model": True,
    "scaling_factor": 1000,
    "running_time": 60,
    "gap": 0,
    "water_quality": False,
}
solve_model(model=strategic_model, options=options)

# Generate report with results in Excel
print("\nConverting to Output Units and Displaying Solution\n" + "-" * 60)
"""Valid values of parameters in the generate_report() call
 is_print: [PrintValues.detailed, PrintValues.nominal, PrintValues.essential]
 output_units: [OutputUnits.user_units, OutputUnits.unscaled_model_units]
 """
[model, results_dict] = generate_report(
    strategic_model,
    is_print=[PrintValues.essential],
    output_units=OutputUnits.unscaled_model_units,
    fname="strategic_optimization_results.xlsx",
)

# This shows how to read data from PARETO reports
set_list = []
parameter_list = ["v_F_Trucked", "v_C_Trucked"]
fname = "strategic_optimization_results.xlsx"
[sets_reports, parameters_report] = get_data(fname, set_list, parameter_list)

strategic_model.v_F_UnusedTreatedWater.display()
strategic_model.vb_y_Treatment.display()


# ----------------------------------------------------------------------
## adding treatment technologies model ##
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
    Any,
    units as pyunits,
    Block,
    Suffix,
    TransformationFactory,
    value,
)

model = strategic_model

model.s_DT = Set(initialize=["DTA", "DTB"], doc="Treatment Desalination Technologies")

model.p_delta_DTreatment = Param(
    model.s_DT,
    default=pyunits.convert_value(
        10,
        from_units=pyunits.oil_bbl / pyunits.week,
        to_units=model.model_units["volume_time"],
    ),
    initialize={"DTA": 50, "DTB": 90},
    units=model.model_units["volume_time"],
    doc="Treatment capacity installation/expansion increments [volume/time]",
)

model.vb_yw_Treatment = Var(
    model.s_R,
    model.s_DT,
    within=Binary,
    initialize=0,
    doc="New or additional treatment capacity installed at treatment site with specific treatment capacity",
)

model.v_TW_Capacity = Var(
    model.s_R,
    within=NonNegativeReals,
    units=model.model_units["volume_time"],
    doc="Treatment capacity at a treatment site [volume/time]",
)


def TreatmentCapacityExpansionRule2(model, r):
    return model.v_TW_Capacity[r] == model.p_sigma_Treatment[r] + sum(
        model.p_delta_DTreatment[j] * model.vb_yw_Treatment[r, j] for j in model.s_DT
    )


model.TreatmentCapacityExpansion2 = Constraint(
    model.s_R,
    rule=TreatmentCapacityExpansionRule2,
    doc="Treatment capacity construction/expansion",
)

# model.TreatmentCapacityExpansion.pprint()


def TreatmentCapacityRule2(model, r, t):
    return model.v_F_UnusedTreatedWater[r, t] <= model.v_TW_Capacity[r]

    # sum(model.v_F_Piped[n, r, t] for n in model.s_N if model.p_NRA[n, r])
    # + sum(model.v_F_Piped[s, r, t] for s in model.s_S if model.p_SRA[s, r])
    # + sum(model.v_F_Trucked[p, r, t] for p in model.s_PP if model.p_PRT[p, r])
    # + sum(model.v_F_Trucked[p, r, t] for p in model.s_CP if model.p_CRT[p, r])

    # return process_constraint(constraint)


model.TreatmentCapacity2 = Constraint(
    model.s_R, model.s_T, rule=TreatmentCapacityRule2, doc="Treatment capacity"
)

# model.TreatmentCapacity.pprint()

# def TreatmentBalanceRule(model, r, t):
#     constraint = (
#         model.p_epsilon_Treatment[r, model.p_W_TreatmentComponent[r]]
#         * (
#             sum(model.v_F_Piped[n, r, t] for n in model.s_N if model.p_NRA[n, r])
#             + sum(model.v_F_Piped[s, r, t] for s in model.s_S if model.p_SRA[s, r])
#             + sum(
#                 model.v_F_Trucked[p, r, t] for p in model.s_PP if model.p_PRT[p, r]
#             )
#             + sum(
#                 model.v_F_Trucked[p, r, t] for p in model.s_CP if model.p_CRT[p, r]
#             )
#         )
#         == sum(model.v_F_Piped[r, p, t] for p in model.s_CP if model.p_RCA[r, p])
#         + sum(model.v_F_Piped[r, s, t] for s in model.s_S if model.p_RSA[r, s])
#         + model.v_F_UnusedTreatedWater[r, t]
#     )
#     return process_constraint(constraint)

# model.TreatmentBalance = Constraint(
#     model.s_R, model.s_T, rule=TreatmentBalanceRule, doc="Treatment balance"
# )


def LogicConstraintTreatmentRule2(model, r):
    return sum(model.vb_yw_Treatment[r, j] for j in model.s_DT) == 1

    # return process_constraint(constraint)


model.LogicConstraintTreatment2 = Constraint(
    model.s_R, rule=LogicConstraintTreatmentRule2, doc="Logic constraint treatment"
)


def TreatmentExpansionCapExRule2(model):
    return model.v_C_TreatmentCapEx == sum(
        sum(
            model.vb_y_Treatment[r, j]
            * model.p_kappa_Treatment[r, j]
            * model.p_delta_Treatment[j]
            for r in model.s_R
        )
        for j in model.s_J
    ) + sum(
        sum(
            model.vb_yw_Treatment[r, j] * 1.4285 * model.p_delta_DTreatment[j]
            for r in model.s_R
        )
        for j in model.s_DT
    )
    # return process_constraint(constraint)


model.TreatmentExpansionCapEx = Constraint(
    rule=TreatmentExpansionCapExRule2,
    doc="Treatment construction or capacity expansion cost",
)
# solve_model(model=strategic_model, options=options)
from pareto.utilities.solvers import get_solver, set_timeout

solver = get_solver("gurobi_direct", "gurobi", "cbc")
solver.solve(strategic_model, tee=True)

strategic_model.v_F_UnusedTreatedWater.display()
strategic_model.vb_y_Treatment.display()
strategic_model.vb_yw_Treatment.display()
