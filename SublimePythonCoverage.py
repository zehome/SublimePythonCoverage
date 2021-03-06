# bootstrap
import os
import sys
plugin_path = os.path.dirname(__file__)
sys.path += [plugin_path, ]
if not os.path.exists(os.path.join(plugin_path, 'coverage')):
    # Fetch coverage.py
    print('SublimePythonCoverage installing coverage.py.')

    import io
    import tarfile
    import urllib.request, urllib.parse, urllib.error
    from hashlib import md5

    SOURCE = 'http://daboog.zehome.com/~ed/coverage-3.6.tar.gz'
    MD5SUM = '67d4e393f4c6a5ffc18605409d2aa1ac'

    payload = urllib.request.urlopen(SOURCE).read()
    if md5(payload).hexdigest() != MD5SUM:
        raise ImportError('Invalid checksum.')

    tar = tarfile.open(mode='r:gz', fileobj=io.BytesIO(payload))
    for m in tar.getmembers():
        if not m.name.startswith('coverage-3.6/coverage/'):
            continue
        m.name = '/'.join(m.name.split('/')[2:])
        tar.extract(m, os.path.join(plugin_path, 'coverage'))

    print('SublimePythonCoverage successfully installed coverage.py.')
# end bootstrap

import sublime
import sublime_plugin
from coverage import coverage
from coverage.files import FnmatchMatcher
PLUGIN_FILE = os.path.abspath(__file__)

def find(base, rel, access=os.R_OK):
    if not isinstance(rel, str):
        rel = os.path.join(*rel)
    while 1:
        path = os.path.join(base, rel)
        if os.access(path, access):
            return path
        baseprev = base
        base = os.path.dirname(base)
        if not base or base == baseprev:
            return


def find_cmd(base, cmd):
    return find(base, ('bin', cmd), os.X_OK)


def find_tests(fname):
    dirname = os.path.dirname(fname)
    init = os.path.join(dirname, '__init__.py')
    if not os.path.exists(init):
        # not a package; run tests for the file
        return fname

    setup = find(dirname, 'setup.py')
    if setup:
        # run tests for the whole distribution
        return os.path.dirname(setup)

    # run tests for the package
    return os.path.dirname(fname)


class SublimePythonCoverageListener(sublime_plugin.EventListener):
    """Event listener to highlight uncovered lines when a Python file is loaded."""

    def on_load(self, view):
        if 'source.python' not in view.scope_name(0):
            return

        view.run_command('show_python_coverage')


class ShowPythonCoverageCommand(sublime_plugin.TextCommand):
    """Highlight uncovered lines in the current file based on a previous coverage run."""

    def run(self, edit):
        view = self.view
        view.erase_regions('SublimePythonCoverage')
        fname = view.file_name()
        if not fname:
            return

        cov_file = find(fname, '.coverage')
        if not cov_file:
            print('Could not find .coverage file.')
            return

        config_file = os.path.join(os.path.dirname(cov_file), '.coveragerc')

        if find(fname, '.coverage-noisy'):
            flags = sublime.DRAW_EMPTY | sublime.DRAW_OUTLINED
        else:
            flags = sublime.HIDDEN

        # run analysis and find uncovered lines
        cov = coverage(data_file=cov_file, config_file=config_file)
        outlines = []
        omit_matcher = FnmatchMatcher(cov.omit)
        if not omit_matcher.match(fname):
            cov.load()
            f, s, excluded, missing, m = cov.analysis2(fname)
            for line in missing:
                outlines.append(view.full_line(view.text_point(line - 1, 0)))

        # update highlighted regions
        if outlines:
            view.add_regions('SublimePythonCoverage', outlines,
                             'coverage.missing', 'bookmark', flags)

