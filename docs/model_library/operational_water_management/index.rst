Operational Water Management
============================


Overview
--------

Given a fixed network of pads (completion and/or production), storage tanks, water forecasts (both consumption and production), and distribution options (trucks and/or pipelines), the operational water management model provides insight into the operational costs associated with water management. The operational model allows the user to explore the tradeoff between minimizing costs (distribution, storage, treatment, disposal, etc.) and maximizing reuse water.


+---------------------------------------------------------+
| Sections                                                |
+=========================================================+
| :ref:`mathematical_notation`                            |
+---------------------------------------------------------+
| :ref:`mathematical_program_formulation`                 |
+---------------------------------------------------------+
| :ref:`operational_model_water_quality_extension`        |
+---------------------------------------------------------+
| :ref:`model_terminology`                                |
+---------------------------------------------------------+


.. _mathematical_notation:

Operational Model Mathematical Notation
---------------------------------------


**Sets**

:math:`\textcolor{blue}{t \in T}`                                           Time periods (i.e. days)

:math:`\textcolor{blue}{p \in P}`                                           Well pads

:math:`\textcolor{blue}{p \in PP}`                                       Production pads (subset of well pads P)

:math:`\textcolor{blue}{p \in CP}`                                         Completions pads (subset of well pads P)

:math:`\textcolor{blue}{f \in F}`                                           Freshwater sources

:math:`\textcolor{blue}{k \in K}`                                           Disposal sites

:math:`\textcolor{blue}{s \in S}`                                           Storage sites

:math:`\textcolor{blue}{r \in R}`                                           Treatment sites

:math:`\textcolor{blue}{o \in O}`                                           Beneficial Reuse options

:math:`\textcolor{blue}{n \in N}`                                           Network nodes

:math:`\textcolor{blue}{l \in L}`                                           Locations (superset of well pads, disposal sites, nodes, \ldots )

:math:`\textcolor{blue}{a \in A}`                                           Production tanks


:math:`\textcolor{blue}{(p,p) \in PCA}`                                   Production-to-completions pipeline arcs

:math:`\textcolor{blue}{(p,n) \in PNA}`                                 Production-to-node pipeline arcs

:math:`\textcolor{blue}{(p,p) \in PPA}`                                 Production-to-production pipeline arcs

:math:`\textcolor{blue}{(p,n) \in CNA}`                                   Completions-to-node pipeline arcs

:math:`\textcolor{blue}{(p,p) \in CCA}`                                   Completions-to-completions pipeline arcs

:math:`\textcolor{blue}{(n,n) \in NNA}`                                 Node-to-node pipeline arcs

:math:`\textcolor{blue}{(n,p) \in NCA}`                                 Node-to-completions pipeline arcs

:math:`\textcolor{blue}{(n,k) \in NKA}`                                   Node-to-disposal pipeline arcs

:math:`\textcolor{blue}{(n,s) \in NSA}`                                   Node-to-storage pipeline arcs

:math:`\textcolor{blue}{(n,r) \in NRA}`                                 Node-to-treatment pipeline arcs

:math:`\textcolor{blue}{(n,o) \in NOA}`                                   Node-to-beneficial reuse pipeline arcs

:math:`\textcolor{blue}{(f,p) \in FCA}`                                   Freshwater-to-completions pipeline arcs

:math:`\textcolor{blue}{(r,n) \in RNA}`                                   Treatment-to-node pipeline arcs

:math:`\textcolor{blue}{(r,p) \in RCA}`                                   Treatment-to-completions pipeline arcs

:math:`\textcolor{blue}{(r,k) \in RKA}`                                   Treatment-to-disposal pipeline arcs

:math:`\textcolor{blue}{(s,n) \in SNA}`                                   Storage-to-node pipeline arcs

:math:`\textcolor{blue}{(s,p) \in SCA}`                                   Storage-to-completions pipeline arcs

:math:`\textcolor{blue}{(s,k) \in SKA}`                                   Storage-to-disposal pipeline arcs

:math:`\textcolor{blue}{(s,r) \in SRA}`                                   Storage-to-treatment pipeline arcs

:math:`\textcolor{blue}{(s,o) \in SOA}`                                   Storage-to-beneficial reuse pipeline arcs

:math:`\textcolor{blue}{(l,\tilde{l}) \in LLA}`     All valid pipeline arcs

:math:`\textcolor{blue}{(p,p) \in PCT}`                                   Production-to-completions trucking arcs

:math:`\textcolor{blue}{(f,c) \in FCT}`                                 Freshwater-to-completions trucking arcs

:math:`\textcolor{blue}{(p,k) \in PKT}`                                   Production-to-disposal trucking arcs

:math:`\textcolor{blue}{(p,s) \in PST}`                                 Production-to-storage trucking arcs

:math:`\textcolor{blue}{(p,r) \in PRT}`                                   Production-to-treatment trucking arcs

:math:`\textcolor{blue}{(p,o) \in POT}`                                   Production-to-beneficial reuse trucking arcs

:math:`\textcolor{blue}{(p,k) \in CKT}`                                   Completions-to-disposal trucking arcs

:math:`\textcolor{blue}{(p,s) \in CST}`                                   Completions-to-storage trucking arcs

:math:`\textcolor{blue}{(p,r) \in CRT}`                                 Completions-to-treatment trucking arcs

:math:`\textcolor{blue}{(p,p) \in CCT}`                                   Completions-to-completions trucking arcs (flowback reuse)

:math:`\textcolor{blue}{(s,p) \in SCT}`                                 Storage-to-completions trucking arcs

:math:`\textcolor{blue}{(s,k) \in SKT}`                                 Storage-to-disposal trucking arcs

:math:`\textcolor{blue}{(r,k) \in RKT}`                                   Treatment-to-disposal trucking arcs

:math:`\textcolor{blue}{(l,\tilde{l}) \in LLT}`     All valid trucking arcs

:math:`\textcolor{blue}{(p,a) \in PAL}`                                   Pad-to-tank links



**Continuous Variables**

:math:`\textcolor{red}{F_{l,\tilde{l},t}^{Piped}}` =                           Produced water piped from one location to another location

:math:`\textcolor{red}{F_{l,\tilde{l},t}^{Trucked}}` =                           Produced water trucked from one location to another location

:math:`\textcolor{red}{F_{f,p,t}^{Sourced}}` =                         Fresh water sourced from source to completions

:math:`\textcolor{red}{F_{p,t}^{PadStorageIn}}` =                       Water put into completions pad storage

:math:`\textcolor{red}{F_{p,t}^{PadStorageOut}}` =                       Water removed from completions pad storage

:math:`\textcolor{red}{F_{r,t}^{TreatmentDestination}}` =               Water delivered to treatment site

:math:`\textcolor{red}{F_{r,t}^{UnusedTreatedWater}}` =                   Water leftover from the treatment process

:math:`\textcolor{red}{F_{k,t}^{DisposalDestination}}` =               Water injected at disposal site

:math:`\textcolor{red}{F_{o,t}^{BeneficialReuseDestination}}` =           Water delivered to beneficial reuse site


**If the production tanks are separate, water level and water drainage are tracked at each individual production tank:**

    :math:`\textcolor{red}{F_{p,a,t}^{Drain}}` =                       Produced water drained from production tank

    :math:`\textcolor{red}{L_{p,a,t}^{ProdTank}}` =                   Water level in production tank at the end of time period t

