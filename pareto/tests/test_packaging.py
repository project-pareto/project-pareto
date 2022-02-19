from pareto import __version__

import pytest
from packaging.version import Version


class TestVersion:
    @pytest.fixture
    def version(self) -> str:
        return __version__

    @pytest.fixture
    def parsed_version(self, version) -> Version:
        return Version(version)

    @pytest.fixture
    def normalized_version(self, parsed_version: Version) -> str:
        return parsed_version.public

    def test_version_is_unchanged_by_normalization(
        self, version: str, parsed_version: Version, normalized_version: str
    ):
        assert version == normalized_version == str(parsed_version)

    @pytest.fixture
    def n_specified_release_components(self, parsed_version: Version) -> int:
        return len(parsed_version.release)

    @pytest.fixture
    def n_expected_release_components(self, parsed_version: Version) -> int:
        return 2 if parsed_version.is_devrelease else 3

    def test_number_of_specified_release_components(
        self, n_specified_release_components: int, n_expected_release_components: int
    ):
        assert n_specified_release_components == n_expected_release_components
