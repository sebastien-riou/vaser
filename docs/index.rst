Vaser documentation
===================

Vaser is a compact serialization format for sending a sequence of 
values over a byte stream, a file, or an in-memory buffer. The package ships
with both a Python API and a small command-line interface for encoding and
decoding.

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

For local documentation builds:

.. code-block:: console

   ./scripts/build-docs


Alternatively, run Sphinx from the Pipenv environment:

.. code-block:: console

   pipenv run sphinx-build -b html docs docs/_build/html



Testing interoperability
------------------------

The repository also includes a small CLI interoperability script that
verifies the Python and C implementations produce matching encoded output
and decode round-trips correctly.

.. code-block:: console

   pipenv run python test/cli_interop.py --c-impl ./test-vaser 010203 next 0405 last