**Otherwise, if the production tanks are equalized, the water level and water drainage can be aggregated to a pad level:**

    :math:`\textcolor{red}{F_{p,t}^{Drain}}` =                           Produced water drained from equalized production tanks

    :math:`\textcolor{red}{L_{p,t}^{ProdTank}}` =                       Water level in equalized production tanks at the end of time period t


:math:`\textcolor{red}{B_{p,t}^{Production}}` =                       Produced water for transport from pad

:math:`\textcolor{red}{L_{s,t}^{Storage}}` =                           Water level in storage site at the end of time period t


:math:`\textcolor{red}{L_{p,t}^{PadStorage}}` =                           Water level in completions pad storage  at the end of time period t

:math:`\textcolor{red}{C_{l,\tilde{l},t}^{Piped}}` =                           Cost of piping produced water from one location to another location

:math:`\textcolor{red}{C_{l,\tilde{l},t}^{Trucked}}` =                           Cost of trucking produced water from one location to another location

:math:`\textcolor{red}{C_{f,p,t}^{Sourced}}` =                           Cost of sourcing fresh water from source to completions pad

:math:`\textcolor{red}{C_{k,t}^{Disposal}}` =                          Cost of injecting produced water at disposal site

:math:`\textcolor{red}{C_{r,t}^{Treatment}}` =                           Cost of treating produced water at treatment site

:math:`\textcolor{red}{C_{p,t}^{CompletionsReuse}}` =                  Cost of reusing produced water at completions site

:math:`\textcolor{red}{C_{s,t}^{Storage}}` =                           Cost of storing produced water at storage site (incl. treatment)

:math:`\textcolor{red}{R_{s,t}^{Storage}}` =                           Credit for retrieving stored produced water from storage site

:math:`\textcolor{red}{C_{p,t}^{PadStorage}}` =                        Cost of storing produced water at completions pad storage

:math:`\textcolor{red}{C^{TotalSourced}}` =                            Total cost of sourcing freshwater

:math:`\textcolor{red}{C^{TotalDisposal}}` =                           Total cost of injecting produced water

:math:`\textcolor{red}{C^{TotalTreatment}}` =                            Total cost of treating produced water

:math:`\textcolor{red}{C^{TotalCompletionsReuse}}` =                   Total cost of reusing produced water

:math:`\textcolor{red}{C^{TotalPiping}}` =                                Total cost of piping produced water

:math:`\textcolor{red}{C^{TotalStorage}}` =                            Total cost of storing produced water

:math:`\textcolor{red}{C^{TotalPadStorage}}` =                            Total cost of storing produced water at completions pad

:math:`\textcolor{red}{C^{TotalTrucking}}` =                           Total cost of trucking produced water

:math:`\textcolor{red}{C^{Slack}}` =                                   Total cost of slack variables

:math:`\textcolor{red}{R^{TotalStorage}}` =                            Total credit for withdrawing produced water


:math:`\textcolor{red}{S_{p,t}^{FracDemand}}` =                         Slack variable to meet the completions water demand

:math:`\textcolor{red}{S_{p,t}^{Production}}` =                        Slack variable to process produced water production

:math:`\textcolor{red}{S_{p,t}^{Flowback}}` =                            Slack variable to process flowback water production

:math:`\textcolor{red}{S_{l,\tilde{l}}^{Pipeline Capacity}}` =                 Slack variable to provide necessary pipeline capacity

:math:`\textcolor{red}{S_{s}^{StorageCapacity}}` =                     Slack variable to provide necessary storage capacity

:math:`\textcolor{red}{S_{k}^{DisposalCapacity}}` =                    Slack variable to provide necessary disposal capacity

:math:`\textcolor{red}{S_{r}^{TreatmentCapacity}}` =                    Slack variable to provide necessary treatment capacity

:math:`\textcolor{red}{S_{o}^{BeneficialReuseCapacity}}` =             Slack variable to provide necessary beneficial reuse capacity



**Binary Variables**


:math:`\textcolor{red}{y_{l,\tilde{l},t}^{Flow}}` =                            Directional flow between two locations

:math:`\textcolor{red}{z_{p,t}^{PadStorage}}` =                        Completions pad storage use


**Parameters**

:math:`\textcolor{green}{y_{p,t}^{Completions}}` =                        Completions demand at a completions site in a time period

**If the production tanks are separate, water level and water drainage are tracked at each individual production tank:**

    :math:`\textcolor{green}{\beta_{p,a,t}^{Production}}` =                Produced water supply forecast for a production pad

    :math:`\textcolor{green}{\beta_{p,a,t}^{Flowback}}` =                Flowback water supply forecast for a completions pad

    :math:`\textcolor{green}{\sigma_{p,a}^{ProdTank}}` =                       Production tank capacity

    :math:`\textcolor{green}{\lambda_{p,a}^{ProdTank}}` =                        Initial water level in production tank

**Otherwise, if the production tanks are equalized, the water level and water drainage can be aggregated to a pad level:**

    :math:`\textcolor{green}{\beta_{p,t}^{Production}}` =                   Produced water supply forecast for a production pad

    :math:`\textcolor{green}{\beta_{p,t}^{Flowback}}` =                           Flowback supply forecast for a completions pad

    :math:`\textcolor{green}{\sigma_{p}^{ProdTank}}` =                       Combined capacity of equalized production tanks

    :math:`\textcolor{green}{\lambda_{p}^{ProdTank}}` =                      Initial water level in equalized production tanks


:math:`\textcolor{green}{\sigma_{l,\tilde{l}}^{Pipeline}}` =                           Daily pipeline capacity between two locations

:math:`\textcolor{green}{\sigma_{k}^{Disposal}}` =                           Daily disposal capacity at a disposal site

:math:`\textcolor{green}{\sigma_{s}^{Storage}}` =                           Storage capacity at a storage site

:math:`\textcolor{green}{\sigma_{p,t}^{PadStorage}}` =                      Storage capacity at completions site

:math:`\textcolor{green}{\sigma_{r}^{Treatment}}` =                         Daily treatment capacity at a treatment site

:math:`\textcolor{green}{\sigma_{o}^{BeneficialReuse}}` =                   Daily reuse capacity at a beneficial reuse site

:math:`\textcolor{green}{\sigma_{f,t}^{Freshwater}}` =                      Daily freshwater sourcing capacity at freshwater source

:math:`\textcolor{green}{\sigma_{p}^{Offloading,Pad}}` =                    Daily truck offloading sourcing capacity per pad

:math:`\textcolor{green}{\sigma_{s}^{Offloading,Storage}}` =                   Daily truck offloading sourcing capacity per storage site


:math:`\textcolor{green}{\sigma_{p}^{Processing,Pad}}` =                    Daily processing (e.g. clarification) capacity per pad

:math:`\textcolor{green}{\sigma_{s}^{Processing,Storage}}` =                Daily processing (e.g. clarification) capacity at storage site

:math:`\textcolor{green}{\varepsilon_{r,w}^{Treatment}}` =                       Treatment efficiency for water quality component at treatment site

:math:`\textcolor{green}{\delta^{Truck}}` =  Truck Capacity

:math:`\textcolor{green}{\tau_{p,p}^{Trucking}}` =                        Drive time between two pads

:math:`\textcolor{green}{\tau_{p,k}^{Trucking}}` =                           Drive time from a pad to a disposal site

