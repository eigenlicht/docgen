# -*- coding: UTF-8 -*-

import os
import re
import ast
import ConfigParser
try:
    import json
except ImportError:
    import simplejson as json

from PyQt4 import QtGui
from PyQt4.QtCore import Qt

from ninja_ide.core import plugin
from ninja_ide.core import plugin_interfaces
from ninja_ide.core import file_manager
from ninja_ide.tools import json_manager

from menu import Menu
from wizard import PagePluginProperties

PROJECT_TYPE = "NINJA-Plugin-Project"

class Docstring(list):
    def __init__(self, indent=0):
        super(Docstring, self).__init__()
        self._default_indent = " " * indent
        self.prefix = self._default_indent

    def append(self, item):
        super(Docstring, self).append(self.prefix + item + '\n')

    def append_newline(self):
        super(Docstring, self).append('\n')

    def indent(self):
        self.prefix += " " * 4

    def unindent(self):
        self.prefix = self.prefix[4:]

    def __str__(self):
        return "{0}\n{1}{0}".format(self._default_indent + "'''", "".join(self))

#TODO: make config stuff more error safe (e.g. text with '\\n')
#TODO: independence from Sphinx
class DocGen(plugin.Plugin):
    def initialize(self):
        global PROJECT_TYPE
        self.explorer_s = self.locator.get_service('explorer')
        self.editor_s = self.locator.get_service('editor')
        self.menu_s = self.locator.get_service('menuApp')

        # set a project handler for NINJA-IDE Plugin
        self.explorer_s.set_project_type_handler(PROJECT_TYPE,
                DocGenHandler(self.locator))

        # get settings from file
        self.config, self.config_path = self._get_config()

        # create settings window
        #FIXME: give ide window as parent
        self.settings_win = SettingsWindow(None, self.config, self.config_path)

        # add menu entries
        #FIXME: implement as menu
        settings = QtGui.QAction("DocGen Settings", self)
        settings.triggered.connect(self.settings_win.show)

        gen_doc = QtGui.QAction("Generate Docstring", self)
        gen_doc.triggered.connect(self.gen_sphinx_doc)
        gen_doc.setShortcut(QtGui.QKeySequence("F8"))

        #menu.addAction(action)

        self.menu_s.add_action(gen_doc)
        self.menu_s.add_action(settings)

    def gen_sphinx_doc(self):
        editor = self.editor_s.get_editor()
        text = editor.get_text()

        # get indices for current line
        pos = editor.get_cursor_position()
        start = text[:pos].rfind('\n') + 1
        end = text[start:].find('\n') + start

        # create regex and its helper
        regex = (r'\s*KEYWORD\s+\w+\(.*?\)\s*:',
                 r'\s*KEYWORD\s+\w+\(.*?\)\s*:\s*#docgen-end')

        cls_regex = [r.replace('KEYWORD', 'class') for r in regex]
        fnc_regex = [r.replace('KEYWORD', 'def') for r in regex]

        def match(regex, text):
            r = re.match(regex, text, re.DOTALL)
            return r.group() if r else ''

        # try to find out what kind of docstring the user wants
        fnc = match(fnc_regex[0], text[start:])
        cls = match(cls_regex[0], text[start:])

        if start == end: # empty line - assume module doc
            doc = self._sphinx_module()
        elif fnc:
            try:
                doc = self._sphinx_function(fnc)
            except SyntaxError: # header might contain "):" - try second regex
                fnc = match(fnc_regex[1], text[start:])
                doc = self._sphinx_function(fnc) if fnc else None
        elif cls:
            try:
                doc = self._sphinx_class(cls)
            except SyntaxError:
                cls = match(cls_regex[1], text[start:])
                doc = self._sphinx_class(cls) if cls else None
        else:
            return # do nothing

        if doc:
            end = start + len(fnc) + len(cls) if start != end else end
            editor.set_cursor_position(end) # set cursor to end of line
            self.editor_s.insert_text('\n' + str(doc))

    def _sphinx_function(self, line):
        # remove indenation and add 'pass' to make 'def <name>(<...>):'
        # a valid Python expression for the syntax parser
        args = ast.parse(line.strip() + '\n    pass').body[0].args.args

        doc = Docstring(indent=line.find('def') + 4)

        for line in self.config.get('Sphinx', 'fnc').split('\n'):
            if line == '.':
                doc.append_newline()
            elif ':params:' in line:
                types = ':types:' in line

                # args is a list of _ast.Name objects)
                for arg in (a.id for a in args):
                    if arg == 'self': continue
                    doc.append(':param %s: ' % arg)
                    if types: doc.append(':type %s: ' % arg)
            else:
                doc.append(line)

        return doc

    def _sphinx_class(self, line):
        # verify what we consider the class header
        ast.parse(line.strip() + '\n    pass')

        doc = Docstring(indent=line.find('class') + 4)

        for line in self.config.get('Sphinx', 'cls').split('\n'):
            if line == '.': doc.append_newline()
            else: doc.append(line)

        return doc

    def _sphinx_module(self):
        doc = Docstring()

        for line in self.config.get('Sphinx', 'mod').split('\n'):
            if line == '.': doc.append_newline()
            else: doc.append(line)

        return doc

    def _get_config(self, path='~/.ninja_ide/addins/plugins/docgen/config'):
        path = os.path.expanduser(path)
        config = ConfigParser.ConfigParser()

        if not os.path.isfile(path):
            config.add_section('Sphinx')

            #FIXME: ugly hack: usage of '.' for empty lines
            #FIXME: otherwhise configparser ignores them
            config.set('Sphinx', 'mod',
            'Created on <date>\n.\n' +
            '.. moduleauthor:: Firstname Lastname <firstname@example.com>\n.\n' +
            ':synopsis:')

            config.set('Sphinx', 'cls',
                '.. codeauthor:: Firstname Lastname <firstname@example.com>')

            config.set('Sphinx', 'fnc',
            '.. codeauthor:: Firstname Lastname <firstname@example.com>\n.\n' +
            ':params: :types:\n.\n' +
            ':returns:\n.\n' +
            ':raise:')

            config.write(open(path, 'w'))
        else:
            config.readfp(open(path))

        return config, path


