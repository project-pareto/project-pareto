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

:math:`\textcolor{blue}{t ∈ T}`			                               Time periods (i.e. days)

:math:`\textcolor{blue}{p ∈ P}`			                               Well pads

:math:`\textcolor{blue}{p ∈ PP}`			                           Production pads (subset of well pads P)

:math:`\textcolor{blue}{p ∈ CP}`  	                                   Completions pads (subset of well pads P)

:math:`\textcolor{blue}{f ∈ F}`			                               Freshwater sources

:math:`\textcolor{blue}{k ∈ K}`			                               Disposal sites

:math:`\textcolor{blue}{s ∈ S}`			                               Storage sites

:math:`\textcolor{blue}{r ∈ R}`			                               Treatment sites

:math:`\textcolor{blue}{o ∈ O}`			                               Beneficial Reuse options

:math:`\textcolor{blue}{n ∈ N}`			                               Network nodes

:math:`\textcolor{blue}{l ∈ L}`			                               Locations (superset of well pads, disposal sites, nodes, …)

:math:`\textcolor{blue}{a ∈ A}`			                               Production tanks


:math:`\textcolor{blue}{(p,p) ∈ PCA}`	                               Production-to-completions pipeline arcs

:math:`\textcolor{blue}{(p,n) ∈ PNA}`                                 Production-to-node pipeline arcs

:math:`\textcolor{blue}{(p,p) ∈ PPA}`                                 Production-to-production pipeline arcs

:math:`\textcolor{blue}{(p,n) ∈ CNA}`	                               Completions-to-node pipeline arcs

:math:`\textcolor{blue}{(p,p) ∈ CCA}`	                               Completions-to-completions pipeline arcs

:math:`\textcolor{blue}{(n,n) ∈ NNA}`                                 Node-to-node pipeline arcs

:math:`\textcolor{blue}{(n,p) ∈ NCA}`                                 Node-to-completions pipeline arcs

:math:`\textcolor{blue}{(n,k) ∈ NKA}`	                               Node-to-disposal pipeline arcs

:math:`\textcolor{blue}{(n,s) ∈ NSA}`	                               Node-to-storage pipeline arcs

:math:`\textcolor{blue}{(n,r) ∈ NRA}`                                 Node-to-treatment pipeline arcs

:math:`\textcolor{blue}{(n,o) ∈ NOA}`	                               Node-to-beneficial reuse pipeline arcs

:math:`\textcolor{blue}{(f,p) ∈ FCA}`	                               Freshwater-to-completions pipeline arcs

:math:`\textcolor{blue}{(r,n) ∈ RNA}`	                               Treatment-to-node pipeline arcs

:math:`\textcolor{blue}{(r,p) ∈ RCA}`	                               Treatment-to-completions pipeline arcs

:math:`\textcolor{blue}{(r,k) ∈ RKA}`	                               Treatment-to-disposal pipeline arcs

:math:`\textcolor{blue}{(s,n) ∈ SNA}`	                               Storage-to-node pipeline arcs

:math:`\textcolor{blue}{(s,p) ∈ SCA}`	                               Storage-to-completions pipeline arcs

:math:`\textcolor{blue}{(s,k) ∈ SKA}`	                               Storage-to-disposal pipeline arcs

:math:`\textcolor{blue}{(s,r) ∈ SRA}`	                               Storage-to-treatment pipeline arcs

:math:`\textcolor{blue}{(s,o) ∈ SOA}`	                               Storage-to-beneficial reuse pipeline arcs


:math:`\textcolor{blue}{(p,p) ∈ PCT}`	                               Production-to-completions trucking arcs

:math:`\textcolor{blue}{(f,c) ∈ FCT}`                                 Freshwater-to-completions trucking arcs

:math:`\textcolor{blue}{(p,k) ∈ PKT}`	                               Production-to-disposal trucking arcs

:math:`\textcolor{blue}{(p,s) ∈ PST}`                                 Production-to-storage trucking arcs

:math:`\textcolor{blue}{(p,r) ∈ PRT}`	                               Production-to-treatment trucking arcs

:math:`\textcolor{blue}{(p,o) ∈ POT}`	                               Production-to-beneficial reuse trucking arcs

:math:`\textcolor{blue}{(p,k) ∈ CKT}`	                               Completions-to-disposal trucking arcs

:math:`\textcolor{blue}{(p,s) ∈ CST}`	                               Completions-to-storage trucking arcs

:math:`\textcolor{blue}{(p,r) ∈ CRT}`                                 Completions-to-treatment trucking arcs

:math:`\textcolor{blue}{(p,p) ∈ CCT}`	                               Completions-to-completions trucking arcs (flowback reuse)

:math:`\textcolor{blue}{(s,p) ∈ SCT}`                                 Storage-to-completions trucking arcs

:math:`\textcolor{blue}{(s,k) ∈ SKT}`                                 Storage-to-disposal trucking arcs

:math:`\textcolor{blue}{(r,k) ∈ RKT}`	                               Treatment-to-disposal trucking arcs

:math:`\textcolor{blue}{(p,a) ∈ PAL}`	                               Pad-to-tank links



**Continuous Variables**

:math:`\textcolor{red}{F_{l,l,t}^{Piped}}` =                           Produced water piped from one location to another location

:math:`\textcolor{red}{F_{l,l,t}^{Trucked}}` =	                       Produced water trucked from one location to another location

:math:`\textcolor{red}{F_{f,p,t}^{Sourced}}` =                         Fresh water sourced from source to completions

:math:`\textcolor{red}{F_{p,t}^{PadStorageIn}}` =	                   Water put into completions pad storage

:math:`\textcolor{red}{F_{p,t}^{PadStorageOut}}` =	                   Water removed from completions pad storage

:math:`\textcolor{red}{F_{r,t}^{TreatmentDestination}}` =	           Water delivered to treatment site

:math:`\textcolor{red}{F_{r,t}^{UnusedTreatedWater}}` =	               Water leftover from the treatment process

:math:`\textcolor{red}{F_{k,t}^{DisposalDestination}}` =	           Water injected at disposal site

:math:`\textcolor{red}{F_{o,t}^{BeneficialReuseDestination}}` =	       Water delivered to beneficial reuse site


**If the production tanks are separate, water level and water drainage are tracked at each individual production tank:**

    :math:`\textcolor{red}{F_{p,a,t}^{DrainF}}` =	                   Produced water drained from production tank

    :math:`\textcolor{red}{L_{p,a,t}^{ProdTankL}}` =	               Water level in production tank at the end of time period t

**Otherwise, if the production tanks are equalized, the water level and water drainage can be aggregated to a pad level:**

    :math:`\textcolor{red}{F_{p,t}^{DrainF}}` =	                       Produced water drained from equalized production tanks

    :math:`\textcolor{red}{L_{p,t}^{ProdTank}}` =	                   Water level in equalized production tanks at the end of time period t


:math:`\textcolor{red}{B_{p,t}^{ProductionB}}` =	                   Produced water for transport from pad

:math:`\textcolor{red}{L_{s,t}^{Storage}}` =	                       Water level in storage site at the end of time period t


:math:`\textcolor{red}{L_{p,t}^{PadStorage}}` =	                       Water level in completions pad storage  at the end of time period t

:math:`\textcolor{red}{C_{l,l,t}^{Piped}}` =	                       Cost of piping produced water from one location to another location

:math:`\textcolor{red}{C_{l,l,t}^{Trucked}}` =	                       Cost of trucking produced water from one location to another location