:math:`\textcolor{green}{\tau_{p,s}^{Trucking}}` =                           Drive time from a pad to a storage site

:math:`\textcolor{green}{\tau_{p,r}^{Trucking}}` =                           Drive time from a pad to a treatment site

:math:`\textcolor{green}{\tau_{p,o}^{Trucking}}` =                        Drive time from a pad to a beneficial reuse site

:math:`\textcolor{green}{\tau_{s,p}^{Trucking}}` =                           Drive time from a storage site to a completions site

:math:`\textcolor{green}{\tau_{s,k}^{Trucking}}` =                        Drive time from a storage site to a disposal site

:math:`\textcolor{green}{\tau_{r,k}^{Trucking}}` =                        Drive time from a treatment site to a disposal site

:math:`\textcolor{green}{\lambda_{s}^{Storage}}` =                           Initial storage level at storage site

:math:`\textcolor{green}{\lambda_{p}^{PadStorage}}` =                        Initial storage level at completions site

:math:`\textcolor{green}{\theta_{p}^{PadStorage}}` =                        Terminal storage level at completions site

:math:`\textcolor{green}{\lambda_{l,\tilde{l}}^{Pipeline}}` =                        Pipeline segment length

:math:`\textcolor{green}{\pi_{k}^{Disposal}}` =                          Disposal operational cost

:math:`\textcolor{green}{\pi_{r}^{Treatment}}` =                           Treatment operational cost (may include "clean brine")

:math:`\textcolor{green}{\pi_{p}^{CompletionReuse}}` =                   Completions reuse operational cost

:math:`\textcolor{green}{\pi_{s}^{Storage}}` =                           Storage deposit operational cost

:math:`\textcolor{green}{\pi_{p,t}^{PadStorage}}` =                      Completions pad operational cost

:math:`\textcolor{green}{\rho_{s}^{Storage}}` =                           Storage withdrawal operational credit

:math:`\textcolor{green}{\pi_{l,\tilde{l}}^{Pipeline}}` =                           Pipeline operational cost

:math:`\textcolor{green}{\pi_{l}^{Trucking}}` =                          Trucking hourly cost (by source)

:math:`\textcolor{green}{\pi_{f}^{Sourcing}}` =                          Fresh sourcing cost (does not include transportation cost)


:math:`\textcolor{green}{M^{Flow}}` =                                  Big-M flow parameter

:math:`\textcolor{green}{\psi^{FracDemand}}` =                            Slack cost parameter

:math:`\textcolor{green}{\psi^{Production}}` =                            Slack cost parameter

:math:`\textcolor{green}{\psi^{Flowback}}` =                              Slack cost parameter

:math:`\textcolor{green}{\psi^{PipelineCapacity}}` =                      Slack cost parameter

:math:`\textcolor{green}{\psi^{StorageCapacity}}` =                         Slack cost parameter

:math:`\textcolor{green}{\psi^{DisposalCapacity}}` =                      Slack cost parameter

:math:`\textcolor{green}{\psi^{TreamentCapacity}}` =                      Slack cost parameter

:math:`\textcolor{green}{\psi^{BeneficialReuseCapacity}}` =                 Slack cost parameter



.. _mathematical_program_formulation:

Operational Model Mathematical Program Formulation
---------------------------------------------------

The default objective function for this produced water operational model is to minimize costs, which includes operational costs associated with procurement of fresh water, the cost of disposal, trucking and piping produced water between well pads and treatment facilities, and the cost of storing, treating and reusing produced water. A credit for using treated water is also considered, and additional slack variables are included to facilitate the identification of potential issues with input data.


**Objective**

.. math::

    \min \ \textcolor{red}{C^{TotalSourced}}+\textcolor{red}{C^{TotalDisposal}}+\textcolor{red}{C^{TotalTreatment}}+\textcolor{red}{C^{TotalCompletionsReuse}}+

        \textcolor{red}{C^{TotalPiping}}+\textcolor{red}{C^{TotalStorage}}+\textcolor{red}{C^{TotalPadStorage}}+ \textcolor{red}{C^{TotalTrucking}}+\textcolor{red}{C^{Slack}-R^{TotalStorage}}


**Completions Pad Demand Balance:** :math:`\forall p \in CP, t \in T`

.. math::

    \textcolor{green}{\gamma_{p,t}^{Completions}}
        = \sum_{l \in (L-F) | (l, p) \in LLA}\textcolor{red}{F_{l,p,t}^{Piped}}
        + \sum_{f \in F | (f, p) \in LLA}\textcolor{red}{F_{f,p,t}^{Sourced}}
        + \sum_{l \in L | (l, p) \in LLT}\textcolor{red}{F_{l,p,t}^{Trucked}}

        + \textcolor{red}{F_{p,t}^{PadStorageOut}} - \textcolor{red}{F_{p,t}^{PadStorageIn}} + \textcolor{red}{S_{p,t}^{FracDemand}}



**Completions Pad Storage Balance:** :math:`\forall p \in CP, t \in T`

This constraint sets the storage level at the completions pad. For each completions pad and for each time period, completions pad storage is equal to storage in last time period plus water put in minus water removed. If it is the first time period, the pad storage is the initial pad storage.


.. math::

    \textcolor{red}{L_{p,t}^{PadStorage}} = \textcolor{green}{\lambda_{p,t=1}^{PadStorage}}+\textcolor{red}{L_{p,t-1}^{PadStorage}}+\textcolor{red}{F_{p,t}^{StorageIn}}-\textcolor{red}{F_{p,t}^{StorageOut}}



**Completions Pad Storage Capacity:** :math:`\forall p \in CP, t \in T`

The storage at each completions pad must always be at or below its capacity in every time period.

.. math::

    \textcolor{red}{L_{p,t}^{PadStorage}}\leq \textcolor{red}{z_{p,t}^{PadStorage}} \cdot \textcolor{green}{\sigma_{p,t}^{PadStorage}}

**Terminal Completions Pad Storage Level:** :math:`\forall p \in CP, t \in T`

.. math::

    \textcolor{red}{L_{p,t=T}^{PadStorage}}\leq \textcolor{green}{\theta_{p}^{PadStorage}}

The storage in the last period must be at or below its terminal storage level.



**Freshwater Sourcing Capacity:** :math:`\forall f \in F, t \in T`

For each freshwater source and each time period, the outgoing water from the freshwater source is below the freshwater capacity.

.. math::

      \sum\nolimits_{(f,p)\in FCA}\textcolor{red}{F_{l,\tilde{l},t}^{Sourced}} +\sum\nolimits_{(f,p)\in FCT}\textcolor{red}{F_{l,\tilde{l},t}^{Trucked}} \leq \textcolor{green}{\sigma_{f,t}^{Freshwater}}



**Completions Pad Truck Offloading Capacity:** :math:`\forall p \in CP, t \in T`

For each completions pad and time period, the volume of water being trucked into the completions pad must be below the trucking offloading capacity.

.. math::

    \sum_{l \in L | (l, p) \in LLT}\textcolor{red}{F_{l,p,t}^{Trucked}}
        \leq \textcolor{green}{\sigma_{p}^{Offloading,Pad}}



**Completions Pad Processing Capacity:**

For each completions pad and time period, the volume of water (excluding freshwater) coming in must be below the processing limit.

