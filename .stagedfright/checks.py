"""
These checks are used by stagedfright to determine whether a staged file is cleared for commit or not.
The check suite should be optimized and optimized based on the features of the specific sensitive data formats and features being handled.
For more information, see the README.md file in this directory.
"""

import ast
import numbers
from pathlib import Path
from typing import List, Dict

import pytest
from stagedfright import StagedFile, AllowFile, PyContent


def test_allowfile_matches_if_present(staged: StagedFile, allowfile: AllowFile):
    assert (
        staged.fingerprint == allowfile.fingerprint
    ), f"An allowfile must contain a matching fingerprint for a staged file to be cleared for commit"


MAP_PATH_EXPECTED_HARDCODED_DATA_COUNT = {
    "pareto/operational_water_management/run_operational_model.py": 5,
    "pareto/operational_water_management/operational_produced_water_optimization_model.py": 85,
    "pareto/strategic_water_management/run_strategic_model.py": 7,
    "pareto/strategic_water_management/run_strategic_model_water_quality.py": 7,
    "pareto/strategic_water_management/strategic_produced_water_optimization.py": 375,
    "pareto/tests/test_operational_model.py": 15,
    "pareto/utilities/get_data.py": 24,
    "pareto/utilities/results.py": 194,
    "pareto/tests/test_strategic_model.py": 54,
    "pareto/tests/test_solvers.py": 31,
    "pareto/tests/test_plot_scatter.py": 8,
    "pareto/tests/test_plot_sankey.py": 3,
}

# this is meta, two levels deep:
# - this file is also included checked by stagedfright,
#   so the hardcoded data used to define this mapping must be counted,
# - the extra number accounts for constants defined below,
#   plus 1 for the fact that this number itself is defined using a constant
MAP_PATH_EXPECTED_HARDCODED_DATA_COUNT[".stagedfright/checks.py"] = (
    len(MAP_PATH_EXPECTED_HARDCODED_DATA_COUNT) + 3
)


@pytest.mark.usefixtures("skip_if_matching_allowfile")
class TestIsClearedForCommit:
    def test_has_py_path_suffix(self, staged: StagedFile):
        assert staged.suffix in {
            ".py"
        }, "Only files with a 'py' extension may be cleared for commit"

    def test_is_text_file(self, staged: StagedFile):
        assert (
            staged.text_content is not None
        ), "Only source (text) files may be cleared for commit"

    def test_has_meaningful_python_code(self, staged_pycontent: PyContent):
        assert len(staged_pycontent.ast_nodes.essential) >= 2

    @pytest.fixture
    def hardcoded_data_definitions(self, staged_pycontent: PyContent) -> List[ast.AST]:
        return [
            n
            for n in staged_pycontent.ast_nodes.literal
            if isinstance(n.value, numbers.Number) and n.value != 0
        ]

    @pytest.fixture
    def hardcoded_data_count(self, hardcoded_data_definitions: List[ast.AST]) -> int:
        return len(hardcoded_data_definitions)

    @pytest.fixture
    def _mapping_with_normalized_paths(self) -> Dict[str, int]:
        # paths must be normalized (here, by using pathlib.Path objects instead of str)
        # so that the same key in the mapping can be matched on both UNIX and Windows
        return {Path(k): v for k, v in MAP_PATH_EXPECTED_HARDCODED_DATA_COUNT.items()}

    @pytest.fixture
    def expected_hardcoded_data_count(
        self,
        staged: StagedFile,
        _mapping_with_normalized_paths: Dict[str, int],
    ) -> int:
        key = Path(staged)
        return int(_mapping_with_normalized_paths.get(key, 0))

    def test_py_module_has_no_unexpected_hardcoded_data(
        self,
        hardcoded_data_count: int,
        expected_hardcoded_data_count: int,
        max_added_count=2,
    ):
        assert hardcoded_data_count <= (expected_hardcoded_data_count + max_added_count)
