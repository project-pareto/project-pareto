#####################################################################################################
# PARETO was produced under the DOE Produced Water Application for Beneficial Reuse Environmental
# Impact and Treatment Optimization (PARETO), and is copyright (c) 2021-2025 by the software owners:
# The Regents of the University of California, through Lawrence Berkeley National Laboratory, et al.
# All rights reserved.
#
# NOTICE. This Software was developed under funding from the U.S. Department of Energy and the U.S.
# Government consequently retains certain rights. As such, the U.S. Government has been granted for
# itself and others acting on its behalf a paid-up, nonexclusive, irrevocable, worldwide license in
# the Software to reproduce, distribute copies to the public, prepare derivative works, and perform
# publicly and display publicly, and to permit others to do so.
#####################################################################################################
"""
Module with enums for strategic and operational models.

Authors: PARETO Team
"""

from enum import Enum, IntEnum


class Objectives(Enum):
    cost = 0
    reuse = 1
    cost_surrogate = 2
    subsurface_risk = 3
    environmental = 4


class PipelineCapacity(Enum):
    calculated = 0
    input = 1


class PipelineCost(Enum):
    distance_based = 0
    capacity_based = 1


class WaterQuality(Enum):
    false = 0
    post_process = 1
    discrete = 2


class Hydraulics(Enum):
    false = 0
    post_process = 1
    co_optimize = 2
    co_optimize_linearized = 3


class RemovalEfficiencyMethod(Enum):
    load_based = 0
    concentration_based = 1


# Inherit from IntEnum so that these values can be used in comparisons
class TreatmentStreams(IntEnum):
    treated_stream = 1
    residual_stream = 2


class InfrastructureTiming(Enum):
    false = 0
    true = 1


class SubsurfaceRisk(Enum):
    false = 0
    exclude_over_and_under_pressured_wells = 1
    calculate_risk_metrics = 2


class DesalinationModel(Enum):
    false = 0
    mvc = 1
    md = 2


class ProdTank(Enum):
    individual = 0
    equalized = 1
