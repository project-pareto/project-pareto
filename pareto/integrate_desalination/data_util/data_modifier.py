# -*- coding: utf-8 -*-
"""
Created on Fri Dec 22 09:32:56 2023

@author: ssnaik
"""

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

def add_solids_gen_parameter(d):
    #This function adds a solids generated parameter. 
    
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
                
    d['p_Cap_treat_min'] = 0.1
    
    return d

def add_min_capacity_parameter(d):
    d['p_Cap_treat_min'] = 0.1
    
    return d