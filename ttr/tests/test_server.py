import unittest
import mock
from ttr import server


class ServerTestCase(unittest.TestCase):

    @mock.patch('socket.socket')
    def test_loop(self, socket):
        pass

    def test_read_tests(self):
        pass