:math:`\textcolor{red}{C_{f,p,t}^{Sourced}}` =	                       Cost of sourcing fresh water from source to completions pad

:math:`\textcolor{red}{C_{k,t}^{Disposal}}` =                          Cost of injecting produced water at disposal site

:math:`\textcolor{red}{C_{r,t}^{Treatment}}` =	                       Cost of treating produced water at treatment site

:math:`\textcolor{red}{C_{r,t}^{UnusedTreatedWater}}` =	               Cost of unused treated water at treatment site

:math:`\textcolor{red}{C_{p,t}^{CompletionsReuse}}` =                  Cost of reusing produced water at completions site

:math:`\textcolor{red}{C_{s,t}^{Storage}}` =                           Cost of storing produced water at storage site (incl. treatment)

:math:`\textcolor{red}{R_{s,t}^{Storage}}` =                           Credit for retrieving stored produced water from storage site

:math:`\textcolor{red}{C^{TotalSourced}}` =                            Total cost of sourcing freshwater

:math:`\textcolor{red}{C^{TotalDisposal}}` =                           Total cost of injecting produced water

:math:`\textcolor{red}{C^{TotalTreatment}}` = 	                       Total cost of treating produced water

:math:`\textcolor{red}{C^{TotalUnusedTreatedWater}}` =                 Total cost of unused treated water

:math:`\textcolor{red}{C^{TotalCompletionsReuse}}` =                   Total cost of reusing produced water

:math:`\textcolor{red}{C^{TotalPiping}}` = 	                           Total cost of piping produced water

:math:`\textcolor{red}{C^{TotalStorage}}` =                            Total cost of storing produced water

:math:`\textcolor{red}{C^{TotalPadStorage}}` = 	                       Total cost of storing produced water at completions pad

:math:`\textcolor{red}{C^{TotalTrucking}}` =                           Total cost of trucking produced water

:math:`\textcolor{red}{C^{Slack}}` =                                   Total cost of slack variables

:math:`\textcolor{red}{R^{TotalStorage}}` = 	                       Total credit for withdrawing produced water


:math:`\textcolor{red}{S_{p,t}^{FracDemand}}` =  	                   Slack variable to meet the completions water demand

:math:`\textcolor{red}{S_{p,t}^{Production}}` = 	                   Slack variable to process produced water production

:math:`\textcolor{red}{S_{p,t}^{Flowback}}` = 	                       Slack variable to process flowback water production

:math:`\textcolor{red}{S_{l,l}^{Pipeline Capacity}}` =                 Slack variable to provide necessary pipeline capacity

:math:`\textcolor{red}{S_{s}^{StorageCapacity}}` =                     Slack variable to provide necessary storage capacity

:math:`\textcolor{red}{S_{k}^{DisposalCapacity}}` =                    Slack variable to provide necessary disposal capacity

:math:`\textcolor{red}{S_{r}^{TreatmentCapacity}}` =                    Slack variable to provide necessary treatment capacity

:math:`\textcolor{red}{S_{o}^{BeneficialReuseCapacity}}` =             Slack variable to provide necessary beneficial reuse capacity



**Binary Variables**


:math:`\textcolor{red}{y_{l,l,t}^{Flow}}` =                            Directional flow between two locations

:math:`\textcolor{red}{z_{p,t}^{PadStorage}}` =                        Completions pad storage use


**Parameters**

:math:`\textcolor{green}{y_{p,t}^{Completions}}` = 	                   Completions demand at a completions site in a time period

**If the production tanks are separate, water level and water drainage are tracked at each individual production tank:**

    :math:`\textcolor{green}{β_{p,a,t}^{Production}}` = 	           Produced water supply forecast for a production pad

    :math:`\textcolor{green}{σ_{p,a}^{ProdTank}}` =	                   Production tank capacity

    :math:`\textcolor{green}{λ_{p,a}^{ProdTank}}` =	 	               Initial water level in production tank

**Otherwise, if the production tanks are equalized, the water level and water drainage can be aggregated to a pad level:**

    :math:`\textcolor{green}{β_{p,t}^{Production}}` =	               Produced water supply forecast for a production pad

    :math:`\textcolor{green}{σ_{p}^{ProdTank}}` =	                   Combined capacity of equalized production tanks

    :math:`\textcolor{green}{λ_{p}^{ProdTank}}` =                      Initial water level in equalized production tanks


:math:`\textcolor{green}{β_{p,t}^{Flowback}}` =	                       Flowback supply forecast for a completions pad

:math:`\textcolor{green}{σ_{l,l}^{Pipeline}}` =	                       Daily pipeline capacity between two locations

:math:`\textcolor{green}{σ_{k}^{Disposal}}` =	                       Daily disposal capacity at a disposal site

:math:`\textcolor{green}{σ_{s}^{Storage}}` =                           Storage capacity at a storage site

:math:`\textcolor{green}{σ_{p,t}^{PadStorage}}` =                      Storage capacity at completions site

:math:`\textcolor{green}{σ_{r}^{Treatment}}` =                         Daily treatment capacity at a treatment site

:math:`\textcolor{green}{σ_{o}^{BeneficialReuse}}` =                   Daily reuse capacity at a beneficial reuse site

:math:`\textcolor{green}{σ_{f,t}^{Freshwater}}` =                      Daily freshwater sourcing capacity at freshwater source

:math:`\textcolor{green}{σ_{p}^{Offloading,Pad}}` =                    Daily truck offloading sourcing capacity per pad

:math:`\textcolor{green}{σ_{s}^{Offloading,Storage}}` =	               Daily truck offloading sourcing capacity per storage site


:math:`\textcolor{green}{σ_{p}^{Processing,Pad}}` =                    Daily processing (e.g. clarification) capacity per pad

:math:`\textcolor{green}{σ_{s}^{Processing,Storage}}` =                Daily processing (e.g. clarification) capacity at storage site

:math:`\textcolor{green}{ϵ_{r,w}^{Treatment}}` =                       Treatment efficiency for water quality component at treatment site

:math:`\textcolor{green}{δ^{Truck}}` =  Truck Capacity

:math:`\textcolor{green}{τ_{p,p}^{Trucking}}` =                        Drive time between two pads

:math:`\textcolor{green}{τ_{p,k}^{Trucking}}` =	                       Drive time from a pad to a disposal site

:math:`\textcolor{green}{τ_{p,s}^{Trucking}}` =	                       Drive time from a pad to a storage site

:math:`\textcolor{green}{τ_{p,r}^{Trucking}}` =	                       Drive time from a pad to a treatment site

:math:`\textcolor{green}{τ_{p,o}^{Trucking}}` =                        Drive time from a pad to a beneficial reuse site

:math:`\textcolor{green}{τ_{s,p}^{Trucking}}` =	                       Drive time from a storage site to a completions site

:math:`\textcolor{green}{τ_{s,k}^{Trucking}}` =                        Drive time from a storage site to a disposal site

:math:`\textcolor{green}{τ_{r,k}^{Trucking}}` =                        Drive time from a treatment site to a disposal site

:math:`\textcolor{green}{λ_{s}^{Storage}}` =                           Initial storage level at storage site

:math:`\textcolor{green}{λ_{p}^{PadStorage}}` =                        Initial storage level at completions site

:math:`\textcolor{green}{θ_{p}^{PadStorage}}` =                        Terminal storage level at completions site

:math:`\textcolor{green}{λ_{l,l}^{Pipeline}}` = 	                   Pipeline segment length

