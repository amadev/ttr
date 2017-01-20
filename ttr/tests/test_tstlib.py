import mock
import unittest
from ttr import tstlib
from testtools.run import list_test


class FakeTestCase(unittest.TestCase):
    def meth1(self):
        pass

    def meth2(self):
        pass


class FilterByIdTestCase(unittest.TestCase):
    def test_create_new_testsuite(self):
        suite = unittest.TestSuite()
        suite.addTest(FakeTestCase('meth1'))
        suite.addTest(FakeTestCase('meth2'))
        tests, _ = list_test(suite)
        self.assertEquals(2, len(tests))
        suite = tstlib.filter_by_ids(
            suite, ['ttr.tests.test_tstlib.FakeTestCase.meth1'])
        tests, _ = list_test(suite)
        self.assertEqual(1, len(tests))

    def test_run_unknown_command(self):
        conn = mock.Mock()
        conn.recv.return_value = ['unknown', '']
        tstlib.TestProgram.run_once = True
        tstlib.TestProgram(conn, argv=[''])

    def test_run_test_command(self):
        conn = mock.Mock()
        conn.recv.return_value = ['run_tests', ['test1']]
        tstlib.TestProgram.run_once = True
        tstlib.TestProgram(conn, argv=[''])
        assert conn.send.call_args == [('',)]
