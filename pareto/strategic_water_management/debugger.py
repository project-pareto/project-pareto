import gurobipy

m = gurobipy.read("model.lp")
m.optimize()
m.computeIIS()
m.write('iismodel.ilp')