:math:`\textcolor{green}{π_{k}^{Disposal}}` =                          Disposal operational cost

:math:`\textcolor{green}{π_{r}^{Treatment}}` =	                       Treatment operational cost (may include “clean brine”)

:math:`\textcolor{green}{π_{p}^{CompletionReuse}}` =                   Completions reuse operational cost

:math:`\textcolor{green}{π_{s}^{Storage}}` =                           Storage deposit operational cost

:math:`\textcolor{green}{π_{p,t}^{PadStorage}}` =                      Completions pad operational cost

:math:`\textcolor{green}{ρ_{s}^{Storage}}` =                           Storage withdrawal operational cgreenit

:math:`\textcolor{green}{π_{l,l}^{Pipeline}}` =	                       Pipeline operational cost

:math:`\textcolor{green}{π_{l}^{Trucking}}` =                          Trucking hourly cost (by source)

:math:`\textcolor{green}{π_{f}^{Sourcing}}` =                          Fresh sourcing cost (does not include transportation cost)


:math:`\textcolor{green}{M^{Flow}}` =                                  Big-M flow parameter

:math:`\textcolor{green}{ψ^{FracDemand}}` =                            Slack cost parameter

:math:`\textcolor{green}{ψ^{Production}}` =                            Slack cost parameter

:math:`\textcolor{green}{ψ^{Flowback}}` =                              Slack cost parameter

:math:`\textcolor{green}{ψ^{PipelineCapacity}}` =                      Slack cost parameter

:math:`\textcolor{green}{ψ^{StorageCapacity}}` =  	                   Slack cost parameter

:math:`\textcolor{green}{ψ^{DisposalCapacity}}` =                      Slack cost parameter

:math:`\textcolor{green}{ψ^{TreamentCapacity}}` =                      Slack cost parameter

:math:`\textcolor{green}{ψ^{BeneficialReuseCapacity}}` =  	           Slack cost parameter



.. _mathematical_program_formulation:

Operational Model Mathematical Program Formulation
---------------------------------------------------

The default objective function for this produced water operational model is to minimize costs, which includes operational costs associated with procurement of fresh water, the cost of disposal, trucking and piping produced water between well pads and treatment facilities, and the cost of storing, treating and reusing produced water. A credit for using treated water is also considered, and additional slack variables are included to facilitate the identification of potential issues with input data.


**Objective**

.. math::

    min = \textcolor{red}{C^{TotalSourced}}+\textcolor{red}{C^{TotalDisposal}}+\textcolor{red}{C^{TotalTreatment}}+\textcolor{red}{C^{TotalUnusedTreatedWater}}+\textcolor{red}{C^{TotalCompletionsReuse}}+

        \textcolor{red}{C^{TotalPiping}}+\textcolor{red}{C^{TotalStorage}}+\textcolor{red}{C^{TotalPadStorage}}+ \textcolor{red}{C^{TotalTrucking}}+\textcolor{red}{C^{Slack}-R^{TotalStorage}}


**Completions Pad Demand Balance:** ∀p ∈ CP, t ∈ T

.. math::

    \textcolor{green}{γ_{p,t}^{Completions}}=\sum\nolimits_{(n,p)∈NCA}\textcolor{red}{F_{l,l,t}^{Piped}} +\sum\nolimits_{(p,p)∈PCA}\textcolor{red}{F_{l,l,t}^{Piped}} +\sum\nolimits_{(s,p)∈SCA}\textcolor{red}{F_{l,l,t}^{Piped}}

        +\sum\nolimits_{(p,c)∈CCA}\textcolor{red}{F_{l,l,t}^{Piped}} +\sum\nolimits_{(r,p)∈RCA}\textcolor{red}{F_{l,l,t}^{Piped}} +\sum\nolimits_{(f,p)∈FCA}\textcolor{red}{F_{l,l,t}^{Sourced}}

        +\sum\nolimits_{(p,p)∈PCT}\textcolor{red}{F_{l,l,t}^{Trucked}} +\sum\nolimits_{(s,p)∈SCT}\textcolor{red}{F_{l,l,t}^{Trucked}} +\sum\nolimits_{(p,p)∈CCT}\textcolor{red}{F_{l,l,t}^{Trucked}}

        +\sum\nolimits_{(f,p)∈FCT}\textcolor{red}{F_{l,l,t}^{Trucked}} +\textcolor{red}{F_{p,t}^{PadStorageOut}}-\textcolor{red}{F_{p,t}^{PadStorageIn}}+\textcolor{red}{S_{p,t}^{FracDemand}}



**Completions Pad Storage Balance:** ∀p ∈ CP, t ∈ T

This constraint sets the storage level at the completions pad. For each completions pad and for each time period, completions pad storage is equal to storage in last time period plus water put in minus water removed. If it is the first time period, the pad storage is the initial pad storage.


.. math::

    \textcolor{red}{L_{p,t}^{PadStorage}} = \textcolor{green}{λ_{p,t=1}^{PadStorage}}+\textcolor{red}{L_{p,t-1}^{PadStorage}}+\textcolor{red}{F_{p,t}^{StorageIn}}-\textcolor{red}{F_{p,t}^{StorageOut}}



**Completions Pad Storage Capacity:** ∀p ∈ CP, t ∈ T

The storage at each completions pad must always be at or below its capacity in every time period.

.. math::

    \textcolor{red}{L_{p,t}^{PadStorage}}≤\textcolor{red}{z_{p,t}^{PadStorage}}⋅\textcolor{green}{σ_{p,t}^{PadStorage}}

**Terminal Completions Pad Storage Level:** ∀p ∈ CP, t ∈ T

.. math::

    \textcolor{red}{L_{p,t=T}^{PadStorage}}≤\textcolor{green}{θ_{p}^{PadStorage}}

The storage in the last period must be at or below its terminal storage level.



**Freshwater Sourcing Capacity:** ∀f ∈ F, t ∈ T

For each freshwater source and each time period, the outgoing water from the freshwater source is below the freshwater capacity.

.. math::

      \sum\nolimits_{(f,p)∈FCA}\textcolor{red}{F_{l,l,t}^{Sourced}} +\sum\nolimits_{(f,p)∈FCT}\textcolor{red}{F_{l,l,t}^{Trucked}} ≤\textcolor{green}{σ_{f,t}^{Freshwater}}



**Completions Pad Truck Offloading Capacity:** ∀p ∈ CP, t ∈ T

For each completions pad and time period, the volume of water being trucked into the completions pad must be below the trucking offloading capacity.

.. math::

    \sum\nolimits_{(p,p)∈PCT}\textcolor{red}{F_{l,l,t}^{Trucked}} +\sum\nolimits_{(s,p)∈SCT}\textcolor{red}{F_{l,l,t}^{Trucked}} +\sum\nolimits_{(f,p)∈FCT}\textcolor{red}{F_{l,l,t}^{Trucked}}

        +\sum\nolimits_{(p,p)∈CCT}\textcolor{red}{F_{l,l,t}^{Trucked}} ≤\textcolor{green}{σ_{p}^{Offloading,Pad}}



**Completions Pad Processing Capacity:**

For each completions pad and time period, the volume of water (excluding freshwater) coming in must be below the processing limit.

