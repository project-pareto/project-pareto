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

from pareto.strategic_water_management.strategic_produced_water_optimization_with_surrogate_elmira_revised_MINLP import (

# from pareto.strategic_water_management.strategic_produced_water_optimization_minlp import (
    WaterQuality,
    create_model,
    Objectives,
    solve_model,
    PipelineCost,
    PipelineCapacity,
    Hydraulics,
    RemovalEfficiencyMethod,
)
import pyomo.opt
from pyomo.opt import TerminationCondition
from pyomo.contrib.iis import write_iis
import gurobipy


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

# from tabulate import tabulate

# Each entry in set_list corresponds to a tab in the Excel input file that
# defines an index set.
set_list = [
    "ProductionPads",
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
    "TreatmentTechnologies",
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
    "RSA",
    "SCA",
    "SNA",
    "ROA",
    "SOA",
    "NOA",
    "PCT",
    "PKT",
    "FCT",
    "CST",
    "CCT",
    "CKT",
    "RST",
    "ROT",
    "SOT",
    "Elevation",
    "CompletionsPadOutsideSystem",
    "DesalinationTechnologies",
    "DesalinationSites",
    "BeneficialReuseCredit",
    "TruckingTime",
    "CompletionsDemand",
    "PadRates",
    "FlowbackRates",
    "WellPressure",
    "NodeCapacities",
    "InitialPipelineCapacity",
    "InitialPipelineDiameters",
    "InitialDisposalCapacity",
    "InitialTreatmentCapacity",
    "ReuseMinimum",
    "ReuseCapacity",
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
    "RemovalEfficiency",
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
    "DisposalOperatingCapacity",
    "TreatmentExpansionLeadTime",
    "DisposalExpansionLeadTime",
    "StorageExpansionLeadTime",
    "PipelineExpansionLeadTime_Dist",
    "PipelineExpansionLeadTime_Capac",
]

# Load data from Excel input file into Python
with resources.path(
    "pareto.case_studies",
    "strategic_treatment_demo_modified_only_MVC.xlsx",
    # "strategic_toy_case_study.xlsx",
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
    "running_time": 5000,
    "gap": 0,
    "gurobi_numeric_focus": 1,
}
results_obj = solve_model(model=strategic_model, options=options)



# Check feasibility of the solved model
def check_feasibility(model):
    with nostdout():
        feasibility_status = is_feasible(model)
    if not feasibility_status:
        print("Model results are not feasible and should not be trusted")
    else:
        print("Model results validated and found to pass feasibility tests")

# check_feasibility(strategic_model)


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
                    if str(var)[:23]!='quality.surrogate_costs':
                        index_var.unfix()
                        index_var.setlb(0)
                        index_var.setub(None)
                    else:
                        index_var.unfix()


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
                    
# Step 2.1: unfix variables (MILP model)
discrete_variables_names = {"v_X"}  # "v_Q", "v_X", "v_Z", "v_ObjectiveWithQuality"}
free_variables(strategic_model, discrete_variables_names)
deactivate_slacks(strategic_model)
strategic_model.quality.objective.deactivate()
strategic_model.CostObjectiveFunction.deactivate()

from pyomo.environ import Constraint, Objective, minimize, SolverFactory, Param
strategic_model.penalty = Param(initialize=1,mutable=True)
desal_sites = {"R01","R03", "R06" }
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
                + model.v_C_TotalTreatment_surrogate
                + model.v_C_TreatmentCapEx_surrogate
                + model.p_alpha_AnnualizationRate
                * (
                    model.v_C_DisposalCapEx
                    + model.v_C_StorageCapEx
                    + model.v_C_TreatmentCapEx
                    + model.v_C_PipelineCapEx
                )
                + model.v_C_Slack
                - model.v_R_TotalStorage
                + model.penalty*sum(model.quality.v_Q[sites, w, t] for sites in desal_sites for w in model.s_QC for t in model.s_T)
            )

strategic_model.ObjectiveFunction = Constraint(
            rule=CostObjectiveFunctionRule2, doc="MINLP objective function"
        )