.. math::

    \sum\nolimits_{(n,p)\in NCA}\textcolor{red}{F_{l,\tilde{l},t}^{Piped}} +\sum\nolimits_{(p,p)\in PCA}\textcolor{red}{F_{l,\tilde{l},t}^{Piped}} +\sum\nolimits_{(s,p)\in SCA}\textcolor{red}{F_{l,\tilde{l},t}^{Piped}}

        +\sum\nolimits_{(p,c)\in CCA}\textcolor{red}{F_{l,\tilde{l},t}^{Piped}} +\sum\nolimits_{(r,p)\in RCA}\textcolor{red}{F_{l,\tilde{l},t}^{Piped}} +\sum\nolimits_{(p,p)\in PCT}\textcolor{red}{F_{l,\tilde{l},t}^{Trucked}}

        +\sum\nolimits_{(s,p)\in SCT}\textcolor{red}{F_{l,\tilde{l},t}^{Trucked}} +\sum\nolimits_{(p,p)\in CCT}\textcolor{red}{F_{l,\tilde{l},t}^{Trucked}} \leq \textcolor{green}{\sigma_{p}^{Processing,Pad}}


.. note:: This constraint has not actually been implemented yet.



**Storage Site Truck Offloading Capacity:** :math:`\forall s \in S, t \in T`

For each storage site and each time period, the volume of water being trucked into the storage site must be below the trucking offloading capacity for that storage site.

.. math::

    \sum_{l \in L | (l, s) \in LLT}\textcolor{red}{F_{l,s,t}^{Trucked}}
        \leq \textcolor{green}{\sigma_{s}^{Offloading,Storage}}


**Storage Site Processing Capacity:** :math:`\forall s \in S, t \in T`

For each storage site and each time period, the volume of water being trucked into the storage site must be less than the processing capacity for that storage site.

.. math::

    \sum_{l \in L | (l, s) \in LLA}\textcolor{red}{F_{l,s,t}^{Piped}}
        + \sum_{l \in L | (l, s) \in LLT}\textcolor{red}{F_{l,s,t}^{Trucked}}
        \leq \textcolor{green}{\sigma_{s}^{Processing,Storage}}


**Production Tank Balance:**

If there are individual production tanks, the water level must be tracked at each tank. The water level at a given tank at the end of each period is equal to the water level at the previous period plus the flowback supply forecast at the pad minus the water that is drained.  If it is the first period, it is equal to the initial water level.

For individual production tanks: :math:`\forall (p,a) \in PAL, t \in T`

For :math:`t = 1`:

.. math::
    \textcolor{red}{L_{p,a,t}^{ProdTank}} = \textcolor{green}{\lambda_{p,a,t=1}^{ProdTank}}+\textcolor{green}{\beta_{p,a,t}^{Production}}+\textcolor{green}{\beta_{p,a,t}^{Flowback}}-\textcolor{red}{F_{p,a,t}^{Drain}}

For :math:`t > 1`:

.. math::
    \textcolor{red}{L_{p,a,t}^{ProdTank}} = \textcolor{red}{L_{p,a,t-1}^{ProdTank}}+\textcolor{green}{\beta_{p,a,t}^{Production}}+\textcolor{green}{\beta_{p,a,t}^{Flowback}}-\textcolor{red}{F_{p,a,t}^{Drain}}

For equalized production tanks: :math:`\forall p \in P, t \in T`

For :math:`t = 1`:

.. math::
    \textcolor{red}{L_{p,t}^{ProdTank}} = \textcolor{green}{\lambda_{p,t=1}^{ProdTank}}+\textcolor{green}{\beta_{p,t}^{Production}}+\textcolor{green}{\beta_{p,t}^{Flowback}}-\textcolor{red}{F_{p,t}^{Drain}}

For :math:`t > 1`:

.. math::
    \textcolor{red}{L_{p,t}^{ProdTank}} = \textcolor{red}{L_{p,t-1}^{ProdTank}}+\textcolor{green}{\beta_{p,t}^{Production}}+\textcolor{green}{\beta_{p,t}^{Flowback}}-\textcolor{red}{F_{p,t}^{Drain}}

**Production Tank Capacity:**

The water level at the production tanks must always be below the production tank capacity.

For individual production tanks: :math:`\forall (p,a) \in PAL, t \in T`

.. math::

    \textcolor{red}{L_{p,a,t}^{ProdTank}}\leq \textcolor{green}{\sigma_{p,a}^{ProdTank}}


For equalized production tanks: :math:`\forall p \in P, t \in T`

.. math::

    \textcolor{red}{L_{p,t}^{ProdTank}}\leq \textcolor{green}{\sigma_{p}^{ProdTank}}



**Terminal Production Tank Level Balance:**

The water level at the production tanks in the final time period must be below the terminal production tank water level parameter.

For individual production tanks: :math:`\forall (p,a) \in PAL, t \in T`

.. math::

    \textcolor{red}{L_{p,a,t=T}^{ProdTank}}\leq \textcolor{green}{\lambda_{p,a,t=1}^{ProdTank}}


For equalized production tanks: :math:`\forall p \in P,t \in T`

.. math::

    \textcolor{red}{L_{p,t=T}^{ProdTank}}\leq \textcolor{green}{\lambda_{p,t=1}^{ProdTank}}



**Tank-to-Pad Production Balance:**

If there are individual production tanks, the water drained across all tanks at the completions pad must be equal to the produced water for transport at the pad.

For individual production tanks: :math:`\forall p \in P, t \in T`

.. math::

    \sum\nolimits_{(p,a)\in PAL}\textcolor{red}{F_{p,a,t}^{Drain}} =\textcolor{red}{B_{p,t}^{Production}}


Otherwise, if the production tanks are equalized, the production water drained is measured on an aggregated production pad level.

For equalized production tanks: :math:`\forall p \in P, t \in T`

.. math::

    \textcolor{red}{F_{p,t}^{Drain}}=\textcolor{red}{B_{p,t}^{Production}}

.. note:: The constraint proposed above is not necessary but included to facilitate switching between (1) an equalized production tank version and (2) a non-equalized production tank version.



**Production Pad Supply Balance:** :math:`\forall p \in PP, t \in T`

All produced water must be accounted for. For each production pad and for each time period, the volume of outgoing water must be equal to the produced water transported out of the production pad.

.. math::

    \textcolor{red}{B_{p,t}^{Production}}
        = \sum_{l \in L | (p, l) \in LLA}\textcolor{red}{F_{p,l,t}^{Piped}}
        + \sum_{l \in L | (p, l) \in LLT}\textcolor{red}{F_{p,l,t}^{Trucked}}
        + \textcolor{red}{S_{p,t}^{Production}}

**Completions Pad Supply Balance (i.e. Flowback Balance):** :math:`\forall p \in CP, t \in T`

All flowback water must be accounted for.  For each completions pad and for each time period, the volume of outgoing water must be equal to the forecasted flowback produced water for the completions pad.

.. math::

    \textcolor{red}{B_{p,t}^{Production}}
        = \sum_{l \in L | (p, l) \in LLA}\textcolor{red}{F_{p,l,t}^{Piped}}
        + \sum_{l \in L | (p, l) \in LLT}\textcolor{red}{F_{p,l,t}^{Trucked}}
        + \textcolor{red}{S_{p,t}^{Flowback}}


