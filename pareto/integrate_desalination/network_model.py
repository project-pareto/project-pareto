# -*- coding: utf-8 -*-
"""
Created on Wed Nov 15 15:22:09 2023

@author: ssnaik
"""

import pyomo.environ as pyo
from pyomo.environ import units as pyunits
from pyomo.util.check_units import assert_units_consistent
from pareto.integrate_desalination.data_util.get_model_from_case_study import get_processed_data

def build_qcp(data, init_custom = False, init_custom_param = None):
    #Load kUSD as units in the pint_registry if the unit is absent
    try:
        getattr(pyunits.pint_registry, 'kUSD')
    except:
        pyunits.load_definitions_from_strings(['kUSD = [currency]'])
    
    model = pyo.ConcreteModel()

    # -------------------SETS-----------------------------
    # Nodes
    model.s_N = pyo.Set(initialize=data['s_N'], doc='Nodes')
    model.s_NMS = pyo.Set(initialize=data['s_NMS'], doc='Mixers/Splitters')
    model.s_NP = pyo.Set(initialize=data['s_NP'], doc='Production pads')
    model.s_NC = pyo.Set(initialize=data['s_NC'], doc='Completion pads')
    model.s_NS = pyo.Set(initialize=data['s_NS'], doc='Storage')
    model.s_ND = pyo.Set(initialize=data['s_ND'], doc='Disposal')
    model.s_NW = pyo.Set(initialize=data['s_NW'], doc='Fresh water source')
    model.s_NTIN = pyo.Set(initialize = data['s_NTIN'], doc = 'Inlet to Treatment Facility')
    model.s_NTTW = pyo.Set(initialize = data['s_NTTW'], doc = 'Treatmed Water of Treatment Facility')
    model.s_NTCW = pyo.Set(initialize = data['s_NTCW'], doc = 'Concentrated Water of Treatment Facility') 
    
    # Arcs
    model.s_A = pyo.Set(initialize = data['s_A'], doc = "Arcs")
    model.s_Ain = pyo.Param(model.s_N, initialize = data['s_Ain'], doc = 'Arcs going into node')
    model.s_Aout = pyo.Param(model.s_N, initialize = data['s_Aout'], doc = "Arcs coming out of node")

    # Components
    model.s_Q = pyo.Set(initialize = data['s_Q'], doc = "Components")
    
    # TODO: Can't do this because then you will have to separate sets for each node
    model.s_Qalpha = pyo.Param(model.s_NTIN, initialize = data['s_Qalpha'], doc = "Components being treated at Treated Water Node")

    # Time Periods
    model.s_T = pyo.Set(initialize = data['s_T'], doc = "Time Periods")

    # ----------------------PARAMETERS-------------------------------------
    # Generation and Consumption Parameters
    model.p_FGen = pyo.Param(model.s_NMS|model.s_NP|model.s_NC, model.s_T, initialize = data['p_FGen'], doc = "Flow Generated", units = pyunits.bbl/pyunits.day)
    model.p_CGen = pyo.Param(model.s_NMS|model.s_NP|model.s_NC, model.s_Q, model.s_T, initialize = data['p_CGen'], doc = "Concentration in flow generated", units = pyunits.g/pyunits.liter)
    model.p_SGen = pyo.Param(model.s_NMS|model.s_NP|model.s_NC, model.s_Q, model.s_T, initialize = data['p_SGen'], doc = "Solids generated", units = pyunits.bbl/pyunits.day*pyunits.g/pyunits.liter)
    model.p_FCons = pyo.Param(model.s_NMS|model.s_NP|model.s_NC, model.s_T, initialize = data['p_FCons'], doc = "Flow consumed", units = pyunits.bbl/pyunits.day)

    # Inventory Parameters
    model.p_I0 = pyo.Param(model.s_NS, initialize = data['p_I0'], doc = "Initial Inventory", units = pyunits.bbl)
    model.p_IS0 = pyo.Param(model.s_NS, model.s_Q, initialize = data['p_IS0'], doc = "Initial solids in inventory", units = pyunits.bbl*pyunits.g/pyunits.liter)
    
    # Treatment Efficiencies
    #Should be set to 1 in the case where we use MVC as the treatment unit. 
    model.p_alpha = pyo.Param(model.s_NTIN, model.s_Q, initialize = data['p_alpha'], doc = "Treatment Efficiency")

    # Capacity limits for sinks
    model.p_Cap = pyo.Param(model.s_ND | model.s_NW | model.s_NTIN, initialize = data['p_Cap'], doc = "Capacity of sources and sinks", units = pyunits.bbl/pyunits.day)
    model.p_Cap_treat_min = pyo.Param(model.s_NTIN, initialize = data['p_Cap_treat_min'], doc = "Minimum flow to the treatment node", units = pyunits.bbl/pyunits.day)
    # Time discretization
    model.p_dt = pyo.Param(initialize = data['p_dt'], doc = "Time discretized for inventory", units = pyunits.day)

    # Minimum treatment concentration required
    model.p_Cmin = pyo.Param(model.s_NTCW, model.s_Q, initialize = data['p_Cmin'], mutable = True, doc = "Minimum concentration required at the concentrated water node", units = pyunits.g/pyunits.liter)
    model.p_Cmax = pyo.Param(initialize = 300, doc = "Maximum concentration in the network", units = pyunits.g/pyunits.liter)
    # Cost Parameters
    
    model.p_betaArc = pyo.Param(model.s_A, initialize = data['p_betaArc'], doc = "Operational costs of arcs" ,units = pyunits.kUSD/pyunits.bbl)
    model.p_betaD = pyo.Param(model.s_ND, initialize = data['p_betaD'], mutable = True, doc = "Operational cost of disposal site",units = pyunits.kUSD/pyunits.bbl)
    model.p_betaW = pyo.Param(model.s_NW, initialize = data['p_betaW'], doc = "Costs of sourcing freshwater",units = pyunits.kUSD/pyunits.bbl)
    model.p_betaT = pyo.Param(model.s_NTIN, initialize = data['p_betaT'], mutable = True, doc = "Operating cost of treatment facility",units = pyunits.kUSD/pyunits.bbl)
    model.p_betaS = pyo.Param(model.s_NS, initialize = data['p_betaS'], mutable = True, doc = "Costs of storing produced water",units = pyunits.kUSD/pyunits.bbl)
    
    #Differentiating the costs to send water to inventory slightly to avoid degeneracy
    data_inv_cost = {}
    counter = 0
    for n in model.s_NS:
        delta = 0.00001
        for t in model.s_T:
            data_inv_cost[n, t] = pyo.value(model.p_betaS[n]+ len(model.s_T)*delta - delta*counter)
            counter = counter + 1
            
   
    model.p_betaSt = pyo.Param(model.s_NS, model.s_T, initialize = data_inv_cost, mutable = True, doc = "Costs of storing produced water",units = pyunits.kUSD/pyunits.bbl)
    
    model.p_gammaS = pyo.Param(model.s_NS, initialize = data['p_gammaS'], mutable = True, doc = "Earnings from retrieving water from storage tanks",units = pyunits.kUSD/pyunits.bbl)
    model.p_gammaT = pyo.Param(model.s_NTTW, initialize = data['p_gammaT'], mutable = True, doc = "Earnings from treating water",units = pyunits.kUSD/pyunits.bbl)
    
    # Functions
    model.p_nodeUp = pyo.Param(model.s_A, initialize = data['p_nodeUp'], doc = "Upstream node of the arc")
    model.p_nodeDown = pyo.Param(model.s_A, initialize = data['p_nodeDown'], doc = "Downstream node of the arc")
    model.p_tp = pyo.Param(model.s_A, initialize = data['p_tp'], doc = "Type of arc")
    model.p_treatedIN = pyo.Param(model.s_NTTW | model.s_NTCW, initialize = data['p_treatedIN'], doc = "Inlet node for each treatment facility")
    
    # --------------------VARIABLES-----------------------------
    model.v_F = pyo.Var(model.s_A, model.s_T, bounds = data['p_Fbounds'], doc = "Flow in arc", initialize = 5, units = pyunits.liter/pyunits.s)
    model.v_S = pyo.Var(model.s_A, model.s_Q, model.s_T, bounds = (0,30000),doc = "Solid flow in arc", initialize = 30, units = pyunits.g/pyunits.s)
    model.v_I = pyo.Var(model.s_NS, model.s_T, bounds=data['p_Ibounds'], doc = "Inventory in node", initialize = 10, units = pyunits.liter)
    model.v_IS = pyo.Var(model.s_NS, model.s_Q, model.s_T, bounds = (0, 30000), doc ="Solids in the inventory node", initialize = 100, units = pyunits.g)
    model.v_C = pyo.Var(model.s_NTIN |model.s_NTTW | model.s_NTCW | model.s_NS , model.s_Q, model.s_T, bounds = (0,300), doc = "Concentration of water at nodes", initialize = 100, units = pyunits.g/pyunits.liter)
    model.v_alphaW = pyo.Var(model.s_NTIN, model.s_T, bounds = (0.1,0.9), doc = "Treatment Efficiency", initialize = 0.5)
    model.v_Ctreatin = pyo.Var(model.s_NTIN, model.s_T, doc = "Concentration of salts going to treatment", bounds = (0, 210), initialize = 100, units = pyunits.g/pyunits.liter)
    #Custom initialization
    if init_custom:
        model.v_I[:, :] = init_custom_param['I_init']
        model.v_IS[:, :, :] = init_custom_param['IS_init']
   
    #Node R01 is just pretreatment. So fix it's alpha 
    #Scaling factor 
    scale_fac = 1/100
    # ----------------------OBJECTIVE---------------------------
    
    @model.Expression()
    def arc_cost(m):
        return sum(sum(pyunits.convert(m.p_betaArc[a], pyunits.kUSD/pyunits.liter)*m.v_F[a,t] for a in m.s_A) for t in m.s_T)*pyunits.convert(m.p_dt, pyunits.s)
    
    @model.Expression()
    def disp_cost(m):
        return sum(sum(pyunits.convert(m.p_betaD[n], pyunits.kUSD/pyunits.liter)*sum(m.v_F[a,t] for a in m.s_Ain[n]) for n in m.s_ND) for t in m.s_T)*pyunits.convert(m.p_dt, pyunits.s)
    
    @model.Expression()
    def fresh_cost(m):
        return sum(sum(pyunits.convert(m.p_betaW[n], pyunits.kUSD/pyunits.liter)*sum(m.v_F[a,t] for a in m.s_Aout[n]) for n in m.s_NW) for t in m.s_T)*pyunits.convert(m.p_dt, pyunits.s)
    
    @model.Expression()
    def stor_cost(m):
        return sum(sum(pyunits.convert(m.p_betaSt[n,t], pyunits.kUSD/pyunits.liter)*sum(m.v_F[a,t] for a in m.s_Ain[n]) for n in m.s_NS) for t in m.s_T)*pyunits.convert(m.p_dt, pyunits.s)
    
    @model.Expression()
    def stor_rev(m):
        return sum(sum(pyunits.convert(m.p_gammaS[n], pyunits.kUSD/pyunits.liter)*sum(m.v_F[a,t] for a in m.s_Aout[n]) for n in m.s_NS) for t in m.s_T)*pyunits.convert(m.p_dt, pyunits.s)
    
    @model.Expression()
    def treatment_rev(m):
        return sum(sum(pyunits.convert(m.p_gammaT[n], pyunits.kUSD/pyunits.liter)*sum(m.v_F[a,t] for a in m.s_Aout[n]) for n in m.s_NTTW) for t in m.s_T)*pyunits.convert(m.p_dt, pyunits.s)
    
    @model.Objective(doc = "Cost Minimization Objective")
    def obj(m):
        return (m.arc_cost + m.disp_cost + m.fresh_cost + m.stor_cost - m.stor_rev - m.treatment_rev)

    # ---------------------------CONSTRAINTS-----------------------------------    
    # flow for non-inventory terms
    @model.Constraint(model.s_NP | model.s_NMS, model.s_T, doc = "General flow equation for non inventory nodes")
    def noinvflow(m,n,t):
        return sum(m.v_F[a,t] for a in m.s_Ain[n]) + pyunits.convert(m.p_FGen[n,t], pyunits.liter/pyunits.sec)== sum(m.v_F[a,t] for a in m.s_Aout[n]) + pyunits.convert(m.p_FCons[n,t], pyunits.liter/pyunits.s)
    assert_units_consistent(model.noinvflow)
    
    # solids flow for non-inventory terms 
    @model.Constraint(model.s_NP | model.s_NMS, model.s_Q, model.s_T, doc = "General solids flow equation for non inventory nodes")
    def noinvsolidsflow(m,n,q,t):
        return scale_fac*(sum(m.v_S[a,q,t] for a in m.s_Ain[n]) + pyunits.convert(m.p_SGen[n,q,t], pyunits.g/pyunits.s)) == scale_fac*(sum(m.v_S[a,q,t] for a in m.s_Aout[n]))
    assert_units_consistent(model.noinvsolidsflow)
    
    # Splitter and Mixers outlet concentration constraints
    model.splitter_conc = pyo.ConstraintList()
    for n in model.s_NMS:
        if len(model.s_Aout[n]) > 1:
            for q in model.s_Q:
                for t in model.s_T:
                    for a in model.s_Aout[n]:
                        model.splitter_conc.add(scale_fac*(model.v_S[a, q, t]*sum(model.v_F[a, t] for a in model.s_Ain[n])) == scale_fac*(sum(model.v_S[a, q, t] for a in model.s_Ain[n])*model.v_F[a, t]))
    assert_units_consistent(model.splitter_conc)     
        
    # Completion Pads
    # flow and concentration constraints are done together below
    model.Cflow = pyo.ConstraintList(doc = "Completions pad flow")
    model.Csolids = pyo.ConstraintList(doc = "Completions pad solids flow")
    for n in model.s_NC:
        for t in model.s_T:
            #condition where completion pad is producing 
            if pyo.value(model.p_FGen[n,t])>0 and pyo.value(model.p_FCons[n,t]) == 0:
                model.Cflow.add(pyunits.convert(model.p_FGen[n,t], pyunits.liter/pyunits.s) == sum(model.v_F[a,t] for a in model.s_Aout[n]))  # flow constraint
                model.Cflow.add(0 == sum(model.v_F[a,t] for a in model.s_Ain[n]))  # flow constraint
                for q in model.s_Q:
                    #Redundant constraint since the inequality bound takes care of this
                    model.Csolids.add(sum(model.v_S[a, q, t] for a in model.s_Ain[n]) == 0)
                    model.Csolids.add(pyunits.convert(model.p_SGen[n,q,t], pyunits.g/pyunits.s) == sum(model.v_S[a, q, t] for a in model.s_Aout[n]))    # solid flow constraint
                    
                    
            #condition where completion pad is consuming
            elif pyo.value(model.p_FGen[n,t]) == 0 and pyo.value(model.p_FCons[n,t]) > 0:
                model.Cflow.add(pyunits.convert(model.p_FCons[n,t], pyunits.liter/pyunits.s) == sum(model.v_F[a,t] for a in model.s_Ain[n]))  # flow constraint
                model.Cflow.add(0 == sum(model.v_F[a,t] for a in model.s_Aout[n]))  # flow constraint
                # Solids are not tracked in this case
                #The sum of solids out of the completions pad is 0. Since solids have a LB of 0
                #All of them have to be 0
                #Redundant constraint since the inequality bound takes care of this
                for q in model.s_Q:
                    model.Csolids.add(sum(model.v_S[a,q,t] for a in model.s_Aout[n]) == 0)
            
            #condition where completion pad is neither producing nor consuming
            elif pyo.value(model.p_FGen[n,t]) == 0 and pyo.value(model.p_FCons[n,t]) == 0:
                model.Cflow.add(0 == sum(model.v_F[a,t] for a in model.s_Aout[n]))  # flow constraint
                model.Cflow.add(0 == sum(model.v_F[a,t] for a in model.s_Ain[n]))  # flow constraint
                for q in model.s_Q:
                    model.Csolids.add(sum(model.v_S[a, q, t] for a in model.s_Aout[n]) == 0)  # solid flow constraint
                    model.Csolids.add(sum(model.v_S[a, q, t] for a in model.s_Ain[n]) == 0)  # solid flow constraint
            
            #condition where completion pad is both producing and consuming
            elif pyo.value(model.p_FGen[n,t]) > 0 and pyo.value(model.p_FCons[n,t]) > 0:
                model.Cflow.add(pyunits.convert(model.p_FGen[n,t], pyunits.liter/pyunits.s) == sum(model.v_F[a,t] for a in model.s_Aout[n]))  # flow constraint
                model.Cflow.add(model.p_FCons[n,t] == sum(model.v_F[a,t] for a in model.s_Ain[n]))  # flow constraint
                for q in model.s_Q:
                    model.Cconc.add(pyunits.convert(model.p_SGen[n,q,t], pyunits.g/pyunits.s)== sum(model.S[a,q,t] for a in model.s_Aout[n]))    # solids flow constraint
    
    assert_units_consistent(model.Cflow)     
    assert_units_consistent(model.Csolids)     
        
    # Storage
    @model.Constraint(model.s_NS, model.s_T, doc = "Storage inventory balance")
    def Sinv(m,n,t):
        if t == m.s_T.first():
            return scale_fac*(m.v_I[n,t])== scale_fac*(pyunits.convert(m.p_I0[n], pyunits.liter) + sum(m.v_F[a,t] for a in m.s_Ain[n])*pyunits.convert(m.p_dt, pyunits.s) - sum(m.v_F[a,t] for a in m.s_Aout[n])*pyunits.convert(m.p_dt, pyunits.s))
        else:
            return scale_fac*(m.v_I[n,t]) == scale_fac*(m.v_I[n,m.s_T.prev(t)] + sum(m.v_F[a,t] for a in m.s_Ain[n])*pyunits.convert(m.p_dt, pyunits.s) - sum(m.v_F[a,t] for a in m.s_Aout[n])*pyunits.convert(m.p_dt, pyunits.s))
    assert_units_consistent(model.Sinv)
    
    @model.Constraint(model.s_NS, model.s_Q, model.s_T, doc = "Storage solids balance")
    def Sconc(m,n,q,t):
        if t == m.s_T.first():
            return scale_fac*(m.v_IS[n, q, t]) == scale_fac*(pyunits.convert(m.p_IS0[n, q], pyunits.g)+ 
                    sum(m.v_S[a,q,t] for a in m.s_Ain[n])*pyunits.convert(m.p_dt, pyunits.s) - sum(m.v_S[a,q,t] for a in m.s_Aout[n])*pyunits.convert(m.p_dt, pyunits.s))
        else:
            return scale_fac*(m.v_IS[n, q, t]) == scale_fac*(m.v_IS[n, q, m.s_T.prev(t)] + 
                    sum(m.v_S[a, q, t] for a in m.s_Ain[n])*pyunits.convert(m.p_dt, pyunits.s) - sum(m.v_S[a, q, t] for a in m.s_Aout[n])*pyunits.convert(m.p_dt, pyunits.s))
    assert_units_consistent(model.Sconc)
    
    #We need to maintain a concentration variable in the inventory unit
    #Since it is a storage tank and the flows aren't just in and out for a simple flow balance
    @model.Constraint(model.s_NS, model.s_Q, model.s_T)
    def Cinvcal(m,n,q,t):
        return m.v_C[n,q,t]*m.v_I[n,t] == m.v_IS[n, q, t]
    assert_units_consistent(model.Cinvcal)
    
    # #This constraint is essential if there is a pretreatment unit before storage. 
    # #Helps a little with situations where flow is 0 to storage and concentration can take any value since 
    # #v_IS is also 0 
    @model.Constraint(model.s_NS, model.s_Q, model.s_T)
    def Cinvzero_pretreatment(m,n,q,t):
        for a in m.s_Ain[n]:
            if a[0].endswith('TW'):
                return m.v_C[n,q,t] == 0
            else:
                return pyo.Constraint.Skip
    assert_units_consistent(model.Cinvzero_pretreatment)
    
    @model.Constraint(model.s_NS, model.s_Q, model.s_T)
    def Srelation(m,n,q,t):
        return scale_fac*sum(m.v_S[a, q, t] for a in m.s_Aout[n]) == scale_fac*m.v_C[n,q,t]*sum(m.v_F[a, t] for a in m.s_Aout[n])
    assert_units_consistent(model.Srelation)
    
    # Disposal
    @model.Constraint(model.s_ND, model.s_T, doc = "Disposal flow restriction")
    def Dflow(m,n,t):
        return sum(m.v_F[a,t] for a in m.s_Ain[n]) <= pyunits.convert(m.p_Cap[n], pyunits.liter/pyunits.s)
    assert_units_consistent(model.Dflow)
    
    # Freshwater 
    @model.Constraint(model.s_NW, model.s_T, doc = "Freshwater flow restriction")
    def Wflow(m,n,t):
        return sum(m.v_F[a,t] for a in m.s_Aout[n]) <= pyunits.convert(m.p_Cap[n], pyunits.liter/pyunits.s)
    assert_units_consistent(model.Wflow)
    
    @model.Constraint(model.s_NW, model.s_Q, model.s_T, doc = "Freshwater solids flow")
    def WSflow(m, n, q, t): 
        return sum(m.v_S[a, q, t] for a in m.s_Aout[n]) == 0
    assert_units_consistent(model.WSflow)
    
    # Treatment Inlet Node
    @model.Constraint(model.s_NTIN, model.s_T, doc = "Treatment inlet flow restriction")
    def TINflowmax(m,n,t):
        return sum(m.v_F[a,t] for a in m.s_Ain[n]) <= 20*pyunits.liter/pyunits.s
    assert_units_consistent(model.TINflowmax)
    
    # Treatment inlet node minimum flow restriction
    @model.Constraint(model.s_NTIN, model.s_T, doc = "Treatment inlet flow minimum")
    def TINflowmin(m,n,t):
        return sum(m.v_F[a,t] for a in m.s_Ain[n]) >= 3*pyunits.liter/pyunits.s
    assert_units_consistent(model.TINflowmin)
    
    # Relate concentration to solids flow into the treatment unit
    @model.Constraint(model.s_NTIN, model.s_Q, model.s_T, doc = "Linking solids to treatment inlet to inlet concentration")
    def TINconc_rel(m, n, q, t):
        return scale_fac*sum(model.v_F[a, t] for a in model.s_Ain[n])*m.v_C[n, q, t] == scale_fac*sum(model.v_S[a, q, t] for a in m.s_Ain[n])
    assert_units_consistent(model.TINconc_rel)
    
    #Make a total concentration variable for the treatment unit since it can only handle one component 
    @model.Constraint(model.s_NTIN, model.s_T, doc = "Linking total conc to component conc")
    def TINtotalconc(m, n, t):
        return scale_fac*sum(model.v_F[a, t] for a in model.s_Ain[n])*m.v_Ctreatin[n, t] == scale_fac*sum(sum(model.v_S[a, q, t] for a in m.s_Ain[n]) for q in m.s_Q)
    assert_units_consistent(model.TINtotalconc)
    
    #Bound on minimum total concentration
    @model.Constraint(model.s_NTIN, model.s_T, doc = "Minimum bound on inlet concentration of the treatment unit")
    def CINmin(m, n, t):
        return model.v_Ctreatin[n, t] >= 70*pyunits.g/pyunits.liter
    assert_units_consistent(model.CINmin)
    
    # Treatment Treated Water Node
    @model.Constraint(model.s_NTTW, model.s_T, doc = "Flow of Treated Water Stream")
    def NTTWflow(m,n,t):
        assert len(m.s_Aout[n]) == 1
        n1 = m.p_treatedIN[n]
        return m.v_F[m.s_Aout[n][0],t] == m.v_alphaW[n1, t]*(m.v_F[m.s_Ain[n1][0],t])
    assert_units_consistent(model.NTTWflow)
    
    model.NTTWconc = pyo.ConstraintList(doc = "Concentration of components being treated at Treated Water Node")
    for n in model.s_NTTW:
        assert len(model.s_Aout[n]) == 1
        n1 = model.p_treatedIN[n]
        for t in model.s_T:
            for q in model.s_Qalpha[n1]:
                model.NTTWconc.add(model.v_C[n,q,t] == 0)
    assert_units_consistent(model.NTTWconc)
    #We need a constraint saying salt out ot TTW is 0. Link conc with salt here too.
    
    # Treatment Concentrated Water Node
    @model.Constraint(model.s_NTCW, model.s_T, doc = "Flow of Concentrated Water Stream")
    def NTCWflow(m,n,t):
        assert len(m.s_Aout[n]) == 1
        n1 = m.p_treatedIN[n]
        return m.v_F[m.s_Aout[n][0],t] == (1-m.v_alphaW[n1, t])*(m.v_F[m.s_Ain[n1][0],t])
    assert_units_consistent(model.NTCWflow)

    model.NTCWconc = pyo.ConstraintList(doc = "Concentration of components being treated at Concentrated Water Node")
    for n in model.s_NTCW:
        assert len(model.s_Aout[n]) == 1
        n1 = model.p_treatedIN[n]
        for t in model.s_T:
            for q in model.s_Qalpha[n1]:
                model.NTCWconc.add(scale_fac*model.v_C[n,q,t]*model.v_F[model.s_Aout[n][0], t] == scale_fac*model.v_C[n1,q,t]*model.v_F[model.s_Ain[n1][0], t])
    assert_units_consistent(model.NTCWconc)
    
    #Relating outlet solids flow to concentration at the node
    @model.Constraint(model.s_NTCW|model.s_NTTW, model.s_Q, model.s_T, doc = "Outlet solids flow")
    def solids_flow(m, n, q, t):
        return scale_fac*sum(m.v_S[a, q, t] for a in m.s_Aout[n]) == scale_fac*m.v_C[n,q,t]*sum(m.v_F[a,t] for a in m.s_Aout[n])
    assert_units_consistent(model.solids_flow)
    
    # Treatment: Cases where treatment is acting as a splitter
    model.NTSrcconc = pyo.ConstraintList(doc = "Concentration of components not being treated")
    for n in model.s_NTTW | model.s_NTCW:
        assert len(model.s_Aout[n]) == 1
        n1  = model.p_treatedIN[n]
        for t in model.s_T:
            for q in (model.s_Q - model.s_Qalpha[n1]):
                model.NTSrcconc.add(model.v_C[n,q,t] == model.v_C[n1,q,t])
    assert_units_consistent(model.NTSrcconc)
            
    # Restricting the minimum concentration at the concentrated water node
    @model.Constraint(model.s_NTCW, model.s_Q, model.s_T, doc = "Minimum concentration out of concentrated water node")
    def minconccon(m,n,q,t):
        return m.v_C[n,q,t] >= m.p_Cmin[n,q]
    assert_units_consistent(model.minconccon)
    
    # Bounds on the salt in the lines
    model.saltbound = pyo.ConstraintList(doc ="Bounding salt flow in inlet of nodes")
    for a in model.s_A:
        for q in model.s_Q:
            for t in model.s_T:
                model.saltbound.add(model.v_S[a, q, t] <= model.p_Cmax*model.v_F[a, t])
    assert_units_consistent(model.saltbound)
    
    return model

if __name__ == "__main__" :
    data = get_processed_data("integrated_desalination_case_study.xlsx")
    m = build_qcp(data)
    m.TINflowmin['R02_IN', :].deactivate()
    m.TINflowmax['R02_IN', :].deactivate()
    m.CINmin['R02_IN', :].deactivate()
    
    m.v_alphaW['R02_IN', :].fix(0.4)
    
    ipopt = pyo.SolverFactory('ipopt')
    ipopt.options["max_iter"] = 10000
    ipopt.solve(m, tee= True)
    