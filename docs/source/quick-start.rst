Quick Start
===========

While the eVolver server is meant to run on the Raspberry Pi mounted within the
eVolver hardware platform connected via serial to the physical hardware, it is
sometimes desireable to run it locally using dummy hardware for evaluation of
configuration or api calls.

* Install the package using pip::

    pip install git+https://github.com/ssec-jhu/evolver-ng@main

* Run the server process::

    python -m evolver.app.main

* Navigate to the web interface of the openapi docs at http://localhost:8080/docs

From the source code
--------------------

Another way to run the server is in development mode via the code repository.
This uses `tox` to run in a virtual environment, resolving and isolating all
dependencies, and can be used if you are modifying any of the code.

* Clone the repository::

    git clone https://github.com/ssec-jhu/evolver-ng
    cd evolver-ng

* Install tox, if you don't have it already::

    pip install -r requirements/dev.txt

* Run the server process::

    tox -e dev

This starts the server in the same manner as above, but using the virtual
environment via tox and against the local source code.




