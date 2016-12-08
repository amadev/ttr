import unittest
from ttr import tstlib


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
        tests, _ = tstlib.list_test(suite)
        self.assertEquals(2, len(tests))
        suite = tstlib.filter_by_ids(
            suite, ['ttr.tests.test_tstlib.FakeTestCase.meth1'])
        tests, _ = tstlib.list_test(suite)
        self.assertEqual(1, len(tests))
