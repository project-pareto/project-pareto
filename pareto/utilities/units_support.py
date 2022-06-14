from pyomo.core.expr.numvalue import (
    native_types,
    pyomo_constant_types,
)

from pyomo.core.expr import current as EXPR
from pyomo.core.base.units_container import _PyomoUnit


class PintUnitExtractionVisitor(EXPR.StreamBasedExpressionVisitor):
    def __init__(self, pyomo_units_container):
        """
        Visitor class used to determine units of an expression. Do not use
        this class directly, but rather use
        "py:meth:`PyomoUnitsContainer.assert_units_consistent`
        or :py:meth:`PyomoUnitsContainer.get_units`
        Parameters
        ----------
        pyomo_units_container : PyomoUnitsContainer
           Instance of the PyomoUnitsContainer that was used for the units
           in the expressions. Pyomo does not support "mixing" units from
           different containers
        units_equivalence_tolerance : float (default 1e-12)
            Floating point tolerance used when deciding if units are equivalent
            or not.
        Notes
        -----
        This class inherits from the :class:`StreamBasedExpressionVisitor` to implement
        a walker that returns the pyomo units and pint units corresponding to an
        expression.
        There are class attributes (dicts) that map the expression node type to the
        particular method that should be called to return the units of the node based
        on the units of its child arguments. This map is used in exitNode.
        """
        super(PintUnitExtractionVisitor, self).__init__()
        self._pyomo_units_container = pyomo_units_container
        self._pint_dimensionless = pyomo_units_container._pint_dimensionless
        self._pint_radian = pyomo_units_container._pint_registry.radian
        self._equivalent_pint_units = pyomo_units_container._equivalent_pint_units
        self._equivalent_to_dimensionless = (
            pyomo_units_container._equivalent_to_dimensionless
        )

    def get_unique(self, child_units):
        """
        Return (and test) the units corresponding to an expression node in the
        expression tree where all children should have the same units (e.g. sum).
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
        # TODO: This may be expensive for long summations and, in the
        # case of reporting only, we may want to skip the checks
        assert bool(child_units)
        unique_units = list()

        for py_unit in child_units:
            unique = True
            for unique_unit in unique_units:
                if self._equivalent_pint_units(unique_unit, py_unit):
                    unique = False
                    break
            if unique:
                unique_units.append(py_unit)
        # verify that the pint units are equivalent from each
        # of the child nodes - assume that PyomoUnits are equivalent

        # checks were OK, return the first one in the list
        return unique_units

    def exitNode(self, node, data):
        """Callback for :class:`pyomo.core.current.StreamBasedExpressionVisitor`. This
        method is called when moving back up the tree in a depth first search."""

        # first check if the node is a leaf
        nodetype = type(node)

        if nodetype in native_types or nodetype in pyomo_constant_types:
            return

        if not node.is_expression_type():
            # this is a leaf, but not a native type
            if nodetype is _PyomoUnit:
                return node._get_pint_unit()
            elif hasattr(node, "get_units"):
                # might want to add other common types here
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

        return self.get_unique(data)  # node_func(self, node, data)

        raise TypeError(
            "An unhandled expression node type: {} was encountered while retrieving the"
            " units of expression".format(str(nodetype), str(node))
        )


def flatten_list(input_list):
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
