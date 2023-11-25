"""
Write the below two lines in the model and then run it. 
Does not matter if it is above or below the solve statement

filename = os.path.join(os.path.dirname(__file__), 'model.lp')
model.write(filename, io_options={'symbolic_solver_labels': True})

Once you run the model and it turns out to be infeasible, 
read the file here and then run this script
"""
import gurobipy
from pareto.utilities.results_minlp import (
    generate_report,
    PrintValues,
    OutputUnits,
    is_feasible,
    nostdout,
)


def check_feasibility(model):
    with nostdout():
        feasibility_status = is_feasible(model)
    if not feasibility_status:
        print("Model results are not feasible and should not be trusted")
    else:
        print("Model results validated and found to pass feasibility tests")


m = gurobipy.read("model.lp")
m.setParam("TimeLimit", 600)
m.optimize()
# check_feasibility(m)
[model, results_dict] = generate_report(
    m,
    # is_print=[PrintValues.essential],
    output_units=OutputUnits.user_units,
    fname="MINLP.xlsx",
)
m.computeIIS()
m.write("iismodel.ilp")
