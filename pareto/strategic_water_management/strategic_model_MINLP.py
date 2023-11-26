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

<<<<<<< HEAD
from pareto.strategic_water_management.strategic_produced_water_optimization_with_surrogate_elmira_re_revised import (
    # from pareto.strategic_water_management.strategic_produced_water_optimization_minlp import (
=======
from pareto.strategic_water_management.strategic_produced_water_optimization_minlp import (
>>>>>>> parent of 3e69472 (Revert to this if nothing else works)
    WaterQuality,
    create_model,
    Objectives,
    solve_model,
    PipelineCost,
    PipelineCapacity,
    Hydraulics,
    RemovalEfficiencyMethod,
)

from pareto.utilities.get_data import get_data
from pareto.utilities.results_minlp import (
    generate_report,
    PrintValues,
    OutputUnits,
    is_feasible,
    nostdout,
)
from importlib import resources
from pyomo.environ import Constraint, value, units

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from ipywidgets import FloatText, Button, Layout, GridspecLayout, ToggleButtons
from IPython.display import display

from os import remove
import os

# from tabulate import tabulate

# Each entry in set_list corresponds to a tab in the Excel input file that
# defines an index set.
set_list = [
    "ProductionPads", "CompletionsPads", "SWDSites", "FreshwaterSources", "StorageSites",
    "TreatmentSites", "ReuseOptions", "NetworkNodes", "PipelineDiameters", "StorageCapacities",
    "InjectionCapacities", "TreatmentCapacities", "TreatmentTechnologies",
]
# Each entry in parameter_list also corresponds to a tab in the Excel input
# file, but these tabs have parameter data.
parameter_list = [
    "Units", "PNA", "CNA", "CCA", "NNA", "NCA", "NKA", "NRA", "NSA", "FCA", "RCA", "RNA",
    "RSA", "SCA", "SNA", "PCT", "PKT", "FCT", "CST", "CCT", "CKT", "CompletionsPadOutsideSystem",
    "DesalinationTechnologies", "DesalinationSites", "TruckingTime", "CompletionsDemand",
    "PadRates", "FlowbackRates", "NodeCapacities", "InitialPipelineCapacity",
    "InitialDisposalCapacity", "InitialTreatmentCapacity", "FreshwaterSourcingAvailability",
    "PadOffloadingCapacity", "CompletionsPadStorage", "DisposalOperationalCost",
    "TreatmentOperationalCost", "ReuseOperationalCost", "PipelineOperationalCost",
    "FreshSourcingCost", "TruckingHourlyCost", "PipelineDiameterValues",
    "DisposalCapacityIncrements", "InitialStorageCapacity", "StorageCapacityIncrements",
    "TreatmentCapacityIncrements", "TreatmentEfficiency", "RemovalEfficiency",
    "DisposalExpansionCost", "StorageExpansionCost", "TreatmentExpansionCost",
    "PipelineCapexDistanceBased", "PipelineCapexCapacityBased", "PipelineCapacityIncrements",
    "PipelineExpansionDistance", "Hydraulics", "Economics", "PadWaterQuality",
    "StorageInitialWaterQuality", "PadStorageInitialWaterQuality", "DisposalOperatingCapacity",
]

# Load data from Excel input file into Python
with resources.path(
    "pareto.case_studies",
    # "strategic_treatment_demo_modified_only_MVC.xlsx",
    "strategic_treatment_demo_modified.xlsx",
) as fpath:
    [df_sets, df_parameters] = get_data(fpath, set_list, parameter_list)

# Create Pyomo optimization model representing the produced water network
strategic_model = create_model(
    df_sets,
    df_parameters,
    default={
        "objective": Objectives.cost,
        "pipeline_cost": PipelineCost.distance_based,
        "pipeline_capacity": PipelineCapacity.input,
        "node_capacity": True,
        "water_quality": WaterQuality.post_process,
    },
)

# Solve Pyomo model with specified options
options = {
    # "solver": "cbc",  # If you don't have gurobi, uncooment this line to use free solver cbc
    "deactivate_slacks": True,
    "scale_model": False,
    "scaling_factor": 1000000,
    "running_time": 3000,
    "gap": 0,
    "gurobi_numeric_focus": 1,
}
results_obj = solve_model(model=strategic_model, options=options)
# filename = os.path.join(os.path.dirname(__file__), 'model.lp')
# strategic_model.write(filename, io_options={'symbolic_solver_labels': True})
# Check feasibility of the solved model
def check_feasibility(model):
    with nostdout():
        feasibility_status = is_feasible(model)
    if not feasibility_status:
        print("Model results are not feasible and should not be trusted")
    else:
        print("Model results validated and found to pass feasibility tests")


<<<<<<< HEAD
# check_feasibility(strategic_model)

# [model, results_dict] = generate_report(
#     strategic_model,
#     # is_print=[PrintValues.essential],
#     output_units=OutputUnits.user_units,
#     fname="MINLP.xlsx",
# )

# # This shows how to read data from PARETO reports
# set_list = []
# parameter_list = ["v_F_Trucked", "v_C_Trucked"]
# fname = "MINLP.xlsx"
# [sets_reports, parameters_report] = get_data(fname, set_list, parameter_list)
# # # Function to extract R01 buildout results
# def get_desal_results(results_dict):
#     desal_sites = {}
#     for datapt in results_dict["vb_y_Treatment_dict"][:]:
#         site, technology, capacity, built = datapt
#         if (
#             technology == "FF" or technology == "MVC" or technology == "HDH"
#         ) and built == 1:
#             desal_sites[f"{site}"] = {}
#             desal_sites[f"{site}"]["technology"] = technology
#             desal_sites[f"{site}"]["capacity"] = capacity

#     return desal_sites


# # Extract R01 buildout results for default solved model
# desal_sites = get_desal_results(results_dict)
# # print('For this case, PARETO recommends installing a desalination plant in R01 location')

# for i in desal_sites:
#     print(f"Site: {i}")
#     print(f"Technology: {desal_sites[i]['technology']}")
#     print(f"Capacity: {desal_sites[i]['capacity']}")
#     print("---------------------------------")
# # print(f"Site: {desal_sites['site']}")
# # print(f"Technology: {desal_sites['technology']}")
# # print(f"Capacity: {desal_sites['capacity']}")
# print(f"Objective function value: {value(strategic_model.v_Z)}")
# print("--------------------")

# # Check what capacity J1 corresponds to (in bbl/day)
# for i in desal_sites:
#     print(
#         f"Desalination plant {i} capacity bbl/day = {df_parameters['TreatmentCapacityIncrements'][(desal_sites[i]['technology'], desal_sites[i]['capacity'])]}"
#     )
from pyomo.environ import Var, Binary


def free_variables(model, exception_list, time_period=None):
    for var in model.component_objects(Var):
        if var.name in exception_list:
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
                    # index_var.free()
                    # index_var.unfix()
                    pass
                else:
                    index_var.unfix()
                    index_var.setlb(0)
                    index_var.setub(None)


def deactivate_slacks(model):
    model.v_C_Slack.fix(0)
    model.v_S_FracDemand.fix(0)
    model.v_S_Production.fix(0)
    model.v_S_Flowback.fix(0)
    model.v_S_PipelineCapacity.fix(0)
    model.v_S_StorageCapacity.fix(0)
    model.v_S_DisposalCapacity.fix(0)
    model.v_S_TreatmentCapacity.fix(0)
    # model.v_S_ReuseCapacity.fix(0)


# Step 2.1: unfix variables (MILP model)
discrete_variables_names = {"v_X"}  # "v_Q", "v_X", "v_Z", "v_ObjectiveWithQuality"}
free_variables(strategic_model, discrete_variables_names)
deactivate_slacks(strategic_model)
strategic_model.quality.objective.deactivate()
strategic_model.CostObjectiveFunction.deactivate()

from pyomo.environ import Constraint, Objective, minimize, SolverFactory, Param

strategic_model.penalty = Param(initialize=1, mutable=True)
from pareto.utilities.solvers import get_solver, set_timeout


def CostObjectiveFunctionRule2(model):
    return model.v_Z == (
        model.v_C_TotalSourced
        + model.v_C_TotalDisposal
        + model.v_C_TotalTreatment
        + model.v_C_TotalReuse
        + model.v_C_TotalPiping
        + model.v_C_TotalStorage
        + model.v_C_TotalTrucking
        + model.quality.v_C_TotalTreatment_surrogate
        + model.quality.v_C_TreatmentCapex_surrogate
        + model.p_alpha_AnnualizationRate
        * (
            model.v_C_DisposalCapEx
            + model.v_C_StorageCapEx
            + model.v_C_TreatmentCapEx
            + model.v_C_PipelineCapEx
        )
        + model.v_C_Slack
        - model.v_R_TotalStorage
        + model.penalty
        * sum(
            model.quality.v_Q[sites, w, t]
            for sites in model.s_R
            for w in model.s_QC
            for t in model.s_T
        )
    )


strategic_model.ObjectiveFunction = Constraint(
    rule=CostObjectiveFunctionRule2, doc="MINLP objective function"
)

wall_time = []
time = []
solver_status = []
objs = []
penalty_value = []

# You should change the below array to desired penalty,
# this was done just to get a feel for the magnitude of
# the penalty term


minlp_solver_source = "gurobi"
if minlp_solver_source == "gams":
    mathoptsolver = "dicopt"
    solver_options = {
        "tol": 1e-3,
        "max_iter": 1000,
        "constr_viol_tol": 0.009,
        "acceptable_constr_viol_tol": 0.01,
        "acceptable_tol": 1e-6,
        "mu_strategy": "adaptive",
        "mu_init": 1e-10,
        "mu_max": 1e-1,
        "print_user_options": "yes",
        "warm_start_init_point": "yes",
        "warm_start_mult_bound_push": 1e-60,
        "warm_start_bound_push": 1e-60,
        #   'linear_solver': 'ma27',
        #   'ma57_pivot_order': 4
    }
    import os
=======
[model, results_dict] = generate_report(
    strategic_model,
    is_print=[PrintValues.essential],
    output_units=OutputUnits.user_units,
    fname="strategic_optimization_MINLP_baron.xlsx",
)

# This shows how to read data from PARETO reports
set_list = []
parameter_list = ["v_F_Trucked", "v_C_Trucked"]
fname = "strategic_optimization_MINLP_baron.xlsx"
[sets_reports, parameters_report] = get_data(fname, set_list, parameter_list)
# # Function to extract R01 buildout results
# def get_desal_results(results_dict):
#     desal_sites={}
#     for datapt in results_dict['vb_y_Treatment_dict'][:]:
#         site, technology, capacity, built = datapt
#         if (technology == 'FF' or  technology == 'MVC' or technology == 'HDH') and built == 1:
#             desal_sites[f'{site}'] = {}
#             desal_sites[f'{site}']['technology'] = technology
#             desal_sites[f'{site}']['capacity'] = capacity
    
#     return desal_sites

# # Extract R01 buildout results for default solved model
# desal_sites = get_desal_results(results_dict)
# # print('For this case, PARETO recommends installing a desalination plant in R01 location')

# for i in desal_sites:
#     print(f'Site: {i}')
#     print(f"Technology: {desal_sites[i]['technology']}")
#     print(f"Capacity: {desal_sites[i]['capacity']}")
#     print('---------------------------------')
# # print(f"Site: {desal_sites['site']}")
# # print(f"Technology: {desal_sites['technology']}")
# # print(f"Capacity: {desal_sites['capacity']}")
# print(f"Objective function value: {value(strategic_model.v_Z)}")
# print('--------------------')

# # Check what capacity J1 corresponds to (in bbl/day) 
# for i in desal_sites:
#     print(f"Desalination plant {i} capacity bbl/day = {df_parameters['TreatmentCapacityIncrements'][(desal_sites[i]['technology'], desal_sites[i]['capacity'])]}")
# from pyomo.environ import Var, Binary
# def free_variables(model, exception_list, time_period=None):
#     for var in model.component_objects(Var):
#         if var.name in exception_list:
#             continue
#         else:
#             for index in var:
#                 is_in_time_period = True
#                 if index is not None and time_period is not None:
#                     for i in index:
#                         if i in model.s_T and i not in time_period:
#                             is_in_time_period = False
#                             break
#                 if not is_in_time_period:
#                     continue
#                 index_var = var if index is None else var[index]
#                 # unfix binary variables and unbound the continuous variables
#                 if index_var.domain is Binary:
#                     # index_var.free()
#                     # index_var.unfix()
#                     pass
#                 else:
#                     index_var.unfix()
#                     index_var.setlb(0)
#                     index_var.setub(None)


# def deactivate_slacks(model):
#     model.v_C_Slack.fix(0)
#     model.v_S_FracDemand.fix(0)
#     model.v_S_Production.fix(0)
#     model.v_S_Flowback.fix(0)
#     model.v_S_PipelineCapacity.fix(0)
#     model.v_S_StorageCapacity.fix(0)
#     model.v_S_DisposalCapacity.fix(0)
#     model.v_S_TreatmentCapacity.fix(0)
#     model.v_S_ReuseCapacity.fix(0)
                    
# # Step 2.1: unfix variables (MILP model)
# discrete_variables_names = {"v_X"}  # "v_Q", "v_X", "v_Z", "v_ObjectiveWithQuality"}
# free_variables(strategic_model, discrete_variables_names)
# deactivate_slacks(strategic_model)
# strategic_model.quality.objective.deactivate()
# strategic_model.CostObjectiveFunction.deactivate()

# from pyomo.environ import Constraint, Objective, minimize, SolverFactory, Param
# strategic_model.penalty = Param(initialize=1,mutable=True)
# from pareto.utilities.solvers import get_solver, set_timeout
# def CostObjectiveFunctionRule2(model):
#             return model.v_Z == (
#                 model.v_C_TotalSourced
#                 + model.v_C_TotalDisposal
#                 + model.v_C_TotalTreatment
#                 + model.v_C_TotalReuse
#                 + model.v_C_TotalPiping
#                 + model.v_C_TotalStorage
#                 + model.v_C_TotalTrucking
#                 + model.v_C_TotalTreatment_surrogate
#                 + model.v_C_TreatmentCapex_surrogate
#                 + model.p_alpha_AnnualizationRate
#                 * (
#                     model.v_C_DisposalCapEx
#                     + model.v_C_StorageCapEx
#                     + model.v_C_TreatmentCapEx
#                     + model.v_C_PipelineCapEx
#                 )
#                 + model.v_C_Slack
#                 - model.v_R_TotalStorage
#                 + model.penalty*sum(model.quality.v_Q[sites, w, t] for sites in desal_sites for w in model.s_QC for t in model.s_T)
#             )

# strategic_model.ObjectiveFunction = Constraint(
#             rule=CostObjectiveFunctionRule2, doc="MINLP objective function"
#         )

# wall_time=[]
# time=[]
# solver_status=[]
# objs=[]
# penalty_value=[]

# # You should change the below array to desired penalty, 
# # this was done just to get a feel for the magnitude of 
# # the penalty term


# minlp_solver_source = 'gurobi'
# if minlp_solver_source == "gams":
#     mathoptsolver = "dicopt"
#     solver_options = {
#         "tol": 1e-3,
#         "max_iter": 1000,
#         "constr_viol_tol": 0.009,
#         "acceptable_constr_viol_tol": 0.01,
#         "acceptable_tol": 1e-6,
#         "mu_strategy": "adaptive",
#         "mu_init": 1e-10,
#         "mu_max": 1e-1,
#         "print_user_options": "yes",
#         "warm_start_init_point": "yes",
#         "warm_start_mult_bound_push": 1e-60,
#         "warm_start_bound_push": 1e-60,
#         #   'linear_solver': 'ma27',
#         #   'ma57_pivot_order': 4
#     }
#     import os
>>>>>>> parent of 3e69472 (Revert to this if nothing else works)

#     if not os.path.exists("temp"):
#         os.makedirs("temp")

#     with open("temp/" + mathoptsolver + ".opt", "w") as f:
#         for k, v in solver_options.items():
#             f.write(str(k) + " " + str(v) + "\n")

<<<<<<< HEAD
    strategic_model.penalty = 10
    print(i)
    try:
        results = SolverFactory(minlp_solver_source).solve(
            strategic_model,
            tee=True,
            keepfiles=True,
            solver=mathoptsolver,
            tmpdir="temp",
            add_options=["gams_model.optfile=1;"],
        )
        res = list(results.values())
        solver_status.append(res[1][0]["Termination condition"].value)
        wall_time.append(res[1][0]["Wall time"])
        time.append(res[1][0]["Time"])
        objs.append(strategic_model.objective())
        penalty_value.append(i)
    except:
        solver_status.append("TimeoutError")
        wall_time.append(1500)
        time.append(1500)
        objs.append(None)
        penalty_value.append(i)

elif minlp_solver_source == "gurobi":
    print("solving with GUROBI")
    mathoptsolver = "gurobi"
    solver = SolverFactory(mathoptsolver)
    solver.options["timeLimit"] = 1500
    solver.options["NonConvex"] = 2
    solver.options["MIPGap"] = 0.05

    strategic_model.penalty = 0.001
    try:
        results = solver.solve(strategic_model, tee=False, warmstart=True)
        res = list(results.values())
        solver_status.append(res[1][0]["Termination condition"].value)
        wall_time.append(res[1][0]["Wall time"])
        time.append(res[1][0]["Time"])
        objs.append(strategic_model.objective())
        penalty_value.append(0.001)
    except:
        solver_status.append("TimeoutError")
        wall_time.append(1500)
        time.append(1500)
        objs.append(None)
        penalty_value.append(0.001)

elif minlp_solver_source == "baron":
    solver = SolverFactory("baron")
    for i in penalties:
        strategic_model.penalty = i
        print(i)
        try:
            results = solver.solve(strategic_model, tee=False)
            res = list(results.values())
            solver_status.append(res[1][0]["Termination condition"].value)
            wall_time.append(res[1][0]["Wall time"])
            time.append(res[1][0]["Time"])
            objs.append(strategic_model.objective())
            penalty_value.append(i)
        except:
            solver_status.append("TimeoutError")
            wall_time.append(1500)
            time.append(1500)
            objs.append(None)
            penalty_value.append(i)

elif minlp_solver_source == "ipopt":
    solver = get_solver("ipopt")
    solver.options["maxiter"] = 100
    for i in penalties:
        strategic_model.penalty = i
        print(i)
        try:
            results = solver.solve(strategic_model, tee=False)
            res = list(results.values())
            solver_status.append(res[1][0]["Termination condition"].value)
            wall_time.append(res[1][0]["Wall time"])
            time.append(res[1][0]["Time"])
            objs.append(strategic_model.objective())
            penalty_value.append(i)
        except:
            solver_status.append("TimeoutError")
            wall_time.append(1500)
            time.append(1500)
            objs.append(None)
            penalty_value.append(i)
=======
#     strategic_model.penalty=10
#     print(i)
#     try:
#         results = SolverFactory(minlp_solver_source).solve(
#             strategic_model,
#             tee=True,
#             keepfiles=True,
#             solver=mathoptsolver,
#             tmpdir="temp",
#             add_options=["gams_model.optfile=1;"],
#         )
#         res=list(results.values())
#         solver_status.append(res[1][0]['Termination condition'].value)
#         wall_time.append(res[1][0]['Wall time'])
#         time.append(res[1][0]['Time'])
#         objs.append(strategic_model.objective())
#         penalty_value.append(i)
#     except:
#         solver_status.append('TimeoutError')
#         wall_time.append(1500)
#         time.append(1500)
#         objs.append(None)
#         penalty_value.append(i)

# elif minlp_solver_source == "gurobi":
#     print("solving with GUROBI")
#     mathoptsolver = 'gurobi'
#     solver = SolverFactory(mathoptsolver)
#     solver.options["timeLimit"] = 1500
#     solver.options["NonConvex"] = 2
#     solver.options["MIPGap"] = 0.05

#     strategic_model.penalty=0.001
#     try:
#         results = solver.solve(strategic_model, tee=False, warmstart=True)
#         res=list(results.values())
#         solver_status.append(res[1][0]['Termination condition'].value)
#         wall_time.append(res[1][0]['Wall time'])
#         time.append(res[1][0]['Time'])
#         objs.append(strategic_model.objective())
#         penalty_value.append(0.001)
#     except:
#         solver_status.append('TimeoutError')
#         wall_time.append(1500)
#         time.append(1500)
#         objs.append(None)
#         penalty_value.append(0.001)

# elif minlp_solver_source == "baron":
#     solver = SolverFactory("baron")
#     for i in penalties:
#         strategic_model.penalty=i
#         print(i)
#         try:
#             results = solver.solve(strategic_model, tee=False)
#             res=list(results.values())
#             solver_status.append(res[1][0]['Termination condition'].value)
#             wall_time.append(res[1][0]['Wall time'])
#             time.append(res[1][0]['Time'])
#             objs.append(strategic_model.objective())
#             penalty_value.append(i)
#         except:
#             solver_status.append('TimeoutError')
#             wall_time.append(1500)
#             time.append(1500)
#             objs.append(None)
#             penalty_value.append(i)

# elif minlp_solver_source == 'ipopt':
#     solver = get_solver('ipopt')
#     solver.options['maxiter'] = 100
#     for i in penalties:
#         strategic_model.penalty=i
#         print(i)
#         try:
#             results = solver.solve(strategic_model, tee=False)
#             res=list(results.values())
#             solver_status.append(res[1][0]['Termination condition'].value)
#             wall_time.append(res[1][0]['Wall time'])
#             time.append(res[1][0]['Time'])
#             objs.append(strategic_model.objective())
#             penalty_value.append(i)
#         except:
#             solver_status.append('TimeoutError')
#             wall_time.append(1500)
#             time.append(1500)
#             objs.append(None)
#             penalty_value.append(i)
>>>>>>> parent of 3e69472 (Revert to this if nothing else works)

# # Check feasibility of the solved model
# def check_feasibility(model):
#     with nostdout():
#         feasibility_status = is_feasible(model)
#     if not feasibility_status:
#         print("Model results are not feasible and should not be trusted")
#     else:
#         print("Model results validated and found to pass feasibility tests")

<<<<<<< HEAD

check_feasibility(strategic_model)
=======
# check_feasibility(strategic_model)
>>>>>>> parent of 3e69472 (Revert to this if nothing else works)

# [model, results_dict] = generate_report(
#     strategic_model,
#     # is_print=[PrintValues.essential],
#     output_units=OutputUnits.user_units,
#     fname="strategic_optimization_small_case_results_SRA_post_process.xlsx",
# )
