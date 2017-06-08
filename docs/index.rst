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

It is important that lxml is installed with the ``--no-binary`` flag. This is
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


.. code-block:: bat

    python.exe win-ci.py install_deps
    python.exe win-ci.py test

This will install all dependencies and html5-parser in the :file:`sw`
sub-directory. You will need to add :file:`sw\bin` to :envvar:`PATH` and
:file:`sw\python\Lib\site-packages` to :envvar:`PYTHONPATH`. Or copy the files
into your system python's directories.


Quickstart
-------------

To use html5-parser in your code, after installing it simply do:

.. code-block:: python
    
    from html5_parser import parse
    from lxml import tostring
    root = parse(some_html)
    print(tostring(root))


.. _xhtml:

XHTML
------------

html5-parser has the ability to parse XHTML documents as well. It will
preserve namespace information even for namespaces not defined in the HTML 5
spec. You can ask it to treat the input html as possibly XHTML by using the 
``maybe_xhtml`` parameter to the :function:`parse` function. For example:

.. code-block:: html

    <p xmlns:n="my namespace"><n:tag n:attr="a" />

becomes

.. code-block:: html

    <html>
        <head/>
        <body>
            <p xmlns:n="my namespace">
                <n:tag n:attr="a"/>
            </p>
        </body>
    </html>

This is useful when try to parse a XHTML document that is not well-formed and
so cannot be parsed by a regular XML parser.

API documentation
------------------

The API of html5-parser is a single function, ``parse()``.

.. autofunction:: html5_parser.parse


Comparison with html5lib
-----------------------------

Before doing the actual comparison, let me say that html5lib is a great
project. It was a pioneer of HTML 5 parsing and I have used it myself for many
years. However, being written in pure python, it cannot help but be slow.

Benchmarks
^^^^^^^^^^^^^^

There is a benchmark script named `benchmark.py
<https://github.com/kovidgoyal/html5-parser/blob/master/benchmark.py>`_ that
compares the parse times for parsing a large (~ 5.7MB) HTML document in
html5lib and html5-parser. The results on my system (using python 3) show a
speedup of **31x**. The output from the script on my system is:

.. code-block:: none

    Testing with HTML file of 5,956,815 bytes
    Parsing 20 times with html5-parser
    html5-parser took an average of: 0.434 seconds to parse it
    Parsing 20 times with html5lib
    html5lib took an average of: 13.518 seconds to parse it

There is further potential for speedup. Currently the gumbo subsystem uses
its own data structures to store parse results and these are converted to
libxml2 data structures in a second pass after parsing completes. By modifying gumbo
to use libxml2 data structures directly, there could be significant speed and
memory usage gains.

XML namespace handling
^^^^^^^^^^^^^^^^^^^^^^^^

html5lib has truly horrible handling of namespaces. There is even a source-code
file in it named :file:`_ihatexml.py`. Compare the result of parsing and pretty
printing the following simple HTML fragment (pretty printing is done via lxml in both
cases).

.. code-block:: html

    <p>xxx<svg><image xlink:href="xxx"></svg><p>yyy

With **html5lib**:

.. code-block:: html

    <html:html xmlns:html="http://www.w3.org/1999/xhtml">
        <html:head/>
        <html:body>
            <html:p>xxx<ns0:svg xmlns:ns0="http://www.w3.org/2000/svg"><ns0:image xmlns:ns1="http://www.w3.org/1999/xlink" ns1:href="xxx"/></ns0:svg></html:p>
            <html:p>yyy</html:p>
        </html:body>
    </html:html> 

With **html5-parser**:

.. code-block:: html

    <html xmlns="http://www.w3.org/1999/xhtml" xmlns:xlink="http://www.w3.org/1999/xlink">
        <head/>
        <body>
            <p>xxx<svg xmlns="http://www.w3.org/2000/svg"><image xlink:href="xxx"/></svg></p>
            <p>yyy</p>
        </body>
    </html>

While both outputs are technically correct, the output produced via
html5-parser is much easier to read and much closer to what an actual human
would write. In particular, notice the unnecessary use of prefixes in
the html5lib output, as well as the ugly ``ns0`` anonymous prefix for the svg
namespace.

html5-parser also has the ability to optionally preserve namespace information
even for namespaces not defined in the HTML 5 standard. See the :ref:`XHTML`
section for more information.


.. |pypi| image:: https://img.shields.io/pypi/v/html5-parser.svg?label=version
    :target: https://pypi.python.org/pypi/html5-parser
    :alt: Latest version released on PyPi

.. |unix_build| image:: https://api.travis-ci.org/kovidgoyal/html5-parser.svg
    :target: http://travis-ci.org/kovidgoyal/html5-parser
    :alt: Build status of the master branch on Unix

.. |windows_build|  image:: https://ci.appveyor.com/api/projects/status/github/kovidgoyal/html5-parser?svg=true
    :target: https://ci.appveyor.com/project/kovidgoyal/html5-parser
    :alt: Build status of the master branch on Windows
