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


API documentation
------------------

The API of html5-parser is a single function, ``parse()``.

.. function:: html5_parser.parse(html, \
    transport_encoding=None, \
    namespace_elements=False,
    fallback_encoding=None, \
    keep_doctype=True, \
    maybe_xhtml=False, \
    stack_size=16 * 1024)

    Parse the specified :attr:`html` and return the parsed representation.

    :param html: The HTML to be parsed. Can be either bytes or a unicode string.

    :param transport_encoding: If specified, assume the passed in bytes are in this encoding.
        Ignored if :attr:`html` is unicode.

    :param namespace_elements:
        Add XML namespaces when parsing so that the resulting tree is XHTML.

    :param fallback_encoding: If no encoding could be detected, then use this encoding.
        Defaults to an encoding based on system locale.

    :param keep_doctype: Keep the <DOCTYPE> (if any).

    :param maybe_xhtml: Useful when it is unknown if the HTML to be parsed is
        actually XHTML. Changes the HTML 5 parsing algorithm to be more
        suitable for XHTML. In particular handles self-closed CDATA elements.
        So a ``<title/>`` or ``<style/>`` in the HTML will not completely break
        parsing.

    :param stack_size: The initial size (number of items) in the stack. The
        default is sufficient to avoid memory allocations for all but the
        largest documents.

Benchmarking
-------------

There is a benchmark script named `benchmark.py
<https://github.com/kovidgoyal/html5-parser/blob/master/benchmark.py>`_ that compares the
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
its own data structures to store parse results and these are converted to
libxml2 data structures in a second pass after parsing completes. By modifying gumbo
to use libxml2 data structures directly, there could be significant speed and
memory usage gains.


.. |pypi| image:: https://img.shields.io/pypi/v/html5-parser.svg?label=version
    :target: https://pypi.python.org/pypi/html5-parser
    :alt: Latest version released on PyPi

.. |unix_build| image:: https://api.travis-ci.org/kovidgoyal/html5-parser.svg
    :target: http://travis-ci.org/kovidgoyal/html5-parser
    :alt: Build status of the master branch on Unix

.. |windows_build|  image:: https://ci.appveyor.com/api/projects/status/github/kovidgoyal/html5-parser?svg=true
    :target: https://ci.appveyor.com/project/kovidgoyal/html5-parser
    :alt: Build status of the master branch on Windows
