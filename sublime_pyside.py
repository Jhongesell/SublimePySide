# -*- coding: utf8 -*-

# Copyright (C) 2012 - Oscar Campos <oscar.campos@member.fsf.org>
# This plugin is Free Software see LICENSE file for details

import sublime
import sublime_plugin

import os
import sys
import shutil
import functools
import threading
import subprocess
from glob import glob

try:
    import rope
    rope_support = True
except ImportError:
    rope_support = False


class Project(object):
    """
    Project class for PySide Qt Projects
    """

    def __init__(self, projectroot, projectname, projecttpl, templates):
        super(Project, self).__init__()

        self.templates = templates
        self.root = projectroot
        self.name = projectname
        self.tpl = projecttpl

    def is_valid(self):
        """
        Checks if the project is valid
        """

        if self.tpl not in [tpl.split('::')[0] for tpl in self.templates]:
            return False

        return True

    def create_files(self):
        """
        Create the project files
        """

        path = self.tpl.replace(' ', '_').lower()

        for file in glob('{0}/{1}/*'.format(get_templates_dir(), path)):
            if os.path.isdir(file):
                sublime.status_message('Copying {0} tree...'.format(file))
                try:
                    shutil.copytree(file, '{0}/{1}'.format(self.root,
                        os.path.basename(file)))
                except OSError, e:
                        sublime.error_message(e)
                continue
            with open(file, 'r') as fh:
                buffer = fh.read().replace('${APP_NAME}',
                    self.name.encode('utf8'))
            with open('{0}/{1}'.format(
                self.root, os.path.basename(file)), 'w') as fh:
                fh.write(buffer)
                sublime.status_message('Copying {0} file...'.format(file))

    def create_rope_files(self):
        """
        Create the Rope project files
        """

        try:
            rope_project = rope.base.project.Project(
                projectroot=self.root)
            rope_project.close()
        except Exception, e:
            msg = 'Could not create rope project folder at {0}\n' \
                  'Exception: {1}'.format(self.root, str(e))
            sublime.error_message(msg)

    def create_st2_project_files(self):
        """
        Create the Sublime Text 2 project file
        """

        pass


class CreateQtProjectCommand(sublime_plugin.WindowCommand):
    """
    Creates a new PySide application from a template
    """
    def run(self):
        CreateQtProjectThread(self.window).start()


class CreateQtProjectThread(threading.Thread):
    """
    Worker that creates a new application from a template
    """
    def __init__(self, window):
        self.window = window
        self.folders = self.window.folders()
        self.templates = list(get_template_list())
        threading.Thread.__init__(self)

    def run(self):
        """
        Starts the thread
        """

        def show_quick_pane():
            if not self.templates:
                sublime.error_message(
                    "{0}: There are no templates to list.".format(__name__))
                return

            self.window.show_quick_panel(self.templates, self.done)

        sublime.set_timeout(show_quick_pane, 10)

    def done(self, picked):
        """
        This method is called when user pickup a template from list
        """
        if picked == -1:
            return

        self.proj_tpl = self.templates[picked].split('::')[0]

        suggest = self.folders[0] if self.folders else os.path.expanduser('~')
        self.window.show_input_panel('Project root:', suggest,
            self.entered_proj_dir, None, None
        )

    def entered_proj_dir(self, path):
        if not os.path.exists(path):
            if sublime.ok_cancel_dialog('{path} does not exists.'
                            'Do you want to create it now?'.format(path=path)):
                os.makedirs(path)
            else:
                return

        if not os.path.isdir(path):
            sublime.error_message("{path} is not a directory".format(path=path))
            return

        self.proj_dir = path

        self.window.show_input_panel(
            'Give me a project name :', 'MyProject', self.entered_proj_name,
            None, None
        )

    def entered_proj_name(self, name):
        if not name:
            sublime.error_message("You will use a project name")
            return

        self.proj_name = name

        project = Project(
                self.proj_dir, self.proj_name, self.proj_tpl, self.templates)

        if project.is_valid():
            project.create_files()
            if rope_support:
                project.create_rope_files()
            project.create_st2_project_files()
            if sublime.ok_cancel_dialog('Do you want to add the project '
                            'directory to the current Sublime Text 2 Window?'):
                subprocess.Popen(
                    [sublime_executable_path(), '-a', self.proj_dir]
                )
        else:
            sublime.error_message(
                'Could not create Qt Project files for template "{0}"'.format(
                    self.proj_tpl)
            )

        if sublime.ok_cancel_dialog('Do you want to add the project '
                            'directory to the Sublime Text 2 current Window?'):
            subprocess.Popen([sublime_executable_path(), '-a', self.proj_dir])


def sublime_executable_path():
    """
    Return the Sublime Text 2 installation path for each platform
    """
    platform = sublime.platform()
    e = sublime.set_timeout(functools.partial(get_settings, 'osx_st2_path'), 0)
    if platform == 'osx':
        if not e:
            return '/Applications/Sublime Text 2.app' \
                                            '/Contents/SharedSupport/bin/subl'
        else:
            return e

    if platform == 'linux':
        if os.path.exists('/proc/self/cmdline'):
            return open('/proc/self/cmdline').read().split(chr(0))[0]

    return sys.executable


def get_template_list():
    """
    Generator for lazy templates list
    """

    with open("{0}/templates.lst".format(get_templates_dir(), "r")) as fh:
        for tpl in fh.read().split('\n'):
            if len(tpl):
                tpl_split = tpl.split(':')
                yield "{0}:: {1}".format(tpl_split[0], tpl_split[1])


def get_templates_dir():
    """
    Return the templates dir
    """

    return '{0}/{1}/{2}/templates'.format(
        sublime.packages_path(),
        get_settings('sublimepyside_package'),
        get_settings('sublimepyside_data_dir')
    )


def get_settings(name, typeof=str):
    settings = sublime.load_settings('SublimePySide.sublime-settings')
    setting = settings.get(name)
    if setting:
        if typeof == str:
            return setting
        elif typeof == bool:
            return setting == True
        elif typeof == int:
            return int(settings.get(name, 500))
    else:
        if typeof == str:
            return ''
        else:
            return None
