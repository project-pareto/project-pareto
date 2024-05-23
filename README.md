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
If you are using the current version of the repository, please cite the resource:

```
@misc{https://doi.org/10.18141/2308839,
  doi = {10.18141/2308839},
  url = {https://www.osti.gov/servlets/purl/2308839/},
  author = {Susarla,  Naresh and Arnold,  Travis and Shamlou,  Elmira and Tominac,  Philip and Beattie,  Keith and Zamarripa,  Miguel and Drouven,  Markus and Gunter,  Dan and Bianchi,  Ludovico and Pesce,  Michael and Shellman,  Melody and Poon,  Sarah},
  keywords = {PARETO, PARETO-UI, PSE, Process Systems Engineering, Produced water, Water},
  language = {en},
  title = {PARETO 0.8.0 Release},
  publisher = {National Energy Technology Laboratory - Energy Data eXchange; NETL},
  year = {2023}
}
```

## Funding Acknowledgement

This work was conducted as part of the Produced Water Optimization Initiative, “Project PARETO”,
with support through the Natural Gas & Oil Program within the U.S. Department of Energy’s Office of
Fossil Energy and Carbon Management (FECM). For more information please see
[www.project-pareto.org](http://www.project-pareto.org/).
