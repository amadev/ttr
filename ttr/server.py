import socket
import logging


ADDRESS = ('localhost', 25000)


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
