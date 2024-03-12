# -*- coding: utf-8 -*-
"""
Created on Sat Jan  6 12:04:14 2024

@author: ssnaik
"""
import matplotlib.pyplot as plt
import pyomo.environ as pyo
from pyomo.environ import units as pyunits
def plot(m, plot_streams = ['PP', 'CP', 'I', 'TR', 'D','REU', 'FW', 'CD'], 
         real_treatment_nodes = [], 
         real_disposal_nodes = [], 
         reuse_arcs = [],
         savefig = False):
    if real_treatment_nodes == []:
        real_treatment_nodes = m.s_NTIN
    if real_disposal_nodes == []:
        real_disposal_nodes = m.s_ND
    
    #Flow out from production pads in time period t
    pp_t = []
    #Flow out from completion pads in time period t
    cp_t = []
    #Stored water in inventory time period t
    I_t = []
    #Water sent to desalination units
    TR_t = []
    #Water sent to disposal at time t
    D_t = []
    #Water reused for completions
    REU_t = []
    #Fresh water added to the system
    FW_t = []
    #Completions demand
    cd_t = []
    
    for stream in plot_streams:
        for t in m.s_T:
            if stream == 'PP':
                water_total = 0
                for n in m.s_NP:
                    water_total += pyo.value(pyunits.convert(sum(m.v_F[n, :,:, t]), pyunits.bbl/pyunits.day))
                pp_t.append(water_total)
            if stream == 'CP':
                water_total = 0
                for n in m.s_NC:
                    water_total += pyo.value(pyunits.convert(sum(m.v_F[n, :,:, t]), pyunits.bbl/pyunits.day))
                cp_t.append(water_total)
            if stream == 'CD':
                water_total = 0
                for n in m.s_NC:
                    water_total += pyo.value(pyunits.convert(sum(m.v_F[:, n,:, t]), pyunits.bbl/pyunits.day))
                cd_t.append(water_total)
            #Inventory stored has units in kg so to convert to bbl we divide by 119.24
            if stream == 'I':
                water_total = 0
                for n in m.s_NS:
                    water_total += pyo.value(pyunits.convert(m.v_I[n, t], pyunits.bbl))
                I_t.append(water_total)
            if stream == 'TR':
                water_total = 0
                for n in real_treatment_nodes:
                    water_total += pyo.value(pyunits.convert(sum(m.v_F[:, n,:, t]), pyunits.bbl/pyunits.day))
                TR_t.append(water_total)
            if stream == 'D':
                water_total = 0
                for n in real_disposal_nodes:
                    water_total += pyo.value(pyunits.convert(sum(m.v_F[:, n,:, t]), pyunits.bbl/pyunits.day))
                D_t.append(water_total)
            if stream =='REU':
                water_total = 0
                for n in reuse_arcs:
                    for k in m.s_NC:
                        water_total += pyo.value(pyunits.convert(sum(m.v_F[n, k,:, t]), pyunits.bbl/pyunits.day))
                REU_t.append(water_total)
            if stream == 'FW':
                water_total = 0
                for n in m.s_NW:
                    water_total += pyo.value(pyunits.convert(sum(m.v_F[n, :,:, t]), pyunits.bbl/pyunits.day))
                FW_t.append(water_total)
    time_periods = range(1, len(m.s_T) + 1)
    #Water produced in the network
    fig = plt.figure(figsize=(8, 2))
    ax = fig.add_subplot(111)
    ax.plot(time_periods, pp_t, 'b--v', label = 'production pads', linewidth= 2)
    ax.plot(time_periods, cp_t, 'g--o',label ='completion flowback', linewidth= 2)
    ax.plot(time_periods, cd_t, 'k--x',label = 'completions demand', linewidth= 2)
    ax.plot(time_periods, FW_t, 'r--', label = 'fresh water sourced', linewidth= 2)
    ax.set_title("Production and demand forecast")
    ax.set_ylabel('(bbl/day)')
    ax.set_xlabel("Time periods (weeks)")
    ax.grid()
    ax.legend()
    if savefig:
        plt.savefig('water_forecast_mee_mvr.png', dpi = 500)
    
    fig = plt.figure(figsize=(8, 2))
    ax = fig.add_subplot(111)
    ax.plot(time_periods, I_t,'b', label = 'inventory', linewidth= 2)
    ax.set_title("Inventory stored ")
    ax.set_ylabel('(bbL)')
    ax.set_xlabel("Time periods (weeks)")
    ax.grid()
    ax.legend()
    if savefig:
        plt.savefig('water_inventory_mee_mvr.png', dpi = 500)
    
   
    fig = plt.figure(figsize=(8, 2))
    ax = fig.add_subplot(111)
    ax.plot(time_periods, TR_t,'b--*',label = 'desalination', linewidth= 2)
    ax.plot(time_periods, D_t, 'r--+',label = 'disposal', linewidth= 2)
    ax.plot(time_periods, REU_t, 'g--X',label = 'reused', linewidth= 2)
    ax.set_title("Optimal flows in the network")
    ax.set_ylabel('(bbl/day)')
    ax.set_xlabel("Time periods (weeks)")
    ax.grid()
    ax.legend()
    if savefig:
        plt.savefig('water_consumed_mee_mvr.png', dpi = 500)
    
def plot_treatment_variables(m):
    alpha = []
    evap_pressure_0 = []
    
    if m.m_treatment['T01'].i == 2:
        evap_pressure_1 = []
    
    
    time_periods = range(1, len(m.m_network.s_T) + 1)
    for t in m.m_network.s_T:
        alpha.append(pyo.value(m.m_treatment[t].water_recovery_fraction))
        evap_pressure_0.append(pyo.value(m.m_treatment[t].evaporator_vapor_pressure[0]))
    fig = plt.figure(figsize=(8, 2))
    ax = fig.add_subplot(111)
    ax.plot(time_periods, alpha, linewidth= 2)
    ax.set_ylabel('Water recovery fraction')
    ax.set_xlabel("Time periods (weeks)")
    ax.set_title('Water recovery fraction from the desaliantion node')
    ax.grid()
        