.. math::

    \sum\nolimits_{(n,p)∈NCA}\textcolor{red}{F_{l,l,t}^{Piped}} +\sum\nolimits_{(p,p)∈PCA}\textcolor{red}{F_{l,l,t}^{Piped}} +\sum\nolimits_{(s,p)∈SCA}\textcolor{red}{F_{l,l,t}^{Piped}}

        +\sum\nolimits_{(p,c)∈CCA}\textcolor{red}{F_{l,l,t}^{Piped}} +\sum\nolimits_{(r,p)∈RCA}\textcolor{red}{F_{l,l,t}^{Piped}} +\sum\nolimits_{(p,p)∈PCT}\textcolor{red}{F_{l,l,t}^{Trucked}}

        +\sum\nolimits_{(s,p)∈SCT}\textcolor{red}{F_{l,l,t}^{Trucked}} +\sum\nolimits_{(p,p)∈CCT}\textcolor{red}{F_{l,l,t}^{Trucked}} ≤\textcolor{green}{σ_{p}^{Processing,Pad}}


.. note:: This constraint has not actually been implemented yet.



**Storage Site Truck Offloading Capacity:** ∀p ∈ S, t ∈ T

For each storage site and each time period, the volume of water being trucked into the storage site must be below the trucking offloading capacity for that storage site.

.. math::

    \sum\nolimits_{(p,s)∈PST}\textcolor{red}{F_{l,l,t}^{Trucked}} +\sum\nolimits_{(p,s)∈CST}\textcolor{red}{F_{l,l,t}^{Trucked}} ≤\textcolor{green}{σ_{s}^{Offloading,Storage}}



**Storage Site Processing Capacity:** ∀s ∈ S, t ∈ T

For each storage site and each time period, the volume of water being trucked into the storage site must be less than the processing capacity for that storage site.

.. math::

    \sum\nolimits_{(n,s)∈NSA}\textcolor{red}{F_{l,l,t}^{Piped}} +\sum\nolimits_{(p,s)∈PST}\textcolor{red}{F_{l,l,t}^{Trucked}} +\sum\nolimits_{(p,s)∈CST}\textcolor{red}{F_{l,l,t}^{Trucked}} ≤\textcolor{green}{σ_{s}^{Processing,Storage}}



**Production Tank Balance:**

If there are individual production tanks, the water level must be tracked at each tank. The water level at a given tank at the end of each period is equal to the water level at the previous period plus the flowback supply forecast at the pad minus the water that is drained.  If it is the first period, it is equal to the initial water level.

For individual production tanks: ∀(p,a) ∈ PAL, t ∈ T

.. math::

    \textcolor{red}{L_{p,a,t}^{ProdTank}} = \textcolor{green}{λ_{p,a,t=1}^{ProdTank}}+\textcolor{red}{L_{p,a,t-1}^{ProdTank}}+\textcolor{green}{β_{p,a,t}^{Production}}-\textcolor{red}{F_{p,a,t}^{Drain}}


For equalized production tanks: ∀p ∈ P, t ∈ T

.. math::

    \textcolor{red}{L_{p,t}^{ProdTank}} = \textcolor{green}{λ_{p,t=1}^{ProdTank}}+\textcolor{red}{L_{p,t-1}^{ProdTank}}+\textcolor{green}{β_{p,t}^{Production}}-\textcolor{red}{F_{p,t}^{Drain}}



**Production Tank Capacity:**

The water level at the production tanks must always be below the production tank capacity.

For individual production tanks: ∀(p,a) ∈ PAL, t ∈ T

.. math::

    \textcolor{red}{L_{p,a,t}^{ProdTank}}≤\textcolor{green}{σ_{p,a}^{ProdTank}}


For equalized production tanks: ∀p ∈ P, t ∈ T

.. math::

    \textcolor{red}{L_{p,t}^{ProdTank}}≤\textcolor{green}{σ_{p}^{ProdTank}}



**Terminal Production Tank Level Balance:**

The water level at the production tanks in the final time period must be below the terminal production tank water level parameter.

For individual production tanks: ∀(p,a) ∈ PAL, t ∈ T

.. math::

    \textcolor{red}{L_{p,a,t=T}^{ProdTank}}≤\textcolor{green}{λ_{p,a,t=1}^{ProdTank}}


For equalized production tanks: ∀p ∈ P,t ∈ T

.. math::

    \textcolor{red}{L_{p,t=T}^{ProdTank}}≤\textcolor{green}{λ_{p,t=1}^{ProdTank}}



**Tank-to-Pad Production Balance:**

If there are individual production tanks, the water drained across all tanks at the completions pad must be equal to the produced water for transport at the pad.

For individual production tanks: ∀p ∈ P, t ∈ T

.. math::

    \sum\nolimits_{(p,a)∈PAL}\textcolor{red}{F_{p,a,t}^{Drain}} =\textcolor{red}{B_{p,t}^{Production}}


Otherwise, if the production tanks are equalized, the production water drained is measured on an aggregated production pad level.

For equalized production tanks: ∀p ∈ P, t ∈ T

.. math::

    \textcolor{red}{F_{p,t}^{Drain}}=\textcolor{red}{B_{p,t}^{Production}}

.. note:: The constraint proposed above is not necessary but included to facilitate switching between (1) an equalized production tank version and (2) a non-equalized production tank version.



**Production Pad Supply Balance:** ∀p ∈ PP, t ∈ T

All produced water must be accounted for. For each production pad and for each time period, the volume of outgoing water must be equal to the produced water transported out of the production pad.

.. math::

    \textcolor{red}{B_{p,t}^{Production}} = \sum\nolimits_{(p,n)∈PNA}\textcolor{red}{F_{l,l,t}^{Piped}} +\sum\nolimits_{(p,p)∈PCA}\textcolor{red}{F_{l,l,t}^{Piped}}+\sum\nolimits_{(p,p)∈PPA}\textcolor{red}{F_{l,l,t}^{Piped}}

        +\sum\nolimits_{(p,p)∈PCT}\textcolor{red}{F_{l,l,t}^{Trucked}}+\sum\nolimits_{(p,k)∈PKT}\textcolor{red}{F_{l,l,t}^{Trucked}}+\sum\nolimits_{(p,s)∈PST}\textcolor{red}{F_{l,l,t}^{Trucked}}

        +\sum\nolimits_{(p,r)∈PRT}\textcolor{red}{F_{l,l,t}^{Trucked}} +\sum\nolimits_{(p,o)∈POT}\textcolor{red}{F_{l,l,t}^{Trucked}}+\textcolor{red}{S_{p,t}^{Production}}



**Completions Pad Supply Balance (i.e. Flowback Balance):** ∀p ∈ CP, t ∈ T

All flowback water must be accounted for.  For each completions pad and for each time period, the volume of outgoing water must be equal to the forecasted flowback produced water for the completions pad.

.. math::

    \textcolor{green}{β_{p,t}^{Flowback}} = \sum\nolimits_{(p,n)∈CNA}\textcolor{red}{F_{l,l,t}^{Piped}}+\sum\nolimits_{(p,c)∈CCA}\textcolor{red}{F_{l,l,t}^{Piped}}+\sum\nolimits_{(p,p)∈CCT}\textcolor{red}{F_{l,l,t}^{Trucked}}+

    \sum\nolimits_{(p,k)∈CKT}\textcolor{red}{F_{l,l,t}^{Trucked}}+\sum\nolimits_{(p,s)∈CST}\textcolor{red}{F_{l,l,t}^{Trucked}}+\sum\nolimits_{(p,r)∈CRT}\textcolor{red}{F_{l,l,t}^{Trucked}} +\textcolor{red}{S_{p,t}^{Flowback}}



**Network Node Balance:** ∀n ∈ N, t ∈ T

