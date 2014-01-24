docgen
======

NINJA IDE Plugin to generate docstring templates.

Configuring DocGen
------------------

Create your own docstring templates in the settings, which you can find in the menubar at the top under Addins -> DocGen Settings. The default key binding for generating docstrings is F8.

To generate...
* a function docstring, place your cursor in the line of the function header (i.e. the line with the 'def'-keyword, the function name, arguments, etc.)
* a class docstring, place your cursor in the line of the class header (i.e. the line with the 'class'-keyword, etc.)
* a module docstring, place your cursor in an empty line
and press the key you assigned to docstring generation or click on Addins -> Generate Docstring.

The DocGen special directives are:

### Sphinx special directives###

* `:params: [:types:]`

    will parse the function header for the arguments and add `:param arg1:` for each argument to the docstring. If you have `:types:` written in the same line as the :params: directive, it will also add `:type arg1:` for each argument.
    For example, if your Function Template looks like this:

        .. codeauthor:: Firstname Lastname <firstname@example.com>
         
        :params: :types:
         
        :returns: 
         
        :raise: 

    The resulting docstring for the function definition `def f(a, b=None): pass` would look like this:

        '''
        .. codeauthor:: Firstname Lastname <firstname@example.com>
         
        :param a: 
        :type a: 
        :param b: 
        :type b: 
         
        :returns: 
         
        :raise: 
        '''

Known Issues
------------

* Very errornous code can not be parsed, e.g.:

        def f(a,b # generating docstring for this won't work correctly
        def g(a,b): pass
