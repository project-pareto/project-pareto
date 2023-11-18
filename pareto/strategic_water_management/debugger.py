'''
Write the below two lines in the model and then run it. 
Does not matter if it is above or below the solve statement

filename = os.path.join(os.path.dirname(__file__), 'model.lp')
model.write(filename, io_options={'symbolic_solver_labels': True})

Once you run the model and it turns out to be infeasible, 
read the file here and then run this script
'''
import gurobipy

m = gurobipy.read("model.lp")
m.optimize()
m.computeIIS()
m.write('iismodel.ilp')
