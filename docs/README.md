# Building the Sphinx documentation

## Build PDF using Docker

**IMPORTANT**: the following will most likely only work on Linux.

From the `docs/` directory, run:

```sh
docker build . -t pareto/sphinx-latexpdf
docker run --rm -v "$PWD":/docs pareto/sphinx-latexpdf:latest
```

The PDF will be in `_build/latex/pareto.pdf`.