class SettingsWindow(QtGui.QDialog):
    def __init__(self, parent, config, path):
        QtGui.QDialog.__init__(self, parent)

        self.parent = parent
        self.config = config
        self.config_path = path

        # set window properties
        self.resize(550, 600)
        self.setMinimumSize(320, 400)
        self.setWindowTitle('DocGen - Settings')

        # create TextEdits for each template
        self.mod_l = QtGui.QLabel("Module Template:")
        self.mod = QtGui.QTextEdit(self)
        self.mod.setLineWrapMode(QtGui.QTextEdit.NoWrap)

        self.cls_l = QtGui.QLabel("Class Template:")
        self.cls = QtGui.QTextEdit(self)
        self.cls.setLineWrapMode(QtGui.QTextEdit.NoWrap)

        self.fnc_l = QtGui.QLabel("Function Template:")
        self.fnc = QtGui.QTextEdit(self)
        self.fnc.setLineWrapMode(QtGui.QTextEdit.NoWrap)

        # button to write config to file
        self.but_save = QtGui.QPushButton('Save', self)
        self.but_save.clicked.connect(self._write_config)

        # create layout
        vbox = QtGui.QVBoxLayout(self)

        vbox.addWidget(self.mod_l)
        vbox.addWidget(self.mod)
        vbox.addWidget(self.cls_l)
        vbox.addWidget(self.cls)
        vbox.addWidget(self.fnc_l)
        vbox.addWidget(self.fnc)
        vbox.addWidget(self.but_save)

        self.setLayout(vbox)

        # read current config
        self.mod.setText(config.get('Sphinx', 'mod').replace('\n.\n', '\n\n'))
        self.cls.setText(config.get('Sphinx', 'cls').replace('\n.\n', '\n\n'))
        self.fnc.setText(config.get('Sphinx', 'fnc').replace('\n.\n', '\n\n'))

    def _write_config(self):
        # set global config to new values
        self.config.set('Sphinx', 'mod',
            self.mod.toPlainText().replace('\n\n', '\n.\n'))
        self.config.set('Sphinx', 'cls',
            self.cls.toPlainText().replace('\n\n', '\n.\n'))
        self.config.set('Sphinx', 'fnc',
            self.fnc.toPlainText().replace('\n\n', '\n.\n'))

        # write new config to file
        self.config.write(open(self.config_path, 'w'))