**Network Node Balance:** :math:`\forall n \in N, t \in T`

Flow balance constraint (i.e., inputs are equal to outputs). For each pipeline node and for each time period, the volume water into the node is equal to the volume of water out of the node.

.. math::

     \sum_{l \in L | (l, n) \in LLA}\textcolor{red}{F_{l,n,t}^{Piped}}
            = \sum_{l \in L | (n, l) \in LLA}\textcolor{red}{F_{n,l,t}^{Piped}}



**Bi-Directional Flow:** :math:`\forall (l,\tilde{l}), \ t \in T` such that :math:`(l,\tilde{l}) \in LLA`, :math:`(\tilde{l}, l) \in LLA`, :math:`l \in L-F-O`, and :math:`\tilde{l} \in L - F`

There can only be flow in one direction for a given pipeline arc in a given time period.

Flow is only allowed in a given direction if the binary indicator for that direction is "on".

.. math::

    \textcolor{red}{y_{l,\tilde{l},t}^{Flow}}+\textcolor{red}{y_{\tilde{l},l,t}^{Flow}} = 1

.. math::

    \textcolor{red}{F_{l,\tilde{l},t}^{Piped}} \leq \textcolor{red}{y_{l,\tilde{l},t}^{Flow}} \cdot \textcolor{green}{M^{Flow}}



**Storage Site Balance:** :math:`\forall s \in S, t \in T`

For each storage site and for each time period, if it is the first time period, the storage level is the initial storage. Otherwise, the storage level is equal to the storage level in the previous time period plus water inputs minus water outputs.

For :math:`t = 1`:

.. math::

    \textcolor{red}{L_{s,t}^{Storage}}
        = \textcolor{green}{\lambda_{s,t=1}^{Storage}}
        + \sum_{l \in L | (l, s) \in LLA}\textcolor{red}{F_{l,s,t}^{Piped}}
        + \sum_{l \in L | (l, s) \in LLT}\textcolor{red}{F_{l,s,t}^{Trucked}}
        - \sum_{l \in L | (s, l) \in LLA}\textcolor{red}{F_{s,l,t}^{Piped}}
        - \sum_{l \in L | (s, l) \in LLT}\textcolor{red}{F_{s,l,t}^{Trucked}}

For :math:`t > 1`:

.. math::

    \textcolor{red}{L_{s,t}^{Storage}}
        = \textcolor{red}{L_{s,t-1}^{Storage}}
        + \sum_{l \in L | (l, s) \in LLA}\textcolor{red}{F_{l,s,t}^{Piped}}
        + \sum_{l \in L | (l, s) \in LLT}\textcolor{red}{F_{l,s,t}^{Trucked}}
        - \sum_{l \in L | (s, l) \in LLA}\textcolor{red}{F_{s,l,t}^{Piped}}
        - \sum_{l \in L | (s, l) \in LLT}\textcolor{red}{F_{s,l,t}^{Trucked}}

**Pipeline Capacity:**

:math:`\forall (l,\tilde{l}) \in LLA, t \in T`

.. math::

    \textcolor{red}{F_{l,\tilde{l},t}^{Piped}} \leq \textcolor{red}{F_{l,\tilde{l},[t]}^{Capacity}}

**Pipeline Capacity Construction/Expansion:** :math:`\forall (l,\tilde{l}) \in LLA, [{t \in T}]`

:math:`\forall(l,\tilde{l})` if :math:`(l,\tilde{l}) \in LLA` and :math:`(\tilde{l}, l) \in LLA`:

.. math::

    \textcolor{red}{F_{l,\tilde{l},[t]}^{Capacity}}
        = \textcolor{green}{\sigma_{l,\tilde{l}}^{Pipeline}}
        + \textcolor{green}{\sigma_{\tilde{l},l}^{Pipeline}}
        +\sum_{d \in D}\textcolor{green}{\delta_{d}^{Pipeline}} \cdot (\textcolor{red}{y_{l,\tilde{l},d}^{Pipeline}}+\textcolor{red}{y_{\tilde{l},l,d}^{Pipeline}} )
        +\textcolor{red}{S_{l,\tilde{l}}^{PipelineCapacity}}


:math:`\forall(l,\tilde{l})` if :math:`(l,\tilde{l}) \in LLA` and :math:`(\tilde{l}, l) \not\in LLA`:

.. math::

    \textcolor{red}{F_{l,\tilde{l},[t]}^{Capacity}}
        = \textcolor{green}{\sigma_{l,\tilde{l}}^{Pipeline}}
        +\sum_{d \in D}\textcolor{green}{\delta_{d}^{Pipeline}} \cdot \textcolor{red}{y_{l,\tilde{l},d}^{Pipeline}}
        +\textcolor{red}{S_{l,\tilde{l}}^{PipelineCapacity}}



**Storage Capacity:**

The total stored water in a given time period must be less than the capacity. If the storage capacity limits the feasibility, the slack variable will be nonzero, and the storage capacity will be increased to allow a feasible solution.

:math:`\forall s \in S,[t \in T]`

.. math::

    \textcolor{red}{X_{s,[t]}^{Capacity}} = \textcolor{green}{\sigma_{s}^{Storage}}+\textcolor{red}{S_{s}^{StorageCapacity}}

:math:`\forall s \in S, t \in T`

.. math::

    \textcolor{red}{L_{s,t}^{Storage}}\leq \textcolor{red}{X_{s,[t]}^{Capacity}}



**Disposal Capacity:**

The total disposed water in a given time period must be less than the capacity. If the disposal capacity limits the feasibility, the slack variable will be nonzero, and the disposal capacity will be increased to allow a feasible solution.

:math:`\forall k \in K, [t \in T]`

.. math::

    \textcolor{red}{D_{k,[t]}^{Capacity}} = \textcolor{green}{\sigma_{k}^{Disposal}}+\textcolor{red}{S_{k}^{DisposalCapacity}}

:math:`\forall k \in K, t \in T`

.. math::

    \sum_{l \in L | (l, k) \in LLA}\textcolor{red}{F_{l,k,t}^{Piped}}
        + \sum_{l \in L | (l, k) \in LLT}\textcolor{red}{F_{l,k,t}^{Trucked}} \leq \textcolor{red}{D_{k,[t]}^{Capacity}}

:math:`\forall k \in K, t \in T`

.. math::

    \textcolor{red}{F_{k,t}^{DisposalDestination}}
        = \sum_{l \in L | (l, k) \in LLA}\textcolor{red}{F_{l,k,t}^{Piped}}
        + \sum_{l \in L | (l, k) \in LLT}\textcolor{red}{F_{l,k,t}^{Trucked}}



**Treatment Capacity:**

The total treated water in a given time period must be less than the capacity. If the treatment capacity limits the feasibility, the slack variable will be nonzero, and the treatment capacity will be increased to allow a feasible solution.

:math:`\forall r \in R, t \in T`

.. math::

    \sum_{l \in L | (l, r) \in LLA}\textcolor{red}{F_{l,r,t}^{Piped}}
        + \sum_{l \in L | (l, r) \in LLT}\textcolor{red}{F_{l,r,t}^{Trucked}} \leq \textcolor{green}{\sigma_{r}^{Treatment}}+\textcolor{red}{S_{r}^{TreatmentCapacity}}

:math:`\forall r \in R, t \in T`

**Treatment Destination Deliveries:**
The total water delivered to a treatment site is the sum of all piped and trucked flows into the site.