wall_time=[]
time=[]
solver_status=[]
objs=[]
penalty_value=[]

# You should change the below array to desired penalty, 
# this was done just to get a feel for the magnitude of 
# the penalty term


minlp_solver_source = 'gurobi'
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

    if not os.path.exists("temp"):
        os.makedirs("temp")

    with open("temp/" + mathoptsolver + ".opt", "w") as f:
        for k, v in solver_options.items():
            f.write(str(k) + " " + str(v) + "\n")

    strategic_model.penalty=10
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
        res=list(results.values())
        solver_status.append(res[1][0]['Termination condition'].value)
        wall_time.append(res[1][0]['Wall time'])
        time.append(res[1][0]['Time'])
        objs.append(strategic_model.objective())
        penalty_value.append(i)
    except:
        solver_status.append('TimeoutError')
        wall_time.append(1500)
        time.append(1500)
        objs.append(None)
        penalty_value.append(i)

elif minlp_solver_source == "gurobi":
    print("solving with GUROBI")
    opt = SolverFactory('gurobi_persistent')
    strategic_model.penalty = 1

    # Set the model instance for the persistent solver
    opt.set_instance(strategic_model)

    # Set GUROBI specific options
    opt.options["timeLimit"] = 1500
    opt.options["NoRelHeurTime"] = 100
    opt.options["NonConvex"] = 2
    opt.options["MIPGap"] = 0.005

    try:
        results = opt.solve(tee=False, warmstart=True)
        termination_condition = results.solver.termination_condition

        # Check for infeasibility
        if termination_condition == pyomo.opt.TerminationCondition.infeasible:
            print("Model is infeasible, computing IIS...")
            write_iis(pyomo_model=strategic_model, iis_file_name="infeasible_model.ilp", solver='gurobi')
            print("IIS written to file 'infeasible_model.ilp'")
        else:
            # handle feasible solutions
            print("Model solved ....")

    except Exception as e:
        print("An exception occurred: ", e)
        solver_status.append('Error')
        wall_time.append(1500)
        time.append(1500)
        objs.append(None)
        penalty_value.append(0.001)



elif minlp_solver_source == "baron":
    solver = SolverFactory("baron")
    for i in penalties:
        strategic_model.penalty=i
        print(i)
        try:
            results = solver.solve(strategic_model, tee=False)
            res=list(results.values())
            solver_status.append(res[1][0]['Termination condition'].value)
            wall_time.append(res[1][0]['Wall time'])
            time.append(res[1][0]['Time'])
            objs.append(strategic_model.objective())
            penalty_value.append(i)
        except:
            solver_status.append('TimeoutError')
            wall_time.append(1500)
            time.append(1500)
            objs.append(None)
            penalty_value.append(i)

elif minlp_solver_source == 'ipopt':
    solver = get_solver('ipopt')
    solver.options['maxiter'] = 100
    for i in penalties:
        strategic_model.penalty=i
        print(i)
        try:
            results = solver.solve(strategic_model, tee=False)
            res=list(results.values())
            solver_status.append(res[1][0]['Termination condition'].value)
            wall_time.append(res[1][0]['Wall time'])
            time.append(res[1][0]['Time'])
            objs.append(strategic_model.objective())
            penalty_value.append(i)
        except:
            solver_status.append('TimeoutError')
            wall_time.append(1500)
            time.append(1500)
            objs.append(None)
            penalty_value.append(i)

# Check feasibility of the solved model
def check_feasibility(model):
    with nostdout():
        feasibility_status = is_feasible(model)
    if not feasibility_status:
        print("Model results are not feasible and should not be trusted")
    else:
        print("Model results validated and found to pass feasibility tests")

check_feasibility(strategic_model)

#[model, results_dict] = generate_report(
 #   strategic_model,
    # is_print=[PrintValues.essential],
  #  output_units=OutputUnits.user_units,
   # fname="strategic_optimization_MINLP_gurobi.xlsx",
#)
