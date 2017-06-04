html5-parser
================

|pypi| |unix_build| |windows_build|

A fast implementation of the `HTML 5 parsing spec
<https://www.w3.org/TR/html5/syntax.html#parsing>`_. Parsing is done in C using
a variant of the `gumbo parser <https://github.com/google/gumbo-parser>`_. The
gumbo parse tree is then transformed into an `lxml <http://lxml.de/>`_ tree, also
in C, yielding parse times that can be **a thirtieth** of the html5lib parse
times. That is a speedup of **30x**.


Installation
--------------

Unix
^^^^^^

On a Unix-y system, with a working compiler, simply run:

.. code-block:: bash

    pip install --no-binary lxml html5-parser

It is important that lxml is installed with the --no-binary flags. This is
because without it, lxml uses a static copy of libxml2. For html5-parser to
work it must use the same libxml2 implementation as lxml. This is only possible
if libxml2 is loaded dynamically.

You can setup html5-parser to run from a source checkout as follows:

.. code-block:: bash

    git clone https://github.com/kovidgoyal/html5-parser && cd html5-parser
    pip install --no-binary lxml 'lxml>=3.8.0' --user
    python setup.py develop --user

Windows
^^^^^^^^

On Windows, installation is a little more involved. There is a 200 line script
that is used to install html5-parser and all its dependencies on the windows
continuous integration server. Using that script installation can be done by
running the following commands in a Visual Studio 2015 Command prompt:


.. code-block:: cmd

    python.exe win-ci.py install_deps
    python.exe win-ci.py test

This will install all dependencies and html5-parser in the ``sw``
sub-directory. You will need to add ``sw\bin`` to ``PATH`` and
``sw\python\Lib\site-packages`` to ``PYTHONPATH``. Or copy the files
into your system python's directories.


Benchmarking
-------------

There is a benchmark script named ``benchmark.py`` that compares the
parse times for parsing a large (~ 5.7MB) HTML document in html5lib and
html5-parser. The results on my system show a speedup of **28x**. The output
from the script on my system is:

.. code-block:: none

    Testing with HTML file of 5,956,815 bytes
    Parsing repeatedly with html5-parser
    html5-parser took an average of : 0.491 seconds to parse it
    Parsing repeatedly with html5lib
    html5lib took an average of : 13.744 seconds to parse it

There is further potential for speedup. Currently the gumbo subsystem uses
its own cache for tag and attribute names and the libxml2 sub-system uses its
own cache. Unifying the two to use the libxml2 cache should yield significant
performance and memory consumption gains.


.. |pypi| image:: https://img.shields.io/pypi/v/html5-parser.svg?label=version
    :target: https://pypi.python.org/pypi/html5-parser
    :alt: Latest version released on PyPi

.. |unix_build| image:: https://api.travis-ci.org/kovidgoyal/html5-parser.svg
    :target: http://travis-ci.org/kovidgoyal/html5-parser
    :alt: Build status of the master branch on Unix

.. |windows_build|  image:: https://ci.appveyor.com/api/projects/status/github/kovidgoyal/html5-parser?svg=true
    :target: https://ci.appveyor.com/project/kovidgoyal/html5-parser
    :alt: Build status of the master branch on Windows
