<!-- ![pareto logo](docs/img/logo-print-hd.jpg) -->
<img src="docs/img/logo-print-hd.jpg" width="400px" alg="Project Pareto logo"></img>
# project-pareto
An Optimization Framework for Produced Water Management and Beneficial Reuse

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

The developer installation will install the cloned directory in editable mode (as opposed to the default behavior of installing a copy of it),
which means that any modification made to the code in the cloned directory
(including switching to a different branch with `git switch`/`git checkout`, or updating the directory with `git pull`) will be available when using the package in Python,
regardless of e.g. the current working directory.

To test that the installation was successful, run the test suite using the `pytest` command:

```sh
pytest
```