Flow balance constraint (i.e., inputs are equal to outputs). For each pipeline node and for each time period, the volume water into the node is equal to the volume of water out of the node.

.. math::

    \sum\nolimits_{(p,n)∈PNA}\textcolor{red}{F_{l,l,t}^{Piped}} +\sum\nolimits_{(p,n)∈CNA}\textcolor{red}{F_{l,l,t}^{Piped}} +\sum\nolimits_{(n ̃,n)∈NNA}\textcolor{red}{F_{l,l,t}^{Piped}}+\sum\nolimits_{(s,n)∈SNA}\textcolor{red}{F_{l,l,t}^{Piped}}

        = \sum\nolimits_{(n,n ̃ )∈NNA}\textcolor{red}{F_{l,l,t}^{Piped}} +\sum\nolimits_{(n,p)∈NCA}\textcolor{red}{F_{l,l,t}^{Piped}}+\sum\nolimits_{(n,k)∈NKA}\textcolor{red}{F_{l,l,t}^{Piped}}

        +\sum\nolimits_{(n,r)∈NRA}\textcolor{red}{F_{l,l,t}^{Piped}} +\sum\nolimits_{(n,s)∈NSA}\textcolor{red}{F_{l,l,t}^{Piped}} +\sum\nolimits_{(n,o)∈NOA}\textcolor{red}{F_{l,l,t}^{Piped}}



**Bi-Directional Flow:** ∀(l,l) ∈ {PCA,PNA,PPA,CNA,NNA,NCA,NKA,NSA,NRA,…,SOA}, t ∈ T

There can only be flow in one direction for a given pipeline arc in a given time period.

Flow is only allowed in a given direction if the binary indicator for that direction is “on”.

.. math::

    \textcolor{red}{y_{l,l ̃,t}^{Flow}}+\textcolor{red}{y_{l ̃,l,t}^{Flow}} = 1

.. note:: Technically this constraint should only be enforced for truly reversible arcs (e.g. NCA and CNA); and even then it only needs to be defined per one reversible arc (e.g. NCA only and not NCA and CNA).

.. math::

    \textcolor{red}{F_{l,l,t}^{Piped}}≤\textcolor{red}{y_{l,l,t}^{Flow}}⋅\textcolor{green}{M^{Flow}}



**Storage Site Balance:** ∀s ∈ S, t ∈ T

For each storage site and for each time period, if it is the first time period, the storage level is the initial storage. Otherwise, the storage level is equal to the storage level in the previous time period plus water inputs minus water outputs.

.. math::

    \textcolor{red}{L_{s,t}^{Storage}} = \textcolor{green}{λ_{s,t=1}^{Storage}}+\textcolor{red}{L_{s,t-1}^{Storage}}+\sum\nolimits_{(n,s)∈NSA}\textcolor{red}{F_{l,l,t}^{Piped}} +\sum\nolimits_{(p,s)∈PST}\textcolor{red}{F_{l,l,t}^{Trucked}}

        +\sum\nolimits_{(p,s)∈CST}\textcolor{red}{F_{l,l,t}^{Trucked}}-\sum\nolimits_{(s,n)∈SNA}\textcolor{red}{F_{l,l,t}^{Piped}}-\sum\nolimits_{(s,p)∈SCA}\textcolor{red}{F_{l,l,t}^{Piped}}-\sum\nolimits_{(s,k)∈SKA}\textcolor{red}{F_{l,l,t}^{Piped}}

        -\sum\nolimits_{(s,r)∈SRA}\textcolor{red}{F_{l,l,t}^{Piped}}-\sum\nolimits_{(s,o)∈SOA}\textcolor{red}{F_{l,l,t}^{Piped}}-\sum\nolimits_{(s,p)∈SCT}\textcolor{red}{F_{l,l,t}^{Trucked}}-\sum\nolimits_{(s,k)∈SKT}\textcolor{red}{F_{l,l,t}^{Trucked}}



**Pipeline Capacity:**

∀(l,l) ∈ {PCA,PNA,PPA,CNA,NNA,NCA,NKA,NSA,NRA,…,SOA}, [t ∈ T]

.. math::

    \textcolor{red}{F_{l,l,[t]}^{Capacity}} = \textcolor{green}{σ_{l,l}^{Pipeline}}+\textcolor{red}{S_{l,l}^{PipelineCapacity}}

∀(l,l) ∈ {PCA,PNA,PPA,CNA,NNA,NCA,NKA,NSA,NRA,…,SOA}, t ∈ T

.. math::

    \textcolor{red}{F_{l,l,t}^{Piped}}≤\textcolor{red}{F_{l,l,[t]}^{Capacity}}



**Storage Capacity:**

The total stored water in a given time period must be less than the capacity. If the storage capacity limits the feasibility, the slack variable will be nonzero, and the storage capacity will be increased to allow a feasible solution.

∀s ∈ S,[t ∈ T]

.. math::

    \textcolor{red}{X_{s,[t]}^{Capacity}} = \textcolor{green}{σ_{s}^{Storage}}+\textcolor{red}{S_{s}^{StorageCapacity}}

∀s ∈ S, t ∈ T

.. math::

    \textcolor{red}{L_{s,t}^{Storage}}≤\textcolor{red}{X_{s,[t]}^{Capacity}}



**Disposal Capacity:**

The total disposed water in a given time period must be less than the capacity. If the disposal capacity limits the feasibility, the slack variable will be nonzero, and the disposal capacity will be increased to allow a feasible solution.

∀k ∈ K, [t ∈ T]

.. math::

    \textcolor{red}{D_{k,[t]}^{Capacity}} = \textcolor{green}{σ_{k}^{Disposal}}+\textcolor{red}{S_{k}^{DisposalCapacity}}

∀k ∈ K, t ∈ T

.. math::


    \sum\nolimits_{(n,k)∈NKA}\textcolor{red}{F_{l,l,t}^{Piped}} +\sum\nolimits_{(s,k)∈SKA}\textcolor{red}{F_{l,l,t}^{Piped}}+\sum\nolimits_{(s,k)∈SKT}\textcolor{red}{F_{l,l,t}^{Trucked}}+\sum\nolimits_{(p,k)∈PKT}\textcolor{red}{F_{l,l,t}^{Trucked}}

        +\sum\nolimits_{(p,k)∈CKT}\textcolor{red}{F_{l,l,t}^{Trucked}}+\sum\nolimits_{(r,k)∈RKT}\textcolor{red}{F_{l,l,t}^{Trucked}} ≤\textcolor{red}{D_{k,[t]}^{Capacity}}

∀k ∈ K, t ∈ T

.. math::


    \sum\nolimits_{(n,k)∈NKA}\textcolor{red}{F_{l,l,t}^{Piped}} +\sum\nolimits_{(s,k)∈SKA}\textcolor{red}{F_{l,l,t}^{Piped}}+\sum\nolimits_{(s,k)∈SKT}\textcolor{red}{F_{l,l,t}^{Trucked}}+\sum\nolimits_{(p,k)∈PKT}\textcolor{red}{F_{l,l,t}^{Trucked}}

        +\sum\nolimits_{(p,k)∈CKT}\textcolor{red}{F_{l,l,t}^{Trucked}}+\sum\nolimits_{(r,k)∈RKT}\textcolor{red}{F_{l,l,t}^{Trucked}} =\textcolor{red}{F_{k,t}^{DisposalDestination}}



**Treatment Capacity:**

