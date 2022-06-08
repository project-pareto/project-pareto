# we use :latest here instead of pinning an image tag since we want to
# simulate what happens on the ReadTheDocs runners
FROM sphinxdoc/sphinx-latexpdf:latest

WORKDIR /docs
RUN pip3 install sphinx_rtd_theme myst-parser nbsphinx

CMD [ "make", "latexpdf" ]
