import logging
import copy
import os.path
import sys
from extras import try_imports, safe_hasattr


# To let setup.py work, make this a conditional import.
unittest = try_imports(['unittest2', 'unittest'])

from testtools import TextTestResult
from testtools.compat import istext, unicode_output_stream
from testtools.testsuite import iterate_tests, sorted_tests


defaultTestLoader = unittest.defaultTestLoader
defaultTestLoaderCls = unittest.TestLoader
have_discover = True
# This shouldn't really be public - its legacy.  Try to set it if we can, and
# if we can't (during installs before unittest2 is installed) just stub it out
# to None.
discover_impl = getattr(unittest, 'loader', None)


def list_test(test):
    """Return the test ids that would be run if test() was run.

    When things fail to import they can be represented as well, though
    we use an ugly hack (see http://bugs.python.org/issue19746 for details)
    to determine that. The difference matters because if a user is
    filtering tests to run on the returned ids, a failed import can reduce
    the visible tests but it can be impossible to tell that the selected
    test would have been one of the imported ones.

    :return: A tuple of test ids that would run and error strings
        describing things that failed to import.
    """
    unittest_import_strs = set([
        'unittest2.loader.ModuleImportFailure.',
        'unittest.loader.ModuleImportFailure.',
        'discover.ModuleImportFailure.'
        ])
    test_ids = []
    errors = []
    for test in iterate_tests(test):
        # Much ugly.
        for prefix in unittest_import_strs:
            if test.id().startswith(prefix):
                errors.append(test.id()[len(prefix):])
                break
        else:
            test_ids.append(test.id())
    return test_ids, errors


class TestToolsTestRunner(object):
    """ A thunk object to support unittest.TestProgram."""

    def __init__(self, verbosity=None, failfast=None, buffer=None,
                 stdout=None, tb_locals=False, **kwargs):
        """Create a TestToolsTestRunner.

        :param verbosity: Ignored.
        :param failfast: Stop running tests at the first failure.
        :param buffer: Ignored.
        :param stdout: Stream to use for stdout.
        :param tb_locals: If True include local variables in tracebacks.
        """
        self.failfast = failfast
        if stdout is None:
            stdout = sys.stdout
        self.stdout = stdout
        self.tb_locals = tb_locals

    def list(self, test, loader):
        """List the tests that would be run if test() was run."""
        test_ids, _ = list_test(test)
        for test_id in test_ids:
            self.stdout.write('%s\n' % test_id)
        errors = loader.errors
        if errors:
            for test_id in errors:
                self.stdout.write('%s\n' % test_id)
            sys.exit(2)

    def run(self, test):
        "Run the given test case or test suite."
        result = TextTestResult(
            unicode_output_stream(self.stdout),
            failfast=self.failfast,
            tb_locals=self.tb_locals)
        result.startTestRun()
        try:
            return test.run(result)
        finally:
            result.stopTestRun()


####################
# Taken from python 2.7 and slightly modified for compatibility with
# older versions. Delete when 2.7 is the oldest supported version.
# Modifications:
#  - If --catch is given, check that installHandler is available, as
#    it won't be on old python versions or python builds without signals.
#  - --list has been added which can list tests (should be upstreamed).
#  - --load-list has been added which can reduce the tests used (should be
#    upstreamed).


class TestProgram(unittest.TestProgram):
    """A command-line program that runs a set of tests; this is primarily
       for making test modules conveniently executable.
    """

    # defaults for testing
    module = None
    verbosity = 1
    failfast = catchbreak = buffer = progName = None
    _discovery_parser = None

    def __init__(self, conn, module=__name__, defaultTest=None, argv=None,
                 testRunner=None, testLoader=defaultTestLoader,
                 exit=True, verbosity=1, failfast=None, catchbreak=None,
                 buffer=None, stdout=None, tb_locals=False):
        if module == __name__:
            self.module = None
        elif istext(module):
            self.module = __import__(module)
            for part in module.split('.')[1:]:
                self.module = getattr(self.module, part)
        else:
            self.module = module
        if argv is None:
            argv = sys.argv
        if stdout is None:
            stdout = sys.stdout
        self.stdout = stdout

        self.exit = exit
        self.failfast = failfast
        self.catchbreak = catchbreak
        self.verbosity = verbosity
        self.buffer = buffer
        self.tb_locals = tb_locals
        self.defaultTest = defaultTest
        self.listtests = False
        self.load_list = None
        self.testRunner = testRunner
        self.testLoader = testLoader
        progName = argv[0]
        if progName.endswith('%srun.py' % os.path.sep):
            elements = progName.split(os.path.sep)
            progName = '%s.run' % elements[-2]
        else:
            progName = os.path.basename(argv[0])
        self.progName = progName
        self.parseArgs(argv)

        while True:
            logging.debug('waiting for recv on pair conn %s', conn)
            test_ids = conn.recv()
            self.stdout.truncate(0)
            logging.debug(
                'test program process got list of tests %s', test_ids)
            # import pprint
            # print 'original tests'
            # pprint.pprint(list_test(self.test)[0])
            tests = copy.deepcopy(filter_by_ids(self.test, test_ids))
            # print 'filtered tests'
            # pprint.pprint(list_test(tests)[0])
            self.runTests(tests)
            conn.send(self.stdout.getvalue())

    def _getParentArgParser(self):
        parser = super(TestProgram, self)._getParentArgParser()
        parser.add_argument(
            '-l', '--list', dest='listtests', default=False,
            action='store_true',
            help='List tests rather than executing them')
        parser.add_argument(
            '--load-list', dest='load_list', default=None,
            help='Specifies a file containing test ids, only tests matching '
            'those ids are executed')
        return parser

    def _do_discovery(self, argv, Loader=None):
        super(TestProgram, self)._do_discovery(argv, Loader=Loader)
        self.test = sorted_tests(self.test)

    def runTests(self, tests):
        if (self.catchbreak and
                getattr(unittest, 'installHandler', None) is not None):
            unittest.installHandler()
        testRunner = self._get_runner()
        self.result = testRunner.run(tests)

    def _get_runner(self):
        if self.testRunner is None:
            self.testRunner = TestToolsTestRunner
        try:
            try:
                testRunner = self.testRunner(verbosity=self.verbosity,
                                             failfast=self.failfast,
                                             buffer=self.buffer,
                                             stdout=self.stdout,
                                             tb_locals=self.tb_locals)
            except TypeError:
                # didn't accept the tb_locals parameter
                testRunner = self.testRunner(verbosity=self.verbosity,
                                             failfast=self.failfast,
                                             buffer=self.buffer,
                                             stdout=self.stdout)
        except TypeError:
            # didn't accept the verbosity, buffer, failfast or stdout arguments
            # Try with the prior contract
            try:
                testRunner = self.testRunner(verbosity=self.verbosity,
                                             failfast=self.failfast,
                                             buffer=self.buffer)
            except TypeError:
                # Now try calling it with defaults
                try:
                    testRunner = self.testRunner()
                except TypeError:
                    # it is assumed to be a TestRunner instance
                    testRunner = self.testRunner
        return testRunner


def get_tests_by_ids(suite_or_case, test_ids):
    if safe_hasattr(suite_or_case, 'id'):
        if suite_or_case.id() in test_ids:
            return [suite_or_case]
        return []
    else:
        filtered = []
        for item in suite_or_case:
            filtered.extend(filter_by_ids(item, test_ids))
        return filtered


def filter_by_ids(suite_or_case, test_ids):
    suite = unittest.TestSuite()
    suite.addTests(get_tests_by_ids(suite_or_case, test_ids))
    return suite
