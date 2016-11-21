import unittest
from subprocess import Popen, PIPE
from socket import create_connection
import time
from ttr import server


class TtrTestCase(unittest.TestCase):
    def test_run_single_test(self):
        p = Popen(['python', '/home/amadev/files/prog/ttr/bin/ttr'])
        time.sleep(0.2)
        sock = create_connection(server.ADDRESS)
        sock.send('ttr.tests.test_server.ServerTestCase.test_listen')
        time.sleep(0.1)
        sock.send('\n')
        time.sleep(0.5)
        sock.close()
        p.terminate()
