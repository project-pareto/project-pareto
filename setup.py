from setuptools import setup, find_packages
from packaging.version import Version


NAME = "project-pareto"
VERSION = "0.1dev1"


def _validate_version(v: str) -> None:
    version_obj = Version(v)
    assert v == version_obj.public
    assert v == str(version_obj)
    n_components_to_specify = 2 if version_obj.is_devrelease else 3
    assert len(version_obj.release) == n_components_to_specify


_validate_version(VERSION)


setup(
    name=NAME,
    version=VERSION,
    packages=find_packages(),
    py_modules=["stagedfright"],
    install_requires=[
        "pyomo>=6.2",
        "pandas==1.2.*",
        "openpyxl",
        # for the moment mainly for getting solvers with `idaes get-extensions`
        "idaes-pse",
        "requests",
        "plotly",
        "kaleido",
    ],
    include_package_data=True,
    package_data={
        # If any package contains these files, include them:
        "": [
            "*.xlsx",
        ]
    },
    entry_points={
        "console_scripts": [
            "stagedfright=stagedfright:main",
        ]
    },
    maintainer="Keith Beattie",
    maintainer_email="ksbeattie@lbl.gov",
    platforms=["any"],
    license="TODO",
    keywords=[
        NAME
        # TODO add keywords
    ],
    classifiers=[
        # TODO add classifiers
    ],
)
