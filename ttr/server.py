import socket
import logging
from multiprocessing import Process, Pipe


ADDRESS = ('localhost', 25000)
TEST_RUNNER_PROCESS = None
TEST_RUNNER_CONN = None


def listen(address):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(address)
    sock.listen(5)
    logging.info('new listen socket is created %s', sock)
    return sock


def read_tests(sock):
    while True:
        logging.debug('waiting for connect %s', sock)
        conn, addr = sock.accept()
        logging.info('connection accepted %s, %s', conn, addr)
        while True:
            test_ids = []
            end = False
            payload = ''
            while True:
                logging.debug('waiting for data on %s', sock)
                data = conn.recv(1024).decode("utf-8")
                logging.debug(
                    'got data: "%s", hex repr: "%s"', data, data.encode('hex'))
                if data == '\n':
                    logging.debug('got command to execute tests')
                    break
                if not data:
                    logging.debug('got command to finish receiving')
                    end = True
                    break
                payload += data

            test_ids.extend(filter(None, payload.split('\n')))
            if test_ids:
                logging.debug('ready to excute tests %s', len(test_ids))
                yield test_ids
            if end:
                logging.debug('test reading finished')
                break


def restart_test_runner(function):
    global TEST_RUNNER_PROCESS, TEST_RUNNER_CONN
    if TEST_RUNNER_PROCESS:
        logging.info('kill existing process %s', TEST_RUNNER_PROCESS)
        TEST_RUNNER_PROCESS.terminate()
    TEST_RUNNER_CONN, child_conn = Pipe()
    TEST_RUNNER_PROCESS = Process(
        target=function, args=(child_conn,))
    TEST_RUNNER_PROCESS.start()
    logging.info('started new subprocess %s', TEST_RUNNER_PROCESS)
