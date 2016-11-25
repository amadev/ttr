import os
import signal
import unittest
from subprocess import Popen, PIPE
from socket import create_connection
import time
from ttr import server


class TtrTestCase(unittest.TestCase):

    def _start(self):
        self.p = Popen(['python', '/home/amadev/files/prog/ttr/bin/ttr'])
        time.sleep(0.2)
        return self.p

    def _stop(self):
        self.p.terminate()
        time.sleep(0.2)

    def test_run_single_test(self):
        p = self._start()
        conn = create_connection(server.ADDRESS)
        conn.send('ttr.tests.test_server.ServerTestCase.test_listen---')
        test_result = conn.recv(1024)
        self.assertIn('Ran 1 test in', test_result)
        conn.close()
        self._stop()

    def test_restart_test_runner(self):
        p = self._start()
        os.kill(p.pid, signal.SIGHUP)
        time.sleep(0.2)
        os.kill(p.pid, signal.SIGHUP)
        time.sleep(0.2)
        self._stop()
