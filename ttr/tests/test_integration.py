import unittest
from subprocess import Popen, PIPE
from socket import create_connection
import time
from ttr import server


class TtrTestCase(unittest.TestCase):
    def test_run_single_test(self):
        p = Popen(['python', '/home/amadev/files/prog/ttr/bin/ttr'])
        time.sleep(0.2)
        conn = create_connection(server.ADDRESS)
        conn.send('ttr.tests.test_server.ServerTestCase.test_listen---')
        test_result = conn.recv(1024)
        self.assertEqual('ok', test_result)
        conn.close()
        p.terminate()