The total treated water in a given time period must be less than the capacity. If the treatment capacity limits the feasibility, the slack variable will be nonzero, and the treatment capacity will be increased to allow a feasible solution.

∀r ∈ R, t ∈ T

.. math::

    \sum\nolimits_{(n,r)∈NRA}\textcolor{red}{F_{l,l,t}^{Piped}} +\sum\nolimits_{(s,r)∈SRA}\textcolor{red}{F_{l,l,t}^{Piped}}+\sum\nolimits_{(p,r)∈PRT}\textcolor{red}{F_{l,l,t}^{Trucked}}

        +\sum\nolimits_{(p,r)∈CRT}\textcolor{red}{F_{l,l,t}^{Trucked}}≤\textcolor{green}{σ_{r}^{Treatment}}+\textcolor{red}{S_{r}^{TreatmentCapacity}}

∀r ∈ R, t ∈ T

.. math::

    \sum\nolimits_{(n,r)∈NRA}\textcolor{red}{F_{l,l,t}^{Piped}} +\sum\nolimits_{(s,r)∈SRA}\textcolor{red}{F_{l,l,t}^{Piped}}+\sum\nolimits_{(p,r)∈PRT}\textcolor{red}{F_{l,l,t}^{Trucked}}

        +\sum\nolimits_{(p,r)∈CRT}\textcolor{red}{F_{l,l,t}^{Trucked}}=\textcolor{red}{F_{r,t}^{TreatmentDestination}}


**Beneficial Reuse Capacity:**

The total water for beneficial reuse in a given time period must be less than the capacity. If the beneficial reuse capacity limits the feasibility, the slack variable will be nonzero, and the beneficial reuse capacity will be increased to allow a feasible solution.

∀o ∈ O, t ∈ T

.. math::

    \sum\nolimits_{(n,o)∈NOA}\textcolor{red}{F_{l,l,t}^{Piped}} +\sum\nolimits_{(s,o)∈SOA}\textcolor{red}{F_{l,l,t}^{Piped}} +\sum\nolimits_{(p,o)∈POT}\textcolor{red}{F_{l,l,t}^{Trucked}} ≤\textcolor{green}{σ_{o}^{Reuse}}+\textcolor{red}{S_{o}^{ReuseCapacity}}

∀o ∈ O, t ∈ T

.. math::

    \sum\nolimits_{(n,o)∈NOA}\textcolor{red}{F_{l,l,t}^{Piped}} +\sum\nolimits_{(s,o)∈SOA}\textcolor{red}{F_{l,l,t}^{Piped}} +\sum\nolimits_{(p,o)∈POT}\textcolor{red}{F_{l,l,t}^{Trucked}} =\textcolor{red}{F_{o,t}^{BeneficialReuseDestination}}


**Fresh Sourcing Cost:**  ∀f ∈ F, p ∈ CP, t ∈ T

For each freshwater source, for each completions pad, and for each time period, the freshwater sourcing cost is equal to all output from the freshwater source times the freshwater sourcing cost.

.. math::

    \textcolor{red}{C_{f,p,t}^{Sourced}} =(\textcolor{red}{F_{f,p,t}^{Sourced}}+\textcolor{red}{F_{f,p,t}^{Trucked}})⋅\textcolor{green}{π_{f}^{Sourcing}}

    \textcolor{red}{C^{TotalSourced}} = \sum\nolimits_{∀t∈T}\sum\nolimits_{(f,p)∈FCA}\textcolor{red}{C_{f,p,t}^{Sourced}}



**Disposal Cost:** ∀k ∈ K, t ∈ T

For each disposal site, for each time period, the disposal cost is equal to all water moved into the disposal site multiplied by the operational disposal cost. Total disposal cost is the sum of disposal costs over all time periods and all disposal sites.

.. math::

       \textcolor{red}{C_{k,t}^{Disposal}} = (\sum\nolimits_{(l,l)∈{NKA,RKA,SKA}}\textcolor{red}{F_{l,l,t}^{Piped}}+\sum\nolimits_{(l,l)∈{PKT,CKT,SKT,RKT}}\textcolor{red}{F_{l,l,t}^{Trucked}})⋅ \textcolor{green}{π_{k}^{Disposal}}

       \textcolor{red}{C^{TotalDisposal}} = \sum\nolimits_{∀t∈T}\sum\nolimits_{k∈K}\textcolor{red}{C_{k,t}^{Disposal}}



**Treatment Cost:** ∀r ∈ R, t ∈ T

For each treatment site, for each time period, the treatment cost is equal to all water moved to the treatment site multiplied by the operational treatment cost. The total treatments cost is the sum of treatment costs over all time periods and all treatment sites.

.. math::

    \textcolor{red}{C_{r,t}^{Treatment}} = (\sum\nolimits_{(l,l)∈{NRA,SRA}}\textcolor{red}{F_{l,l,t}^{Piped}}+\sum\nolimits_{(l,l)∈{PRT,CRT}}\textcolor{red}{F_{l,l,t}^{Trucked}})⋅ \textcolor{green}{π_{r}^{Treatment}}

    \textcolor{red}{C^{TotalTreatment}} = \sum\nolimits_{∀t∈T}\sum\nolimits_{r∈R}\textcolor{red}{C_{r,t}^{Treatment}}

**Unused Treated Water Cost:** ∀r ∈ R, t ∈ T

For each treatment site, for each time period, the unused treated water cost is equal to all water not used after treating multiplied by the highest disposal cost. The total unused treated water cost is the sum of unused treated water costs over all time periods and all treatment sites.

.. math::

    \textcolor{red}{C_{r,t}^{UnusedTreatedWater}} = \textcolor{red}{F_{r,t}^{UnusedTreatedWater}}⋅ Max_{∀k∈K}(\textcolor{green}{π_{k}^{Disposal}})

    \textcolor{red}{C^{TotalUnusedTreatedWater}} = \sum\nolimits_{∀t∈T}\sum\nolimits_{r∈R}\textcolor{red}{C_{r,t}^{UnusedTreatedWater}}


**Treatment Balance:** ∀r ∈ R, t ∈ T

Water input into treatment facility is treated with a level of efficiency, meaning only a given percentage of the water input is outputted to be reused at the completions pads.

.. math::

    \textcolor{green}{ϵ^{Treatment}}⋅(\sum\nolimits_{(n,r)∈NRA}\textcolor{red}{F_{l,l,t}^{Piped}}+\sum\nolimits_{(s,r)∈SRA}\textcolor{red}{F_{l,l,t}^{Piped}}+\sum\nolimits_{(p,r)∈PRT}\textcolor{red}{F_{l,l,t}^{Trucked}}

        +\sum\nolimits_{(p,r)∈CRT}\textcolor{red}{F_{l,l,t}^{Trucked}} )=\sum\nolimits_{(r,p)∈RCA}\textcolor{red}{F_{l,l,t}^{Piped}} + \textcolor{red}{F_{r,t}^{UnusedTreatedWater}}

where :math:`\textcolor{green}{ϵ^{Treatment}}` <1



**Completions Reuse Cost:** ∀p ∈ P, t ∈ T

Completions reuse water is all water that meets completions pad demand, excluding freshwater. Completions reuse cost is the volume of completions reused water multiplied by the cost for reuse.

