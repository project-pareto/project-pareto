<!-- ![pareto logo](docs/img/logo-print-hd.jpg) -->
<img src="docs/img/logo-print-hd.jpg" width="400px" alg="Project Pareto logo"></img>
# project-pareto
An Optimization Framework for Produced Water Management and Beneficial Reuse

## Project Status
[![Checks](https://github.com/project-pareto/project-pareto/actions/workflows/checks.yml/badge.svg)](https://github.com/project-pareto/project-pareto/actions/workflows/checks.yml)
[![codecov](https://codecov.io/gh/project-pareto/project-pareto/branch/main/graph/badge.svg?token=2ZN7V4VA6X)](https://codecov.io/gh/project-pareto/project-pareto)
[![Documentation Status](https://readthedocs.org/projects/pareto/badge/?version=latest)](https://pareto.readthedocs.io/en/latest/?badge=latest)
[![Contributors](https://img.shields.io/github/contributors/project-pareto/project-pareto?style=plastic)](https://github.com/project-pareto/project-pareto/contributors)
[![Merged PRs](https://img.shields.io/github/issues-pr-closed-raw/project-pareto/project-pareto.svg?label=merged+PRs)](https://github.com/project-pareto/project-pareto/pulls?q=is:pr+is:merged)
[![Issue stats](http://isitmaintained.com/badge/resolution/project-pareto/project-pareto.svg)](http://isitmaintained.com/project/project-pareto/project-pareto)
[![Downloads](https://pepy.tech/badge/project-pareto)](https://pepy.tech/project/project-pareto)

## Getting started

### Creating a Conda environment

The recommended way to install Pareto is to use a Conda environment.

A Conda environment is a separate installation directory where packages and even different Python versions can be installed
without conflicting with other Python versions installed on the system, or other environments.

To create a Conda environment, the `conda` command should be installed and configured for your operating system.
Detailed steps to install and configure `conda` are available [here](https://conda.io/projects/conda/en/latest/user-guide/install/index.html).

### For users

Create a Conda environment:

```sh
conda create -n pareto-env python=3.8 pip --yes
conda activate pareto-env
```

Install the latest version from the repository's `main` branch:

```sh
pip install 'project_pareto @ https://github.com/project-pareto/project-pareto/archive/main.zip`
```

Install the open-source solvers packaged by the IDAES project:

```sh
idaes get-extensions --verbose
```

Open a Python shell and test that the `pareto` package was installed correctly:

```sh
python
>>> import pareto
```

### For developers

(Recommended) Create a dedicated Conda environment for development work:

```sh
conda create -n pareto-dev python=3.8 pip --yes
conda activate pareto-dev
```

Clone the repository and enter the `project-pareto` directory:

```sh
git clone https://github.com/project-pareto/project-pareto
cd project-pareto
```

Install the Python package using pip and the `requirements-dev.txt` file:

```sh
pip install -r requirements-dev.txt
```

Install the pre-commit checks that will run automatically whenever `git commit` is used, preventing the commit from being created if any of the checks fail:

```sh
pre-commit install
```

Install the open-source solvers packaged by the IDAES project:

```sh
idaes get-extensions --verbose
```

To test that the installation was successful, run the test suite using the `pytest` command:

```sh
pytest --verbose
```

## Notes for developers

### Editable installation with pip

The developer installation will install the Python packages and modules found in the cloned directory in editable mode (as opposed to the default behavior of installing a copy of it),
which means that any modification made to the code in the cloned directory
(including switching to a different branch with `git switch`/`git checkout`, or updating the directory with `git pull`) will be available when using the package in Python,
regardless of e.g. the current working directory.

### Formatting code with Black

Black (https://black.readthedocs.io) is the code formatter used by Pareto to ensure that the codebase is formatted consistently.

#### Installation

Black is part of the Pareto developer dependencies and it is installed alongside the other dependencies when running `pip install -r requirements-dev.txt` in the Conda environment used for development.

To verify that Black is installed correctly, run e.g.:

```sh
black --version
```

#### Usage

Before committing code to the Pareto repository, run `black` locally (i.e. on your development machine) with the default options from the repository root:

```sh
black .
```

#### Automated check

When a PR is created or updated, as part of the automated check suite running on GitHub, Black will run in "check mode": rather than formatting files, it will check if any file would need to be formatted, and exiting with an error if this is the case.

To reproduce this check locally (e.g. to verify that your code would pass this check when enforced on the GitHub side), from the root of the repository, run:

```sh
black --check .
```

**NOTE**: This is now done automatically as part of the pre-commit checks (see above).


## Funding Acknowledgement

This work was conducted as part of the Produced Water Optimization Initiative, “Project PARETO”,
with support through the Natural Gas & Oil Program within the U.S. Department of Energy’s Office of
Fossil Energy and Carbon Management (FECM). For more information please see
[www.project-pareto.org](http://www.project-pareto.org/).
