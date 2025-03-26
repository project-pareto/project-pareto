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
Provides PARETO specific support for units. This primarily supports
test_strategic_model_unit_consistency in pareto/tests/test_strategic_model.py by providing the
non dimensionless units of all elements in a given expression.
The class PintUnitExtractionVisitor is an altered version of the class of the
same name from pyomo.core.base.units_container.
"""
from pyomo.core.expr.numvalue import (
    native_types,
    pyomo_constant_types,
)

from pyomo.core.expr import current as EXPR
from pyomo.core.base.units_container import _PyomoUnit
from pyomo.environ import units as pyunits


# Return the units container used for strategic/operational model. This is
# needed in test_strategic_model.py and test_operational_model.py for checking
# units consistency.
def get_model_unit_container():
    return pyunits


def units_setup(model):
    """
    Set up units for strategic or operational model.
    """
    try:
        # Check that currency is set to USD
        print("Setting currency to:", pyunits.USD)
    # Exception if USD is not already set and throws Attribute Error
    except AttributeError:
        # Currency base units are not inherently defined by default
        pyunits.load_definitions_from_strings(["USD = [currency]"])

    # Convert user unit selection to a user_units dictionary
    model.user_units = {}
    for user_input in model.df_parameters["Units"]:
        # Concentration is a relationship between two units, so requires some manipulation from user input
        if user_input == "concentration":
            split = model.df_parameters["Units"][user_input].split("/")
            mass = split[0]
            vol = split[1]
            exec(
                "model.user_units['concentration'] = pyunits.%s / pyunits.%s"
                % (mass, vol)
            )
        # Pyunits defines oil_bbl separately from bbl. Users will see 'bbl', but pyunits are defined in oil_bbl
        elif user_input == "volume":
            user_volume = model.df_parameters["Units"][user_input]
            if user_volume == "bbl":
                exec("model.user_units['volume'] = pyunits.%s" % ("oil_bbl"))
            elif user_volume == "kbbl":
                exec("model.user_units['volume'] = pyunits.%s" % ("koil_bbl"))

        # Decision Period is not a user_unit. We will define this as a separate variable.
        elif user_input == "decision period":
            exec(
                "model.decision_period = pyunits.%s"
                % model.df_parameters["Units"][user_input]
            )
        # All other units can be interpreted directly from user input
        else:
            exec(
                "model.user_units['%s'] = pyunits.%s"
                % (user_input, model.df_parameters["Units"][user_input])
            )

    model.model_units = {
        "volume": pyunits.koil_bbl,
        "distance": pyunits.mile,
        "diameter": pyunits.inch,
        "concentration": pyunits.kg / pyunits.liter,
        "currency": pyunits.kUSD,
        "pressure": pyunits.kpascal,
        "elevation": pyunits.meter,
        "mass": pyunits.kg,
        "time": model.decision_period,
    }

    # Units that are most helpful for troubleshooting
    model.unscaled_model_display_units = {
        "volume": pyunits.oil_bbl,
        "distance": pyunits.mile,
        "diameter": pyunits.inch,
        "concentration": pyunits.mg / pyunits.liter,
        "currency": pyunits.USD,
        "pressure": pyunits.pascal,
        "elevation": pyunits.meter,
        "mass": pyunits.g,
        "time": model.decision_period,
    }

    # Defining compound units - user units
    model.user_units["volume_time"] = (
        model.user_units["volume"] / model.user_units["time"]
    )
    model.user_units["currency_time"] = (
        model.user_units["currency"] / model.user_units["time"]
    )
    model.user_units["pipe_cost_distance"] = model.user_units["currency"] / (
        model.user_units["diameter"] * model.user_units["distance"]
    )
    model.user_units["pipe_cost_capacity"] = model.user_units["currency"] / (
        model.user_units["volume"] / model.user_units["time"]
    )
    model.user_units["currency_volume"] = (
        model.user_units["currency"] / model.user_units["volume"]
    )
    model.user_units["currency_volume_time"] = (
        model.user_units["currency"] / model.user_units["volume_time"]
    )

    # Defining compound units - model units
    model.model_units["volume_time"] = (
        model.model_units["volume"] / model.decision_period
    )
    model.model_units["currency_time"] = (
        model.model_units["currency"] / model.decision_period
    )
    model.model_units["pipe_cost_distance"] = model.model_units["currency"] / (
        model.model_units["diameter"] * model.model_units["distance"]
    )
    model.model_units["pipe_cost_capacity"] = model.model_units["currency"] / (
        model.model_units["volume"] / model.decision_period
    )
    model.model_units["currency_volume"] = (
        model.model_units["currency"] / model.model_units["volume"]
    )
    model.model_units["currency_volume_time"] = (
        model.model_units["currency"] / model.model_units["volume_time"]
    )

    # Defining compound units - unscaled model display units
    model.unscaled_model_display_units["volume_time"] = (
        model.unscaled_model_display_units["volume"] / model.decision_period
    )
    model.unscaled_model_display_units["currency_time"] = (
        model.unscaled_model_display_units["currency"] / model.decision_period
    )
    model.unscaled_model_display_units[
        "pipe_cost_distance"
    ] = model.unscaled_model_display_units["currency"] / (
        model.unscaled_model_display_units["diameter"]
        * model.unscaled_model_display_units["distance"]
    )
    model.unscaled_model_display_units[
        "pipe_cost_capacity"
    ] = model.unscaled_model_display_units["currency"] / (
        model.unscaled_model_display_units["volume"] / model.decision_period
    )
    model.unscaled_model_display_units["currency_volume"] = (
        model.unscaled_model_display_units["currency"]
        / model.unscaled_model_display_units["volume"]
    )
    model.unscaled_model_display_units["currency_volume_time"] = (
        model.unscaled_model_display_units["currency"]
        / model.unscaled_model_display_units["volume_time"]
    )

    # Create dictionary to map model units to user units to assist generating results in the user units
    model.model_to_user_units = {}
    for unit in model.model_units:
        model_unit = model.model_units[unit].to_string()
        if "/" in model_unit:
            model_unit = "(" + model_unit + ")"
        user_unit = model.user_units[unit]
        model.model_to_user_units[model_unit] = user_unit

    # Create dictionary to map model units to user units to assist generating results in units relative to time discretization
    model.model_to_unscaled_model_display_units = {}
    for unit in model.model_units:
        model_unit = model.model_units[unit].to_string()
        if "/" in model_unit:
            model_unit = "(" + model_unit + ")"
        developer_output = model.unscaled_model_display_units[unit]
        model.model_to_unscaled_model_display_units[model_unit] = developer_output


class PintUnitExtractionVisitor(EXPR.StreamBasedExpressionVisitor):
    def __init__(self, pyomo_units_container):
        """
        Visitor class used to determine units of an expression. This class is
        adapted from pyomo.core.base.units_container PintUnitExtractionVisitor.
        Parameters
        ----------
        pyomo_units_container : PyomoUnitsContainer
           Instance of the PyomoUnitsContainer that was used for the units
           in the expressions. Pyomo does not support "mixing" units from
           different containers

        Notes
        -----
        This class inherits from the :class:`StreamBasedExpressionVisitor` to implement
        a walker that returns the pyomo units and pint units corresponding to an
        expression.
        """
        super(PintUnitExtractionVisitor, self).__init__()
        self._pyomo_units_container = pyomo_units_container
        self._equivalent_pint_units = pyomo_units_container._equivalent_pint_units
        self._equivalent_to_dimensionless = (
            pyomo_units_container._equivalent_to_dimensionless
        )

    def exitNode(self, node, data):
        """Callback for :class:`pyomo.core.current.StreamBasedExpressionVisitor`. This
        method is called when moving back up the tree in a depth first search.
        This class is adapted from pyomo.core.base.units_container. The unit at
        each node is returned."""

        # first check if the node is a leaf
        nodetype = type(node)

        # These nodes are dimensionless,
        # and for PARETO purposes should not return a unit
        # (e.g. dimensionless -1 to represent subtraction)
        if nodetype in native_types or nodetype in pyomo_constant_types:
            return

        if not node.is_expression_type():
            # this is a leaf, but not a native type
            if nodetype is _PyomoUnit:
                return node._get_pint_unit()
            elif hasattr(node, "get_units"):
                pyomo_unit = node.get_units()
                pint_unit = self._pyomo_units_container._get_pint_units(pyomo_unit)
                return pint_unit

        # not a leaf - check if it is a named expression
        if (
            hasattr(node, "is_named_expression_type")
            and node.is_named_expression_type()
        ):
            pint_unit = self._get_unit_for_single_child(node, data)
            return pint_unit

        return data

        raise TypeError(
            "An unhandled expression node type: {} was encountered while retrieving the"
            " units of expression".format(str(nodetype), str(node))
        )

    def _get_unit_for_single_child(self, node, child_units):
        """
        Return (and test) the units corresponding to a unary operation (e.g. negation)
        expression node in the expression tree.

        Parameters
        ----------
        node : Pyomo expression node
            The parent node of the children

        child_units : list
           This is a list of pint units (one for each of the children)

        Returns
        -------
        : pint unit
        """
        assert len(child_units) == 1
        return child_units[0]


def flatten_list(input_list):
    """Returns a single list with all items from the input_list. The input_list
    can be nested lists of any dimension.
    """
    flat_list = []
    while input_list:  # runs until the given list is empty.
        element = input_list.pop()
        # if the element is a list
        if type(element) == list:
            # extend the item to given list
            input_list.extend(element)
        else:
            # otherwise, it is a single element,  add it to the flat list.
            flat_list.append(element)
    return flat_list
