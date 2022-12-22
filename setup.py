from setuptools import setup, find_packages


NAME = "project-pareto"
VERSION = "0.5.0"


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
        "idaes-pse",
        "requests",
        "plotly",
        "kaleido",
    ],
    extras_require={
        "testing": [
            "pytest",
            "packaging",  # packaging is already a dependency of pytest, but we specify it here just in case
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