.. math::

    \sum_{l \in L | (l, r) \in LLA}\textcolor{red}{F_{l,r,t}^{Piped}}
        + \sum_{l \in L | (l, r) \in LLT}\textcolor{red}{F_{l,r,t}^{Trucked}}=\textcolor{red}{F_{r,t}^{TreatmentDestination}}


**Beneficial Reuse Capacity:**

The total water for beneficial reuse in a given time period must be less than the capacity. If the beneficial reuse capacity limits the feasibility, the slack variable will be nonzero, and the beneficial reuse capacity will be increased to allow a feasible solution.

:math:`\forall o \in O, t \in T`

.. math::

    \sum_{l \in L | (l, o) \in LLA}\textcolor{red}{F_{l,o,t}^{Piped}}
        + \sum_{l \in L | (l, o) \in LLT}\textcolor{red}{F_{l,o,t}^{Trucked}} \leq \textcolor{green}{\sigma_{o}^{Reuse}}+\textcolor{red}{S_{o}^{ReuseCapacity}}

:math:`\forall o \in O, t \in T`

.. math::

        \sum_{l \in L | (l, o) \in LLA}\textcolor{red}{F_{l,o,t}^{Piped}}
        + \sum_{l \in L | (l, o) \in LLT}\textcolor{red}{F_{l,o,t}^{Trucked}}=\textcolor{red}{F_{o,t}^{BeneficialReuseDestination}}


**Fresh Sourcing Cost:**  :math:`\forall f \in F, p \in CP, t \in T`

For each freshwater source, for each completions pad, and for each time period, the freshwater sourcing cost is equal to all output from the freshwater source times the freshwater sourcing cost.

.. math::

    \textcolor{red}{C_{f,p,t}^{Sourced}} =(\textcolor{red}{F_{f,p,t}^{Sourced}}+\textcolor{red}{F_{f,p,t}^{Trucked}}) \cdot \textcolor{green}{\pi_{f}^{Sourcing}}

    \textcolor{red}{C^{TotalSourced}} = \sum\nolimits_{\forall t\in T}\sum\nolimits_{f \in F, p \in CP}\textcolor{red}{C_{f,p,t}^{Sourced}}



**Disposal Cost:** :math:`\forall k \in K, t \in T`

For each disposal site, for each time period, the disposal cost is equal to all water moved into the disposal site multiplied by the operational disposal cost. Total disposal cost is the sum of disposal costs over all time periods and all disposal sites.

.. math::

       \textcolor{red}{C_{k,t}^{Disposal}} = (\sum\nolimits_{(l,k)\in LLA}\textcolor{red}{F_{l,k,t}^{Piped}}+\sum\nolimits_{(l,k)\in LLT}\textcolor{red}{F_{l,k,t}^{Trucked}}) \cdot \textcolor{green}{\pi_{k}^{Disposal}}

       \textcolor{red}{C^{TotalDisposal}} = \sum\nolimits_{\forall t\in T}\sum\nolimits_{k\in K}\textcolor{red}{C_{k,t}^{Disposal}}



**Treatment Cost:** :math:`\forall r \in R, t \in T`

For each treatment site, for each time period, the treatment cost is equal to all water moved to the treatment site multiplied by the operational treatment cost. The total treatments cost is the sum of treatment costs over all time periods and all treatment sites.

.. math::

    \textcolor{red}{C_{r,t}^{Treatment}} = (\sum\nolimits_{(l,r)\in LLA}\textcolor{red}{F_{l,r,t}^{Piped}}+\sum\nolimits_{(l,r)\in LLT}\textcolor{red}{F_{l,r,t}^{Trucked}}) \cdot \textcolor{green}{\pi_{r}^{Treatment}}

    \textcolor{red}{C^{TotalTreatment}} = \sum\nolimits_{\forall t\in T}\sum\nolimits_{r\in R}\textcolor{red}{C_{r,t}^{Treatment}}



**Treatment Balance:** :math:`\forall r \in R, t \in T`

Water input into treatment facility is treated with a level of efficiency, meaning only a given percentage of the water input is outputted to be reused at the completions pads.

.. math::

     \textcolor{green}{\varepsilon^{Treatment}} \cdot (\sum_{l \in L | (l, r) \in LLA}\textcolor{red}{F_{l,r,t}^{Piped}}
        + \sum_{l \in L | (l, r) \in LLT}\textcolor{red}{F_{l,r,t}^{Trucked}})= \sum_{l \in L | (l, r) \in LLA}\textcolor{red}{F_{r,l,t}^{Piped}} + \textcolor{red}{F_{r,t}^{UnusedTreatedWater}}

where :math:`\textcolor{green}{\varepsilon^{Treatment}} \leq 1`



**Completions Reuse Cost:** :math:`\forall p \in P, t \in T`

Completions reuse water is all water that meets completions pad demand, excluding freshwater. Completions reuse cost is the volume of completions reused water multiplied by the cost for reuse.

.. math::

    \textcolor{red}{C_{p,t}^{CompletionsReuse}} = (\sum\nolimits_{(l,\tilde{l})\in LLA, l\notin F}\textcolor{red}{F_{l,\tilde{l},t}^{Piped}}+\sum\nolimits_{(l,\tilde{l})\in LLT, l\notin F}\textcolor{red}{F_{l,\tilde{l},t}^{Trucked}}) \cdot \textcolor{green}{\pi_{p}^{CompletionsReuse}}


.. note:: Freshwater sourcing is excluded from completions reuse costs.

.. math::

    \textcolor{red}{C^{TotalCompletionsReuse}} = \sum\nolimits_{\forall t\in T}\sum\nolimits_{p\in CP}\textcolor{red}{C_{p,t}^{CompletionsReuse}}



**Piping Cost:** :math:`\forall {l \in (L - O - K)}, \forall {\tilde{l} \in (L - F)}, \forall {(l,\tilde{l}) \in LLA}, {t \in T}`

Piping cost is the total volume of piped water multiplied by the cost for piping.

:math:`\forall(l,\tilde{l})` if :math:`l \in F`:

.. math::

    \textcolor{red}{C_{l,\tilde{l},t}^{Piped}}
        = \textcolor{red}{F_{l,\tilde{l},t}^{Sourced}} \cdot \textcolor{green}{\pi_{l,\tilde{l}}^{Pipeline}}

Otherwise, :math:`\forall(l,\tilde{l})` if :math:`l \notin F`:

.. math::

    \textcolor{red}{C_{l,\tilde{l},t}^{Piped}}
        = \textcolor{red}{F_{l,\tilde{l},t}^{Piped}} \cdot \textcolor{green}{\pi_{l,\tilde{l}}^{Pipeline}}

Total Piping Cost:

.. math::

    \textcolor{red}{C^{TotalPiping}} = \sum_{t \in T}\sum_{(l,\tilde{l}) \in LLA}\textcolor{red}{C_{l,\tilde{l},t}^{Piped}}

.. note:: Note: Freshwater piping is tracked through Sourced Flow variable.



**Storage Deposit Cost:** :math:`\forall s \in S, t \in T`

Cost of depositing into storage is equal to the total volume of water moved into storage multiplied by the storage operation cost rate.