class DocGenHandler(plugin_interfaces.IProjectTypeHandler):

    EXT = '.plugin'

    def __init__(self, locator):
        self.locator = locator

    def get_context_menus(self):
        return (Menu(self.locator), )

    def get_pages(self):
        return [PagePluginProperties(self.locator)]

    def on_wizard_finish(self, wizard):
        global PROJECT_TYPE
        ids = wizard.pageIds()
        # Manipulate default data for NINJA-IDE projects
        page = wizard.page(ids[2])
        path = unicode(page.txtPlace.text())
        if not path:
            QtGui.QMessageBox.critical(self, self.tr("Incorrect Location"),
                self.tr("The project couldn\'t be create"))
            return
        project = {}
        name = unicode(page.txtName.text())
        project['name'] = name
        project['project-type'] = PROJECT_TYPE
        project['description'] = unicode(page.txtDescription.toPlainText())
        project['license'] = unicode(page.cboLicense.currentText())
        project['venv'] = unicode(page.vtxtPlace.text())

        # Manipulate plugin project data
        page = wizard.page(ids[1])
        # Create a folder to contain all the project data (<path>/<name>/)
        path = os.path.join(path, name)
        file_manager.create_folder(path, add_init_file=False)
        # Create the .nja file
        json_manager.create_ninja_project(path, name, project)

        plugin_dict = self.create_descriptor(page, path)
        self.create_plugin_class(page, path, plugin_dict)
        # Load the project!
        wizard._load_project(path)

    def create_descriptor(self, page, path):
        plugin = {}

        module = unicode(page.txtModule.text())
        plugin['module'] = module
        className = str(page.txtClass.text())
        plugin['class'] = className
        authors = unicode(page.txtAuthors.text())
        plugin['authors'] = authors
        url = unicode(page.txtUrl.text())
        plugin['url'] = url
        version = unicode(page.txtVersion.text())
        plugin['version'] = version

        fileName = os.path.join(path, module + self.EXT)
        # Create the .plugin file with metadata
        self.create_file(fileName, plugin)
        # Return the dictionary
        return plugin

    def create_plugin_class(self, page, path, plugin_dict):
        module = plugin_dict['module']
        className = plugin_dict['class']
        completed = False
        # Start the template
        content = TEMPLATE_PLUGIN_BEGIN % className

        if page.checkEditorS.checkState() == Qt.Checked:
            content += TEMPLATE_EDITOR_S
            completed = True

        if page.checkToolbarS.checkState() == Qt.Checked:
            content += TEMPLATE_TOOLBAR_S
            completed = True

        if page.checkMenuPluginS.checkState() == Qt.Checked:
            content += TEMPLATE_MENU_S
            completed = True

        if page.checkMiscS.checkState() == Qt.Checked:
            content += TEMPLATE_MISC_S
            completed = True

        if page.checkExplorerS.checkState() == Qt.Checked:
            content += TEMPLATE_EXPLORER_S
            completed = True

        if not completed:
            content += TEMPLATE_PASS_STATMENT

        content += TEMPLATE_PLUGIN_FINISH
        content = content
        # Create the folder
        file_manager.create_folder(os.path.join(path, module))
        # Create the file
        fileName = os.path.join(os.path.join(path, module), module + '.py')
        # Write to the file
        file_manager.store_file_content(fileName, content)
        # Create the __init__.py with the imports!
        file_manager.create_init_file_complete(os.path.join(path, module))

    def create_file(self, fileName, structure):
        f = open(fileName, mode='w')
        json.dump(structure, f, indent=2)
        f.close()


###############################################################################
# TEMPLATES
###############################################################################

TEMPLATE_PLUGIN_BEGIN = """# -*- coding: UTF-8 -*-

from ninja_ide.core import plugin


class %s(plugin.Plugin):
    def initialize(self):
        # Init your plugin"""

TEMPLATE_PASS_STATMENT = """
        pass"""

TEMPLATE_EDITOR_S = """
        self.editor_s = self.locator.get_service('editor')"""

TEMPLATE_TOOLBAR_S = """
        self.toolbar_s = self.locator.get_service('toolbar')"""

TEMPLATE_MENU_S = """
        self.menuApp_s = self.locator.get_service('menuApp')"""

TEMPLATE_MISC_S = """
        self.misc_s = self.locator.get_service('misc')"""

TEMPLATE_EXPLORER_S = """
        self.explorer_s = self.locator.get_service('explorer')"""

TEMPLATE_PLUGIN_FINISH = """

    def finish(self):
        # Shutdown your plugin
        pass

    def get_preferences_widget(self):
        # Return a widget for customize your plugin
        pass
"""
