# -*- coding: utf-8 -*-
"""
Created on Mon Feb 19 14:22:47 2024

@author: ssnaik
"""
import pyomo.environ as pyo
from pyomo.environ import units as pyunits
from pareto.integrate_desalination.network_model import build_qcp
from pareto.integrate_desalination.data_util.get_model_from_case_study import get_processed_data
from pareto.models_extra.desalination_models.mee_mvr import make_mee_mvr_model
from pareto.integrate_desalination.util.plotting import plot
def integrated_model_build(treatment_dict = {'R01_IN': 1}, pretreatment_dict = {'R02_IN': 0.4}):
    """
    Inputs
    -------
    treatment_dict - A dictionary mapping treatment site to stages in the MEE-MVR unit
    pretreatment_dict - A dictionary mapping the pretreatment site to the fixed water recovery from the site
    """
    m = pyo.ConcreteModel()
    
    #Network Model
    data = get_processed_data("integrated_desalination_case_study.xlsx")
    m.m_network = build_qcp(data)
    
    #Deactivating the minimum flow and minimum concentration constraints to the pretreatment units
    #ToDo: Identify pretreatment nodes directly from the sheet and diffrentiate them from the treatment nodes
    for n in pretreatment_dict.keys():
        m.m_network.TINflowmin[n, :].deactivate()
        m.m_network.CINmin[n, :].deactivate()
        
        #Fix recovery fraction in pretreatment node
        water_recovery = pretreatment_dict[n]
        m.m_network.v_alphaW[n, :].fix(water_recovery)
    
    
    #Solve network model for initialization
    ipopt = pyo.SolverFactory('ipopt')
    ipopt.options["max_iter"] = 10000
    ipopt.options["tol"] = 1e-4
    ipopt.solve(m.m_network, tee= True)
    
    #Set for desalination sites
    m.m_network.desal_sites = pyo.Set(initialize = treatment_dict.keys())
    
    #Treatment models in each period
    treatment_models = {}
    global_evap_capex_index = []
    for site in treatment_dict.keys():
        N_evap = treatment_dict[site]
        for i in m.m_network.s_T:
            treatment_models[site, i] = make_mee_mvr_model(N_evap=N_evap, inputs_variables=True)
            
        #Store desal site name and evaporator index for each in a 
        for n in range(N_evap):
            global_evap_capex_index.append((site, n))
    m.m_treatment = pyo.Reference(treatment_models)
    
    #Initialize treatment models
    annual_fac = {}
    for site in treatment_dict.keys():
        for t in m.m_network.s_T:
            m.m_treatment[site, t].flow_feed.fix(pyo.value(pyunits.convert(sum(m.m_network.v_F[:, site, :, t]), pyunits.liter/pyunits.s)))
            m.m_treatment[site, t].salt_feed.fix(pyo.value(m.m_network.v_Ctreatin[site,t]))
            ipopt.options['tol'] = 1e-6
            res = ipopt.solve(m.m_treatment[site, i])
            try:
                pyo.assert_optimal_termination(res)
            except:
                import pdb;pdb.set_trace()
            m.m_treatment[site, t].flow_feed.unfix()
            m.m_treatment[site, t].salt_feed.unfix()
            
            annual_fac[site] = pyo.value(m.m_treatment[site, t].annual_fac)

        
    #Global capacity variables
    #Indices for global evaporator capacity
    m.global_evaporator_capex = pyo.Var(global_evap_capex_index, domain = pyo.NonNegativeReals)
    m.global_preheater_capex = pyo.Var(m.m_network.desal_sites, domain = pyo.NonNegativeReals)
    m.global_compressor_capex = pyo.Var(m.m_network.desal_sites, domain = pyo.NonNegativeReals)
    m.CAPEX = pyo.Var(m.m_network.desal_sites, domain = pyo.NonNegativeReals)
    m.OPEX = pyo.Var(m.m_network.desal_sites, m.m_network.s_T, domain = pyo.NonNegativeReals)
    
    
    #ToDo: Global capacity variables initialization from treatment model solves
    #Initialization for global variables
    global_var_init = {}
    for site in m.m_network.desal_sites:
        N_evap = treatment_dict[site]
        for n in range(N_evap):
            global_var_init['global_evap_capex', site, n] = max(pyo.value(m.m_treatment[site, i].evaporator_capex[n]) for i in m.m_network.s_T)
            m.global_evaporator_capex[site, n] =  global_var_init['global_evap_capex', site, n]
        
        global_var_init['global_preheater_capex', site] = max(pyo.value(m.m_treatment[site, i].preheater_capex) for i in m.m_network.s_T)
        global_var_init['global_compressor_capex', site] = max(pyo.value(m.m_treatment[site, i].compressor_capex) for i in m.m_network.s_T)
        global_var_init['capex', site] =  pyo.value(annual_fac[site]*(sum(global_var_init['global_evap_capex', site, n] for n in range(N_evap))
                                                                                     + global_var_init['global_preheater_capex', site]
                                                                                     + global_var_init['global_compressor_capex', site])) 
        
        m.global_preheater_capex[site] = global_var_init['global_preheater_capex', site]
        m.global_compressor_capex[site] = global_var_init['global_compressor_capex', site] 
        m.CAPEX[site] = global_var_init['capex', site]
        for i in m.m_network.s_T:
            m.OPEX[site, i] = pyo.value(m.m_treatment[site, i].OPEX)
        
    #Linking constraints
    #Need to convert units of flow to kg/s and concentration to g/kg
    def _feed_flow_link(m, s, t):
        return m.m_treatment[s, t].flow_feed == pyunits.convert(sum(m.m_network.v_F[:, s, :, t]), pyunits.liter/pyunits.s)
    m.feed_flow_link = pyo.Constraint(m.m_network.desal_sites, m.m_network.s_T, rule = _feed_flow_link)
    
    #Link feed composition to treatment feed composition
    def _feed_conc_link(m, s, t):
        return m.m_treatment[s, t].salt_feed == m.m_network.v_Ctreatin[s,t]
    m.feed_conc_link = pyo.Constraint(m.m_network.desal_sites, m.m_network.s_T, rule = _feed_conc_link)
    
    #Link recovery fractions
    def _recovery_fractions_link(m, s, t):
        return m.m_network.v_alphaW[s, t] == m.m_treatment[s, t].water_recovery_fraction
    m.recovery_fractions_link = pyo.Constraint(m.m_network.desal_sites, m.m_network.s_T, rule = _recovery_fractions_link)
    
     
    #Global capacity constraints
    def _global_evap_area_link(m, s, i, t):
        return m.global_evaporator_capex[s, i] >= m.m_treatment[s, t].evaporator_capex[i]
    m.global_evap_area_link = pyo.Constraint(global_evap_capex_index, m.m_network.s_T, rule = _global_evap_area_link)
    
    def _global_ph_area_link(m, s, t):
        return m.global_preheater_capex[s] >= m.m_treatment[s,t].preheater_capex
    m.global_preheater_area_link = pyo.Constraint(m.m_network.desal_sites, m.m_network.s_T, rule = _global_ph_area_link)
    
    def _global_comp_capacity_link(m, s, t):
        return m.global_compressor_capex[s] >= m.m_treatment[s, t].compressor_capex
    m.global_compressor_capacity_link = pyo.Constraint(m.m_network.desal_sites, m.m_network.s_T, rule = _global_comp_capacity_link)
    
    #Calculating CAPEX based on the global variables
    def _capex_cal(m, s):
        return m.CAPEX[s] == m.m_treatment[s, 'T01'].annual_fac*(sum(m.global_evaporator_capex[s, i] for i in range(treatment_dict[s])) 
                                                                 + m.global_compressor_capex[s] 
                                                                 + m.global_preheater_capex[s])
    m.capex_con = pyo.Constraint(m.m_network.desal_sites, rule = _capex_cal)
    
    #Opex calculation 
    def _opex_cal(m, s, t):
        return m.OPEX[s, t] == m.m_treatment[s, t].OPEX 
    m.opex_con = pyo.Constraint(m.m_network.desal_sites, m.m_network.s_T, rule = _opex_cal)
    
    #Objective function
    m.m_network.obj.deactivate()
    m.m_treatment[:,:].obj.deactivate()
    
    m.objective = pyo.Objective(expr =
        1e-4*(m.m_network.obj
        + sum(m.CAPEX[s] for s in m.m_network.desal_sites)/365*m.m_network.p_dt*len(m.m_network.s_T)
        + sum(sum(m.OPEX[s, t]/365*m.m_network.p_dt for t in m.m_network.s_T) for s in m.m_network.desal_sites)))
    
    return m
if __name__ == "__main__":
    treatment_dict = {'R01_IN': 1}
    m = integrated_model_build(treatment_dict)
    
    #Solve model 
    ipopt = pyo.SolverFactory('ipopt')
    ipopt.options["mu_init"] = 1e-4
    ipopt.options["bound_push"] = 1e-4
    ipopt.options["acceptable_tol"] = 1e-4
    ipopt.options["acceptable_dual_inf_tol"] = 1e-4
    ipopt.options['tol'] = 1e-6
    ipopt.options['max_iter'] = 10000
    ipopt.solve(m, tee= True)
    
    plot(m.m_network, real_treatment_nodes = ['R01_IN'], real_disposal_nodes = ['K01','K02', 'K2_CW'], reuse_arcs = ['S02', 'N01', 'N05'])

    