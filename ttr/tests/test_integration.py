import os
import signal
import unittest
from subprocess import Popen
from socket import create_connection
import time
from ttr import server


class TtrTestCase(unittest.TestCase):

    def setUp(self):
        self.p = Popen(['python', '/home/amadev/files/prog/ttr/bin/ttr'])
        time.sleep(0.3)
        return self.p

    def tearDown(self):
        self.p.terminate()
        time.sleep(0.3)

    def test_run_single_test(self):
        conn = create_connection(server.ADDRESS)
        conn.send('ttr.tests.test_server.ServerTestCase.test_listen---')
        test_result = conn.recv(1024)
        self.assertIn('Ran 1 test in', test_result)
        conn.close()

    def test_restart_test_runner(self):
        os.kill(self.p.pid, signal.SIGHUP)
        time.sleep(0.2)
        os.kill(self.p.pid, signal.SIGHUP)
        time.sleep(0.2)

    def test_be_resilent_after_not_found_test(self):
        conn = create_connection(server.ADDRESS)
        conn.send('ttr.tests.test_server.ServerTestCase.test_read_tests---')
        test_result = conn.recv(1024)
        self.assertIn('Ran 1 test in', test_result)
        conn.send('xxx---')
        test_result = conn.recv(1024)
        self.assertIn('Ran 0 tests in', test_result)
        conn.send('ttr.tests.test_server.ServerTestCase.test_listen---')
        test_result = conn.recv(1024)
        self.assertIn('Ran 1 test in', test_result)
        conn.close()
