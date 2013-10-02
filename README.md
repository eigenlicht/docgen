docgen
======

NINJA IDE Plugin to generate docstring templates.

Configuring DocGen
------------------

Create your own docstring templates in the settings.
The DocGen special directives are:

### Sphinx special directives###

* :params: [:types:]

    will parse the function header for the arguments and add ':param arg1:' for each argument to the docstring. If you have ':types:' written in the same line as the :params: directive, it will also add ':type arg1:' for each argument.

Known Issues
------------

* Identing the template string in the config is not possible (ConfigParser just ignores them...)
* Very errornous code can not be parsed, e.g.:

        def f(a,b # generating docstring for this won't work correctly
        def g(a,b): pass
