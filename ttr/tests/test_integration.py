import os
import signal
import unittest
from subprocess import Popen
from socket import create_connection
import time
from ttr import server

ROOT_PATH = __file__
for i in range(3):
    ROOT_PATH = os.path.dirname(ROOT_PATH)
WAIT_TIME = 0.5


class TtrTestCase(unittest.TestCase):

    def setUp(self):
        self.p = Popen(['python', ROOT_PATH + '/bin/ttr-start'])
        time.sleep(WAIT_TIME)
        return self.p

    def tearDown(self):
        self.p.terminate()
        time.sleep(WAIT_TIME)

    def test_run_single_test(self):
        conn = create_connection(server.ADDRESS)
        conn.send(
            'run_tests|ttr.tests.test_server.ServerTestCase.test_listen---')
        test_result = conn.recv(1024)
        self.assertIn('Ran 1 test in', test_result)
        conn.close()

    def test_restart_test_runner(self):
        os.kill(self.p.pid, signal.SIGHUP)
        time.sleep(WAIT_TIME)
        conn = create_connection(server.ADDRESS)
        self.assert_list_tests_work(conn)

    def test_be_resilent_after_not_found_test(self):
        conn = create_connection(server.ADDRESS)
        conn.send(
            'run_tests|'
            'ttr.tests.test_server.ServerTestCase.test_read_tests---')
        test_result = conn.recv(1024)
        self.assertIn('Ran 1 test in', test_result)
        conn.send('run_tests|xxx---')
        test_result = conn.recv(1024)
        self.assertIn('Ran 0 tests in', test_result)
        conn.send(
            'run_tests|'
            'ttr.tests.test_server.ServerTestCase.test_read_tests---')
        test_result = conn.recv(1024)
        self.assertIn('Ran 1 test in', test_result)
        conn.close()

    def test_run_multiple_tests_at_once(self):
        conn = create_connection(server.ADDRESS)
        conn.send(
            'run_tests|'
            'ttr.tests.test_server.ServerTestCase.test_read_tests\n'
            'ttr.tests.test_server.ServerTestCase.test_listen---')
        test_result = conn.recv(1024)
        self.assertIn('Ran 2 tests in', test_result)

    def test_run_testcase(self):
        conn = create_connection(server.ADDRESS)
        conn.send(
            'run_tests|'
            'ttr.tests.test_server.ServerTestCase---')
        test_result = conn.recv(1024)
        self.assertNotIn('Ran 0', test_result)
        self.assertIn('tests in', test_result)

    def assert_list_tests_work(self, conn):
        conn.send('list_tests|ServerTestCase.test_read_tests---')
        test_result = conn.recv(1024)
        self.assertIn(
            'ttr.tests.test_server.ServerTestCase.test_read_tests',
            test_result)
        self.assertEqual(1, len(test_result.split('\n')))

    def test_filter_tests(self):
        conn = create_connection(server.ADDRESS)
        self.assert_list_tests_work(conn)