.. math::

    \textcolor{red}{C_{s,t}^{Storage}}
        = (\sum_{l \in L | (l, s) \in {LLA}}\textcolor{red}{F_{l,s,t}^{Piped}}
        + \sum_{l \in L | (l, s) \in {LLT}}\textcolor{red}{F_{l,s,t}^{Trucked}}) \cdot \textcolor{green}{\pi_{s}^{Storage}}

    \textcolor{red}{C^{TotalStorage}} = \sum\nolimits_{\forall t\in T}\sum\nolimits_{\forall s\in S}\textcolor{red}{C_{s,t}^{Storage}}



**Storage Withdrawal Credit:** :math:`\forall s \in S, t \in T`

Credits from withdrawing from storage is equal to the total volume of water moved out from storage multiplied by the storage operation credit rate.

.. math::

    \textcolor{red}{R_{s,t}^{Storage}}
        = (\sum_{l \in L | (s, l) \in LLA}\textcolor{red}{F_{s,l,t}^{Piped}}
        + \sum_{l \in L | (s, l) \in LLT}\textcolor{red}{F_{s,l,t}^{Trucked}}) \cdot \textcolor{green}{\rho_{s}^{Storage}}

    \textcolor{red}{R^{TotalStorage}} = \sum\nolimits_{\forall t\in T}\sum\nolimits_{\forall s\in S}\textcolor{red}{R_{s,t}^{Storage}}



**Pad Storage Cost:** :math:`\forall p \in CP, t \in T`

.. math::

    \textcolor{red}{C_{p,t}^{PadStorage}} = \textcolor{red}{z_{p,t}^{PadStorage}} \cdot \textcolor{green}{\pi_{p,t}^{PadStorage}}

    \textcolor{red}{C^{TotalPadStorage}} = \sum\nolimits_{\forall t\in T}\sum\nolimits_{\forall p\in CP}\textcolor{red}{C_{p,t}^{PadStorage}}

**Trucking Cost (Simplified)**

