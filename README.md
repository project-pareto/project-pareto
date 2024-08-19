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

For complete installation instructions, including developer install instructions, see the [Getting Started](https://pareto.readthedocs.io/en/latest/getting_started/index.html) page of the [PARETO online documentation](https://pareto.readthedocs.io).

### Quickstart (user install)

The recommended way to install Pareto is to use a dedicated Conda environment.

To install the latest stable release of PARETO, create and activate the Conda environment, then install PARETO using `pip`:

```sh
conda create --yes -n pareto-env python=3.9
conda activate pareto-env
pip install project-pareto
idaes get-extensions --verbose
```

## Resources for PARETO contributors

See the "For developers" pages in the [PARETO GitHub Wiki](https://github.com/project-pareto/project-pareto/wiki).

## How to Cite PARETO software
If you make use of PARETO software in your work, please cite the following article:

```
@article{PARETO_article,
  author  = {Drouven, Markus G. and Caldéron, Andres J. and Zamarripa, Miguel A. and Beattie, Keith},
  title   = {PARETO: An open-source produced water optimization framework},
  journal = {Optimization and Engineering},
  year    = {2023},
  volume  = {24},
  number  = {3},
  pages   = {2229–2249},
  doi     = {https://doi.org/10.1007/s11081-022-09773-w},
}
```

You can also cite the latest release of PARETO software (currently 0.9.0) as follows: 

```
@misc{PARETO_090,
  author = {Shellman, Melody and Arnold, Travis and Bianchi, Ludovico and Shamlou, Elmira and Susarla, Naresh and Tominac, Philip and Pesce, Michael and Poon, Sarah and Beattie, Keith and Zamarripa, Miguel and Gunter, Dan and Drouven, Markus},
  title  = {PARETO 0.9.0 Release},
  month  = {November},
  year   = {2023},
  note   = {https://edx.netl.doe.gov/dataset/pareto-0-9-0-release}
}
```

Citation information for previous versions of PARETO software may be found on [EDX](https://edx.netl.doe.gov/group/pareto).

## Funding Acknowledgement

This work was conducted as part of the Produced Water Optimization Initiative, “Project PARETO”,
with support through the Natural Gas & Oil Program within the U.S. Department of Energy’s Office of
Fossil Energy and Carbon Management (FECM). For more information please see
[www.project-pareto.org](http://www.project-pareto.org/).