.. math::

    \textcolor{red}{C_{p,t}^{CompletionsReuse}} = (\sum\nolimits_{(n,p)∈NCA}\textcolor{red}{F_{l,l,t}^{Piped}}+\sum\nolimits_{(p,p)∈PCA}\textcolor{red}{F_{l,l,t}^{Piped}}+\sum\nolimits_{(r,p)∈RCA}\textcolor{red}{F_{l,l,t}^{Piped}}

        +\sum\nolimits_{(s,p)∈SCA}\textcolor{red}{F_{l,l,t}^{Piped}}+\sum\nolimits_{(p,c)∈CCA}\textcolor{red}{F_{l,l,t}^{Piped}}+\sum\nolimits_{(p,p)∈CCT}\textcolor{red}{F_{l,l,t}^{Trucked}}

        +\sum\nolimits_{(p,p)∈PCT}\textcolor{red}{F_{l,l,t}^{Trucked}}+\sum\nolimits_{(s,p)∈SCT}\textcolor{red}{F_{l,l,t}^{Trucked}})⋅ \textcolor{green}{π_{p}^{CompletionsReuse}}


.. note:: Freshwater sourcing is excluded from completions reuse costs.

.. math::

    \textcolor{red}{C^{TotalCompletionsReuse}} = \sum\nolimits_{∀t∈T}\sum\nolimits_{p∈CP}\textcolor{red}{C_{p,t}^{CompletionsReuse}}



**Piping Cost:** ∀(l,l) ∈ {PPA,…,CCA}, t ∈ T

Piping cost is the total volume of piped water multiplied by the cost for piping.

