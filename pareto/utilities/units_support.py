#####################################################################################################
# PARETO was produced under the DOE Produced Water Application for Beneficial Reuse Environmental
# Impact and Treatment Optimization (PARETO), and is copyright (c) 2021 by the software owners: The
# Regents of the University of California, through Lawrence Berkeley National Laboratory, et al. All
# rights reserved.
#
# NOTICE. This Software was developed under funding from the U.S. Department of Energy and the
# U.S. Government consequently retains certain rights. As such, the U.S. Government has been granted
# for itself and others acting on its behalf a paid-up, nonexclusive, irrevocable, worldwide license
# in the Software to reproduce, distribute copies to the public, prepare derivative works, and perform
# publicly and display publicly, and to permit other to do so.
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
