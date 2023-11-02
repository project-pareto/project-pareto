#####################################################################################################
# PARETO was produced under the DOE Produced Water Application for Beneficial Reuse Environmental
# Impact and Treatment Optimization (PARETO), and is copyright (c) 2021-2023 by the software owners:
# The Regents of the University of California, through Lawrence Berkeley National Laboratory, et al.
# All rights reserved.
#
# NOTICE. This Software was developed under funding from the U.S. Department of Energy and the U.S.
# Government consequently retains certain rights. As such, the U.S. Government has been granted for
# itself and others acting on its behalf a paid-up, nonexclusive, irrevocable, worldwide license in
# the Software to reproduce, distribute copies to the public, prepare derivative works, and perform
# publicly and display publicly, and to permit others to do so.
#####################################################################################################
from setuptools import setup, find_packages


NAME = "project-pareto"
VERSION = "0.9.0"


setup(
    name=NAME,
    version=VERSION,
    description="Project PARETO - The Produced Water Optimization Initiative",
    long_description=(
        "The Produced Water Application for Beneficial Reuse, Environmental Impact and Treatment Optimization (PARETO) "
        "is specifically designed for produced water management and beneficial reuse. "
        "The major deliverable of this project will be an open-source, optimization-based, downloadable and executable produced water decision-support application, PARETO, "
        "that can be run by upstream operators, midstream companies, technology providers, water end users, research organizations and regulators."
    ),
    long_description_content_type="text/plain",
    url="https://www.project-pareto.org",
    author="PARETO team",
    license="BSD",
    maintainer="Keith Beattie",
    maintainer_email="ksbeattie@lbl.gov",
    keywords=[
        "PARETO",
        "produced water",
        "optimization",
        "process modeling",
        "chemical engineering",
        "water management",
    ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: BSD License",
        "Natural Language :: English",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: Unix",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: Implementation :: CPython",
        "Topic :: Scientific/Engineering :: Mathematics",
        "Topic :: Scientific/Engineering :: Chemistry",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Programming Language :: Python :: 3 :: Only",
    ],
    platforms=[
        "windows",
        "linux",
    ],
    python_requires=">=3.8, <4",
    packages=find_packages(),
    py_modules=["stagedfright"],
    install_requires=[
        "pyomo>=6.2",
        "pandas==1.2.*",
        "openpyxl",
        # for the moment mainly for getting solvers with `idaes get-extensions`
        # https://peps.python.org/pep-0440/#compatible-release
        "idaes-pse ~= 2.0",
        "requests",
        "plotly==5.11.0",
        "kaleido",
        "ipywidgets>=8.0.0",
    ],
    extras_require={
        "testing": [
            "pytest",
            "packaging",  # packaging is already a dependency of pytest, but we specify it here just in case
            "pyyaml",
        ],
    },
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
)