.. math::

    \textcolor{red}{C_{l,l,t}^{Piped}} = (\textcolor{red}{F_{l,l,t}^{Piped}}+\textcolor{red}{F_{l,l,t}^{Sourced}})⋅ \textcolor{green}{π_{l,l}^{Pipeline}}

    \textcolor{red}{C^{TotalPiping}} = \sum\nolimits_({t∈T}\sum\nolimits_{∀(l,l)∈{PPA,…}}\textcolor{red}{C_{l,l,t}^{Piped}}


.. note:: The constraints above explicitly consider freshwater piping via FCA arcs.



**Storage Deposit Cost:** ∀s ∈ S, t ∈ T

Cost of depositing into storage is equal to the total volume of water moved into storage multiplied by the storage operation cost rate.

.. math::

    \textcolor{red}{C_{s,t}^{Storage}} = (\sum\nolimits_{(l,l)∈{NSA}}\textcolor{red}{F_{l,l,t}^{Piped}}+\sum\nolimits_{(l,l)∈{CST}}\textcolor{red}{F_{l,l,t}^{Trucked}}+\sum\nolimits_{(l,s)∈{PST}}\textcolor{red}{F_{l,s,t}^{Trucked}})⋅ \textcolor{green}{π_{s}^{Storage}}

    \textcolor{red}{C^{TotalStorage}} = \sum\nolimits_{∀t∈T}\sum\nolimits_{∀s∈S}\textcolor{red}{C_{s,t}^{Storage}}



**Storage Withdrawal Credit:** ∀s ∈ S, t ∈ T

Credits from withdrawing from storage is equal to the total volume of water moved out from storage multiplied by the storage operation credit rate.

.. math::

    \textcolor{red}{R_{s,t}^{Storage}} = (\sum\nolimits_{(l,l)∈{SNA,SCA,SKA,SRA,SOA}}\textcolor{red}{F_{l,l,t}^{Piped}}+\sum\nolimits_{(l,l)∈{SCT,SKT}}\textcolor{red}{F_{l,l,t}^{Trucked}})⋅ \textcolor{green}{ρ_{s}^{Storage}}

    \textcolor{red}{R^{TotalStorage}} = \sum\nolimits_{∀t∈T}\sum\nolimits_{∀s∈S}\textcolor{red}{R_{s,t}^{Storage}}



**Pad Storage Cost:** ∀l ∈ L, l ̃ ∈ L, t ∈ T

.. math::

    \textcolor{red}{C^{TotalPadStorage}} = \sum\nolimits_{∀t∈T}\sum\nolimits_{∀p∈CP}\textcolor{red}{z_{p,t}^{PadStorage}}⋅\textcolor{green}{π_{p,t}^{PadStorage}}


**Trucking Cost (Simplified)**

Trucking cost between two locations for time period is equal to the trucking volume between locations in time t divided by the truck capacity [this gets # of truckloads] multiplied by the lead time between two locations and hourly trucking cost.

.. math::

    \textcolor{red}{C_{l,l ̃  ,t}^{Trucked}} = \textcolor{red}{F_{l,l ̃,t}^{Trucked}}⋅\textcolor{green}{1⁄δ^{Truck}}⋅\textcolor{green}{τ_{p,p}^{Trucking}}⋅\textcolor{green}{π_{l}^{Trucking}}

    \textcolor{red}{C^{TotalTrucking}} = \sum\nolimits_{∀t∈T}\sum\nolimits_{∀(l,l)∈{PPA,…,CCT}}\textcolor{red}{C_{l,l ̃  ,t}^{Trucked}}


.. note:: The constraints above explicitly consider freshwater trucking via FCT arcs.



**Slack Costs:**

Weighted sum of the slack variables. In the case that the model is infeasible, these slack variables are used to determine where the infeasibility occurs (e.g. pipeline capacity is not sufficient).

.. math::

    \textcolor{red}{C^{Slack}} = \sum\nolimits_{p∈CP}\sum\nolimits_{t∈T}\textcolor{red}{S_{p,t}^{FracDemand}}⋅\textcolor{green}{ψ^{FracDemand}}+\sum\nolimits_{p∈PP}\sum\nolimits_{t∈T}\textcolor{red}{S_{p,t}^{Production}} ⋅\textcolor{green}{ψ^{Production}}

        +\sum\nolimits_{p∈CP}\sum\nolimits_{t∈T}\textcolor{red}{S_{p,t}^{Flowback}}⋅\textcolor{green}{ψ^{Flowback}}+\sum\nolimits_{(l,l)∈{…}}\textcolor{red}{S_{l,l}^{PipelineCapacity}} ⋅\textcolor{green}{ψ^{PipeCapacity}}

         +\sum\nolimits_{s∈S}\textcolor{red}{S_{s}^{StorageCapacity}} ⋅\textcolor{green}{ψ^{StorageCapacity}}+\sum\nolimits_{k∈K}\textcolor{red}{S_{k}^{DisposalCapacity}}⋅\textcolor{green}{ψ^{DisposalCapacity}}

         +\sum\nolimits_{r∈R}\textcolor{red}{S_{r}^{TreatmentCapacity}} ⋅\textcolor{green}{ψ^{TreatmentCapacity}}+\sum\nolimits_{o∈O}\textcolor{red}{S_{o}^{BeneficialReuseCapacity}} ⋅\textcolor{green}{ψ^{BeneficialReuseCapacity}}

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

:math:`\textcolor{blue}{w ∈ W}`			 Water Quality Components (e.g., TDS)


**Water Quality Parameters**

:math:`\textcolor{green}{v_{l,w,[t]}}` = 	   Water quality at well pad

:math:`\textcolor{green}{ξ_{l,w}}` = 	       Initial water quality at storage


**Water Quality Variables**

:math:`\textcolor{red}{Q_{l,w,t}}` =           Water quality at location


**Disposal Site Water Quality** ∀k ∈ K, w ∈ W, t ∈ T

The water quality of disposed water is dependent on the flow rates into the disposal site and the quality of each of these flows.

.. math::

    \sum\nolimits_{(n,k)∈NKA}\textcolor{purple}{F_{l,l,t}^{Piped}}⋅\textcolor{red}{Q_{n,w,t}} +\sum\nolimits_{(s,k)∈SKA}\textcolor{purple}{F_{l,l,t}^{Piped}}⋅\textcolor{red}{Q_{s,w,t}}+\sum\nolimits_{(r,k)∈RKA}\textcolor{purple}{F_{l,l,t}^{Piped}}⋅\textcolor{red}{Q_{r,w,t}}

    +\sum\nolimits_{(s,k)∈SKT}\textcolor{purple}{F_{l,l,t}^{Trucked}}⋅\textcolor{red}{Q_{s,w,t}}+\sum\nolimits_{(p,k)∈PKT}\textcolor{purple}{F_{l,l,t}^{Trucked}}⋅\textcolor{red}{Q_{p,w,t}}

    +\sum\nolimits_{(p,k)∈CKT}\textcolor{purple}{F_{l,l,t}^{Trucked}}⋅\textcolor{red}{Q_{p,w,t}}+\sum\nolimits_{(r,k)∈RKT}\textcolor{purple}{F_{l,l,t}^{Trucked}}⋅\textcolor{red}{Q_{r,w,t}}

    =\textcolor{purple}{F_{k,t}^{DisposalDestination}}⋅\textcolor{red}{Q_{k,w,t}}

**Storage Site Water Quality** ∀s ∈ S, w ∈ W, t ∈ T

The water quality at storage sites is dependent on the flow rates into the storage site, the volume of water in storage in the previous time period, and the quality of each of these flows. Even mixing is assumed, so all outgoing flows have the same water quality. If it is the first time period, the initial storage level and initial water quality replaces the water stored and water quality in the previous time period respectively.

.. math::

    \textcolor{green}{λ_{s,t=1}^{Storage}}⋅\textcolor{green}{ξ_{s,w}} +\textcolor{purple}{L_{s,t-1}^{Storage}}⋅\textcolor{red}{Q_{s,w,t-1}} +\sum\nolimits_{(n,s)∈NSA}\textcolor{purple}{F_{l,l,t}^{Piped}}⋅\textcolor{red}{Q_{n,w,t}}

    +\sum\nolimits_{(p,s)∈PST}\textcolor{purple}{F_{l,l,t}^{Trucked}}⋅\textcolor{red}{Q_{p,w,t}} +\sum\nolimits_{(p,s)∈CST}\textcolor{purple}{F_{l,l,t}^{Trucked}}⋅\textcolor{red}{Q_{p,w,t}}

    = \textcolor{red}{Q_{s,w,t}}⋅(\textcolor{purple}{L_{s,t}^{Storage}} +\sum\nolimits_{(s,n)∈SNA}\textcolor{purple}{F_{l,l,t}^{Piped}}+\sum\nolimits_{(s,p)∈SCA}\textcolor{purple}{F_{l,l,t}^{Piped}}+\sum\nolimits_{(s,k)∈SKA}\textcolor{purple}{F_{l,l,t}^{Piped}}

    +\sum\nolimits_{(s,r)∈SRA}\textcolor{purple}{F_{l,l,t}^{Piped}}+\sum\nolimits_{(s,o)∈SOA}\textcolor{purple}{F_{l,l,t}^{Piped}}+\sum\nolimits_{(s,p)∈SCT}\textcolor{purple}{F_{l,l,t}^{Trucked}}+\sum\nolimits_{(s,k)∈SKT}\textcolor{purple}{F_{l,l,t}^{Trucked}})

**Treatment Site Water Quality** ∀r ∈ R, w ∈ W, t ∈ T

The water quality at treatment sites is dependent on the flow rates into the treatment site, the efficiency of treatment, and the water quality of the flows. Even mixing is assumed, so all outgoing flows have the same water quality. The treatment process does not affect water quality

.. math::

    \textcolor{green}{ϵ_{r,w}^{Treatment}}⋅(\sum\nolimits_{(n,r)∈NRA}\textcolor{purple}{F_{l,l,t}^{Piped}}⋅\textcolor{red}{Q_{n,w,t}} +\sum\nolimits_{(s,r)∈SRA}\textcolor{purple}{F_{l,l,t}^{Piped}}⋅\textcolor{red}{Q_{s,w,t}}

    +\sum\nolimits_{(p,r)∈PRT}\textcolor{purple}{F_{l,l,t}^{Trucked}}⋅\textcolor{red}{Q_{p,w,t}} +\sum\nolimits_{(p,r)∈CRT}\textcolor{purple}{F_{l,l,t}^{Trucked}}⋅\textcolor{red}{Q_{p,w,t}} )

    = \textcolor{red}{Q_{r,w,t}}⋅(\sum\nolimits_{(r,p)∈RCA}\textcolor{purple}{F_{l,l,t}^{Piped}} + \textcolor{purple}{F_{r,t}^{UnusedTreatedWater}})

where :math:`\textcolor{green}{ϵ_{r,w}^{Treatment}}` <1

**Network Node Water Quality** ∀n ∈ N, w ∈ W, t ∈ T

The water quality at nodes is dependent on the flow rates into the node and the water quality of the flows. Even mixing is assumed, so all outgoing flows have the same water quality.

.. math::

    \sum\nolimits_{(p,n)∈PNA}\textcolor{purple}{F_{l,l,t}^{Piped}}⋅\textcolor{red}{Q_{p,w,t}} +\sum\nolimits_{(p,n)∈CNA}\textcolor{purple}{F_{l,l,t}^{Piped}}⋅\textcolor{red}{Q_{p,w,t}}

    +\sum\nolimits_{(n ̃,n)∈NNA}\textcolor{purple}{F_{l,l,t}^{Piped}}⋅\textcolor{red}{Q_{n,w,t}}+\sum\nolimits_{(s,n)∈SNA}\textcolor{purple}{F_{l,l,t}^{Piped}}⋅\textcolor{red}{Q_{s,w,t}}

    = \textcolor{red}{Q_{n,w,t}}⋅(\sum\nolimits_{(n,n ̃)∈NNA}\textcolor{purple}{F_{l,l,t}^{Piped}} +\sum\nolimits_{(n,p)∈NCA}\textcolor{purple}{F_{l,l,t}^{Piped}}

    +\sum\nolimits_{(n,k)∈NKA}\textcolor{purple}{F_{l,l,t}^{Piped}} +\sum\nolimits_{(n,r)∈NRA}\textcolor{purple}{F_{l,l,t}^{Piped}}

    +\sum\nolimits_{(n,s)∈NSA}\textcolor{purple}{F_{l,l,t}^{Piped}} +\sum\nolimits_{(n,o)∈NOA}\textcolor{purple}{F_{l,l,t}^{Piped}})


**Beneficial Reuse Water Quality** ∀o ∈ O, w ∈ W, t ∈ T

The water quality at beneficial reuse sites is dependent on the flow rates into the site and the water quality of the flows.

.. math::

    \sum\nolimits_{(n,o)∈NOA}\textcolor{purple}{F_{l,l,t}^{Piped}}⋅\textcolor{red}{Q_{n,w,t}} +\sum\nolimits_{(s,o)∈SOA}\textcolor{purple}{F_{l,l,t}^{Piped}}⋅\textcolor{red}{Q_{s,w,t}} +\sum\nolimits_{(p,o)∈POT}\textcolor{purple}{F_{l,l,t}^{Trucked}}⋅\textcolor{red}{Q_{p,w,t}}

    = \textcolor{red}{Q_{o,w,t}}⋅\textcolor{purple}{F_{o,t}^{BeneficialReuseDestination}}


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
