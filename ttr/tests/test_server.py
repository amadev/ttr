import unittest
import mock
from ttr import server


class ServerTestCase(unittest.TestCase):

    @mock.patch('socket.socket')
    def test_listen(self, socket):
        sock = mock.Mock()
        socket.return_value = sock
        self.assertEqual(sock, server.listen(('fake', 'fake')))
        self.assertTrue(sock.bind.called)
        self.assertTrue(sock.listen.called)

    def test_read_tests(self):
        pass
