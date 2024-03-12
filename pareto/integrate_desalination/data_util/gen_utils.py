"""
General Utilities
This file contains any utility functions that would help processing data,
generating reports, etc.
"""

import pyomo.environ as pyo
import pandas as pd
import sys

def set_processing(d):
    # This function does any required processing for the sets
    if 's_NT' in d:
        d['s_NTIN'] = []
        d['s_NTTW'] = []
        d['s_NTCW'] = []
        for i in d['s_NT']:
            d['s_NTIN'].append(i+'_IN')
            d['s_NTTW'].append(i+'_TW')
            d['s_NTCW'].append(i+'_CW')

    d['s_N'] = (d['s_NMS'] + d['s_NP'] + d['s_NC'] + d['s_NS'] + d['s_NW'] 
                + d['s_ND'] + d['s_NTIN'] + d['s_NTTW'] + d['s_NTCW'])

    # Categorized Nodes
    d['s_NNoInv'] = d['s_NMS'] + d['s_NP'] + d['s_NC']
    d['s_NInv'] = d['s_NS']
    d['s_NSrc'] = d['s_NW']
    d['s_NSnk'] = d['s_ND'] + d['s_NTIN']
    d['s_NTSrc'] = d['s_NTTW'] + d['s_NTCW']

    # Arcs In
    A_out = dict()
    A_in = dict()

    items = [A_out, A_in]
    for i in range(len(items)):
        for n in d['s_N']:
            n_tuple_set = [] 
            for arc in d['s_A']:
                if n == arc[i]:
                    n_tuple_set.append(arc)
            items[i][n] = n_tuple_set
    
    d['s_Ain'] = A_in
    d['s_Aout'] = A_out

    return d

def parameter_processing(d):
    # This function is required for processing the parameters

    d['p_nodeUp'] = {a: a[0] for a in d['s_A']}
    d['p_nodeDown'] = {a: a[1] for a in d['s_A']}
    d['p_tp'] = {a: a[2] for a in d['s_A']}

    return d



def data_preprocessing(d):
    # TODO: assert in data preprocessing that there should not be demand and flowback for a completion pad during the same t 
    # TODO: Assert that if there is no flow coming out of a completion pad, there should not be a composition either
    # TODO: Handle empty sets
    # TODO: Assert that arcs are made by components that exist in s_N
    
    # creating a set N: union of all nodes
    d['s_N'] = d['s_NMS'] + d['s_NP'] + d['s_NC'] + d['s_NS'] + d['s_ND']+ d['s_NW'] + d['s_NT']

    # defining input and output arcs
    A_out = dict()
    A_in = dict()

    items = [A_out, A_in]
    for i in range(len(items)):
        for n in d['s_N']:
            n_tuple_set = [] 
            for arc in d['s_A']:
                if n == arc[i]:
                    n_tuple_set.append(arc)
            items[i][n] = n_tuple_set

    d['s_Ain'] = A_in
    d['s_Aout'] = A_out 

    return d

def solve_nlp(m, solvername='gurobi', time_limit=100, tee=True):
    if solvername == 'gurobi':
        opt = pyo.SolverFactory('gurobi')
        opt.options['TimeLimit'] = time_limit
        opt.options['NonConvex'] = 2
        # opt.options['Threads'] = 8
        m.results = opt.solve(m, tee=tee)
    
    # TODO: Add flags needed for opensource version of ipopt
    # elif solvername == 'ipopt' ...

    else:
        # SOLVE
        opt = pyo.SolverFactory('gams', solver=solvername)
        m.results = opt.solve(m, tee=tee,
                            add_options=[
                                'option reslim = ',str(time_limit),';'])
    
    return m

def report_results_to_excel(model: pyo.ConcreteModel, filename: str, split_var: dict = {}) -> None:
    counter = 0
    for var_name, var in model.component_map(pyo.Var, active=True).items():
        
        #creating the columns for the excel file
        set_names = []
        for index_set in var.index_set().subsets():
            if index_set.name in list(split_var.keys()):
                num_splits = split_var[index_set.name]
                for i in range(1,num_splits+1):
                    set_names.append(index_set.name + str(i))
            else:
                set_names.append(index_set.name)
        set_names.append('Values')

        # assigning values to the data frame
        df = pd.DataFrame(columns = set_names)
        k = 0
        for i in list(var.keys()):
            row = list(i)
            row.append(var[i].value)
            df.loc[k] = row
            k += 1

        # adding variable sheet to the excel
        if counter == 0:
            with pd.ExcelWriter(filename, mode = 'w') as writer: 
                df.to_excel(writer, sheet_name = var.name)
        else:
            with pd.ExcelWriter(filename, mode = 'a') as writer: 
                df.to_excel(writer, sheet_name = var.name)
        counter += 1

# Function to turn off certain variables and constraints
def obj_fix(model: pyo.ConcreteModel, var, cons):

    # Fixing and unfixing specified variables
    for var_name, var in model.component_map(pyo.Var, active = True).items():
        # fixing variables if they are specified by user
        if var_name in vars:
            for i in list(var.keys()):
                var[i].fix(var[i].value)
        # unfixing remaining variables
        else:
            var.unfix()

    # Deactivating constraints specified by user
    for con_name, con in model.component_map(pyo.Constraint, active = True).items():
        if con_name in cons:    # deactivating
            con.deactivate()
        else:   # activating 
            con.activate()
    
    return model

# Terminate script if model is infeasible or unbounded
def terminate(status):
    term_cond = status.solver.termination_condition
    if  term_cond != 'infeasible' or 'unbounded':
        pass
    else:
        print("Model is", term_cond, ". Terminating script")
        return sys.exit()

def add_solids_gen_parameter(d):
    #This function adds a solids generated parameter.for the solids based model 
    
    d['p_SGen'] = {}
    for n in d['s_NNoInv']:
        for t in d['s_T']:
            for q in d['s_Q']:
                if d['p_CGen'][n,q,t] != 0 and d['p_FGen'][n,t] != 0:
                    d['p_SGen'][n,q,t] = d['p_CGen'][n,q,t]*d['p_FGen'][n,t]
                else:
                    d['p_SGen'][n,q,t] = 0
                    
    d['p_IS0'] = {}
    for n in d['s_NInv']:
        for q in d['s_Q']:
            if d['p_I0'] != 0 and d['p_C0'] != 0:
                d['p_IS0'][n, q] = d['p_I0'][n]*d['p_C0'][n,q]
            else:
                d['p_IS0'][n, q] = 0
    
    return d

def add_treatment_capacities(d, capacities = None, units = None):
    #capacities should be a dictionary of the form
    #{Treatment_site: {min_flow_capacity: min_flow, min_inlet_concentration: min_concentration}}
    #Units should be a dictionary of the form 
    #{flow_units:unit, concentration_units: unit}
    from pyomo.environ import units as pyunits
    d['p_flow_treatment_min'] = {}
    d['p_Cmin_treatment_inlet'] = {}
  
    if capacities is None and units is None:
        d['flow_units'] = pyunits.liter/pyunits.s
        d['concentration_units'] = pyunits.g/pyunits.liter
        for n in d['s_NTIN']:
            d['p_flow_treatment_min'][n] = 3
            d['p_Cmin_treatment_inlet'][n] = 70
    
    else:
        d['flow_units'] = units['flow_inits']
        d['concentration_units'] = units['concentration_units']
        for n in d['s_NTIN']:
            d['p_flow_treatment_min'][n] = capacities["min_flow"][n]
            d['p_Cmin_treatment_inlet'][n] = capacities["min_concentration"][n]
    
    return d