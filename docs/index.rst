Vaser documentation
===================

Vaser is a compact serialization format for sending a sequence of integer
values over a byte stream, a file, or an in-memory buffer. The package ships
with both a Python API and a small command-line interface for encoding and
decoding chunks.

The documentation below covers:

- the Python API exposed by :class:`vaser.Vaser`
- the command-line interface for encoding and decoding data
- the serialized format used on the wire

.. toctree::
   :maxdepth: 2
   :caption: Contents

   api
   cli
   format

Installation
------------

Install the package from a checkout of the repository with Pipenv:

.. code-block:: console

   pipenv install --dev

For local documentation builds, run Sphinx from the Pipenv environment:

.. code-block:: console

   pipenv run sphinx-build -b html docs docs/_build/html
