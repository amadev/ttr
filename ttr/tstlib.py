import logging
import os
import sys
import copy
from functools import partial
from extras import try_imports, safe_hasattr
from testtools.compat import istext
from testtools.run import (
    TestProgram as TestoolsTestProgram,
    TestToolsTestRunner, list_test)


# To let setup.py work, make this a conditional import.
unittest = try_imports(['unittest2', 'unittest'])
logger = logging.getLogger(__name__)


class TestLoader(unittest.TestLoader):
    def _find_test_path(self, *args, **kwargs):
        r = super(TestLoader, self)._find_test_path(*args, **kwargs)
        if r is None:
            return None, False
        return r


class TestProgram(TestoolsTestProgram):
    """A command-line program that runs a set of tests; this is primarily
       for making test modules conveniently executable.
    """

    # defaults for testing
    module = None
    verbosity = 1
    failfast = catchbreak = buffer = progName = None
    _discovery_parser = None

    def __init__(self, conn, module=__name__, defaultTest=None, argv=None,
                 testRunner=None, testLoader=TestLoader(),
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
        self.handlers = {'run_tests': self.handler_run_tests,
                         'list_tests': self.handler_list_tests}
        self.parseArgs(argv)
        logger.debug('tests loaded: %s', len(list_test(self.test)[0]))
        while True:
            # cleanup stream from previos run
            self.stdout.truncate(0)

            logger.debug('waiting for recv on pair conn %s', conn)
            cmd, params = conn.recv()
            if cmd not in self.handlers:
                logger.info('got unknown command: %s', cmd)
            else:
                conn.send(self.handlers[cmd](params))
            if hasattr(self, 'run_once') and self.run_once:
                break

    def handler_run_tests(self, test_ids):
        logger.debug(
            'test program process got list of tests %s', test_ids)
        tests = filter_by_ids(self.test, test_ids)
        self.runTests(tests)
        result = ''
        if hasattr(self.stdout, 'getvalue'):
            result = self.stdout.getvalue()
        return result

    def handler_list_tests(self, needle):
        return '\n'.join(
            filter(
                lambda test: needle in test, list_test(self.test)[0])) or ' '

    def runTests(self, tests):
        if (self.catchbreak and
                getattr(unittest, 'installHandler', None) is not None):
            unittest.installHandler()
        testRunner = self._get_runner()
        self.result = testRunner.run(tests)


def get_tests_by_ids(suite_or_case, test_ids):
    if safe_hasattr(suite_or_case, 'id'):
        if suite_or_case.id() in test_ids:
            return [copy.deepcopy(suite_or_case)]
        return []
    else:
        filtered = []
        for item in suite_or_case:
            filtered.extend(get_tests_by_ids(item, test_ids))
        return filtered


def filter_by_ids(suite_or_case, test_ids):
    suite = unittest.TestSuite()
    suite.addTests(get_tests_by_ids(suite_or_case, test_ids))
    return suite


def run_program(conn, argv, stdout):
    logger.debug('Starting TestProgram (dir: %s, args: %s)',
                 os.getcwd(), argv)
    try:
        TestProgram(
            conn,
            argv=argv,
            testRunner=partial(TestToolsTestRunner, stdout=stdout),
            stdout=stdout)
    except Exception:
        logger.exception('Error is occured in test process')
        raise