Trucking cost between two locations for time period is equal to the trucking volume between locations in time t divided by the truck capacity [this gets # of truckloads] multiplied by the lead time between two locations and hourly trucking cost.

.. math::

    \textcolor{red}{C_{l,\tilde{l},t}^{Trucked}} = \textcolor{red}{F_{l,\tilde{l},t}^{Trucked}} \cdot \textcolor{green}{1/\delta^{Truck}} \cdot \textcolor{green}{\tau_{p,p}^{Trucking}} \cdot \textcolor{green}{\pi_{l}^{Trucking}}

    \textcolor{red}{C^{TotalTrucking}} = \sum_{t \in T}\sum_{(l, \tilde{l}) \in LLT}\textcolor{red}{C_{l,\tilde{l},t}^{Trucked}}

.. note:: The constraints above explicitly consider freshwater trucking via FCT arcs included in LLT.



**Slack Costs:**

Weighted sum of the slack variables. In the case that the model is infeasible, these slack variables are used to determine where the infeasibility occurs (e.g. pipeline capacity is not sufficient).

.. math::

    \textcolor{red}{C^{Slack}} = \sum\nolimits_{p\in CP}\sum\nolimits_{t\in T}\textcolor{red}{S_{p,t}^{FracDemand}} \cdot \textcolor{green}{\psi^{FracDemand}}+\sum\nolimits_{p\in PP}\sum\nolimits_{t\in T}\textcolor{red}{S_{p,t}^{Production}} \cdot \textcolor{green}{\psi^{Production}}

        +\sum\nolimits_{p\in CP}\sum\nolimits_{t\in T}\textcolor{red}{S_{p,t}^{Flowback}} \cdot \textcolor{green}{\psi^{Flowback}}+\sum\nolimits_{(l,\tilde{l})\in {\ldots }}\textcolor{red}{S_{l,\tilde{l}}^{PipelineCapacity}} \cdot \textcolor{green}{\psi^{PipeCapacity}}

         +\sum\nolimits_{s\in S}\textcolor{red}{S_{s}^{StorageCapacity}} \cdot \textcolor{green}{\psi^{StorageCapacity}}+\sum\nolimits_{k\in K}\textcolor{red}{S_{k}^{DisposalCapacity}} \cdot \textcolor{green}{\psi^{DisposalCapacity}}

         +\sum\nolimits_{r\in R}\textcolor{red}{S_{r}^{TreatmentCapacity}} \cdot \textcolor{green}{\psi^{TreatmentCapacity}}+\sum\nolimits_{o\in O}\textcolor{red}{S_{o}^{BeneficialReuseCapacity}} \cdot \textcolor{green}{\psi^{BeneficialReuseCapacity}}

.. _operational_model_water_quality_extension:

Operational Model Water Quality Extension
---------------------------------------------------
An extension to this operational optimization model measures the water quality across all locations over time. As of now, water quality is not a decision variable. It is calculated after optimization of the operational model.
The process for calculating water quality is as follows: the operational model is first solved to optimality, water quality variables and constraints are added, flow rates and storage levels are fixed to the solved values at optimality, and the water quality is calculated.

.. note:: Fixed variables are denoted in purple in the documentation.

Assumptions:

* Water quality at a production pad or completions pad remains the same across all time periods
* When blending flows of different water quality, they blend linearly
* Treatment does not affect water quality

**Water Quality Sets**

:math:`\textcolor{blue}{w \in W}`             Water Quality Components (e.g., TDS)


**Water Quality Parameters**

:math:`\textcolor{green}{v_{l,w,[t]}}` =        Water quality at well pad

:math:`\textcolor{green}{\xi_{l,w}}` =            Initial water quality at storage


**Water Quality Variables**

:math:`\textcolor{red}{Q_{l,w,t}}` =           Water quality at location


**Disposal Site Water Quality** :math:`\forall k \in K, w \in W, t \in T`

The water quality of disposed water is dependent on the flow rates into the disposal site and the quality of each of these flows.

.. math::

    \sum\nolimits_{(n,k)\in NKA}\textcolor{purple}{F_{l,\tilde{l},t}^{Piped}} \cdot \textcolor{red}{Q_{n,w,t}} +\sum\nolimits_{(s,k)\in SKA}\textcolor{purple}{F_{l,\tilde{l},t}^{Piped}} \cdot \textcolor{red}{Q_{s,w,t}}+\sum\nolimits_{(r,k)\in RKA}\textcolor{purple}{F_{l,\tilde{l},t}^{Piped}} \cdot \textcolor{red}{Q_{r,w,t}}

    +\sum\nolimits_{(s,k)\in SKT}\textcolor{purple}{F_{l,\tilde{l},t}^{Trucked}} \cdot \textcolor{red}{Q_{s,w,t}}+\sum\nolimits_{(p,k)\in PKT}\textcolor{purple}{F_{l,\tilde{l},t}^{Trucked}} \cdot \textcolor{red}{Q_{p,w,t}}

    +\sum\nolimits_{(p,k)\in CKT}\textcolor{purple}{F_{l,\tilde{l},t}^{Trucked}} \cdot \textcolor{red}{Q_{p,w,t}}+\sum\nolimits_{(r,k)\in RKT}\textcolor{purple}{F_{l,\tilde{l},t}^{Trucked}} \cdot \textcolor{red}{Q_{r,w,t}}

    =\textcolor{purple}{F_{k,t}^{DisposalDestination}} \cdot \textcolor{red}{Q_{k,w,t}}

**Storage Site Water Quality** :math:`\forall s \in S, w \in W, t \in T`

The water quality at storage sites is dependent on the flow rates into the storage site, the volume of water in storage in the previous time period, and the quality of each of these flows. Even mixing is assumed, so all outgoing flows have the same water quality. If it is the first time period, the initial storage level and initial water quality replaces the water stored and water quality in the previous time period respectively.

.. math::

    \textcolor{green}{\lambda_{s,t=1}^{Storage}} \cdot \textcolor{green}{\xi_{s,w}} +\textcolor{purple}{L_{s,t-1}^{Storage}} \cdot \textcolor{red}{Q_{s,w,t-1}} +\sum\nolimits_{(n,s)\in NSA}\textcolor{purple}{F_{l,\tilde{l},t}^{Piped}} \cdot \textcolor{red}{Q_{n,w,t}}

    +\sum\nolimits_{(p,s)\in PST}\textcolor{purple}{F_{l,\tilde{l},t}^{Trucked}} \cdot \textcolor{red}{Q_{p,w,t}} +\sum\nolimits_{(p,s)\in CST}\textcolor{purple}{F_{l,\tilde{l},t}^{Trucked}} \cdot \textcolor{red}{Q_{p,w,t}}

    = \textcolor{red}{Q_{s,w,t}} \cdot (\textcolor{purple}{L_{s,t}^{Storage}} +\sum\nolimits_{(s,n)\in SNA}\textcolor{purple}{F_{l,\tilde{l},t}^{Piped}}+\sum\nolimits_{(s,p)\in SCA}\textcolor{purple}{F_{l,\tilde{l},t}^{Piped}}+\sum\nolimits_{(s,k)\in SKA}\textcolor{purple}{F_{l,\tilde{l},t}^{Piped}}

    +\sum\nolimits_{(s,r)\in SRA}\textcolor{purple}{F_{l,\tilde{l},t}^{Piped}}+\sum\nolimits_{(s,o)\in SOA}\textcolor{purple}{F_{l,\tilde{l},t}^{Piped}}+\sum\nolimits_{(s,p)\in SCT}\textcolor{purple}{F_{l,\tilde{l},t}^{Trucked}}+\sum\nolimits_{(s,k)\in SKT}\textcolor{purple}{F_{l,\tilde{l},t}^{Trucked}})

**Treatment Site Water Quality** :math:`\forall r \in R, w \in W, t \in T`

The water quality at treatment sites is dependent on the flow rates into the treatment site, the efficiency of treatment, and the water quality of the flows. Even mixing is assumed, so all outgoing flows have the same water quality. The treatment process does not affect water quality

.. math::

    \textcolor{green}{\varepsilon_{r,w}^{Treatment}} \cdot (\sum\nolimits_{(n,r)\in NRA}\textcolor{purple}{F_{l,\tilde{l},t}^{Piped}} \cdot \textcolor{red}{Q_{n,w,t}} +\sum\nolimits_{(s,r)\in SRA}\textcolor{purple}{F_{l,\tilde{l},t}^{Piped}} \cdot \textcolor{red}{Q_{s,w,t}}

    +\sum\nolimits_{(p,r)\in PRT}\textcolor{purple}{F_{l,\tilde{l},t}^{Trucked}} \cdot \textcolor{red}{Q_{p,w,t}} +\sum\nolimits_{(p,r)\in CRT}\textcolor{purple}{F_{l,\tilde{l},t}^{Trucked}} \cdot \textcolor{red}{Q_{p,w,t}} )

    = \textcolor{red}{Q_{r,w,t}} \cdot (\sum\nolimits_{(r,p)\in RCA}\textcolor{purple}{F_{l,\tilde{l},t}^{Piped}} + \textcolor{purple}{F_{r,t}^{UnusedTreatedWater}})

where :math:`\textcolor{green}{\varepsilon_{r,w}^{Treatment}} \leq 1`

**Network Node Water Quality** :math:`\forall n \in N, w \in W, t \in T`

The water quality at nodes is dependent on the flow rates into the node and the water quality of the flows. Even mixing is assumed, so all outgoing flows have the same water quality.

.. math::

    \sum\nolimits_{(p,n)\in PNA}\textcolor{purple}{F_{l,\tilde{l},t}^{Piped}} \cdot \textcolor{red}{Q_{p,w,t}} +\sum\nolimits_{(p,n)\in CNA}\textcolor{purple}{F_{l,\tilde{l},t}^{Piped}} \cdot \textcolor{red}{Q_{p,w,t}}

    +\sum\nolimits_{(\tilde{n},n)\in NNA}\textcolor{purple}{F_{l,\tilde{l},t}^{Piped}} \cdot \textcolor{red}{Q_{n,w,t}}+\sum\nolimits_{(s,n)\in SNA}\textcolor{purple}{F_{l,\tilde{l},t}^{Piped}} \cdot \textcolor{red}{Q_{s,w,t}}

    = \textcolor{red}{Q_{n,w,t}} \cdot (\sum\nolimits_{(n,\tilde{n})\in NNA}\textcolor{purple}{F_{l,\tilde{l},t}^{Piped}} +\sum\nolimits_{(n,p)\in NCA}\textcolor{purple}{F_{l,\tilde{l},t}^{Piped}}

    +\sum\nolimits_{(n,k)\in NKA}\textcolor{purple}{F_{l,\tilde{l},t}^{Piped}} +\sum\nolimits_{(n,r)\in NRA}\textcolor{purple}{F_{l,\tilde{l},t}^{Piped}}

    +\sum\nolimits_{(n,s)\in NSA}\textcolor{purple}{F_{l,\tilde{l},t}^{Piped}} +\sum\nolimits_{(n,o)\in NOA}\textcolor{purple}{F_{l,\tilde{l},t}^{Piped}})


**Beneficial Reuse Water Quality** :math:`\forall o \in O, w \in W, t \in T`

The water quality at beneficial reuse sites is dependent on the flow rates into the site and the water quality of the flows.

.. math::

    \sum\nolimits_{(n,o)\in NOA}\textcolor{purple}{F_{l,\tilde{l},t}^{Piped}} \cdot \textcolor{red}{Q_{n,w,t}} +\sum\nolimits_{(s,o)\in SOA}\textcolor{purple}{F_{l,\tilde{l},t}^{Piped}} \cdot \textcolor{red}{Q_{s,w,t}} +\sum\nolimits_{(p,o)\in POT}\textcolor{purple}{F_{l,\tilde{l},t}^{Trucked}} \cdot \textcolor{red}{Q_{p,w,t}}

    = \textcolor{red}{Q_{o,w,t}} \cdot \textcolor{purple}{F_{o,t}^{BeneficialReuseDestination}}


.. _model_terminology:

Operational Model Terminology
-----------------------------

**Beneficial Reuse Options:** This term refers to the reuse of water at mining facilities, farms, etc.

**Completions Demand:** Demand set by completions pads.  This demand can be met by produced water, treated water, or freshwater.

**Completions Reuse Water:** Water that meets demand at a completions site. This does not include freshwater or water for beneficial reuse.

**Network Nodes:** These are branch points for pipelines only.

.. note:: Well pads are not a subset of network nodes.

**[t]:** This notation indicates that timing of capacity expansion has not yet been implemented.

**Terminal Storage Level:** These are goal storage levels for the final time period. Without this, the storage levels would likely be depleted in the last time period.
