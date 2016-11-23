import os
import signal
import socket
import logging
from multiprocessing import Process, Pipe
import inotify.adapters


ADDRESS = ('localhost', 25000)
TEST_RUNNER_PROCESS = None
WATCHER_PROCESS = None
TEST_RUNNER_CONN = None
EXCLUDE_DIRS = ['/.git', '/.tox', '/.eggs', '/__pycache__', '/doc', '/api-ref']
EXCLUDE_FILES = ['.#', '.pyc']
END_MARKER = '---'

class InotifyExcludedTree(inotify.adapters.BaseTree):
    def __init__(self, path, mask=inotify.constants.IN_ALL_EVENTS,
                 block_duration_s=1,
                 excludes=None):
        super(InotifyExcludedTree, self).__init__(
            mask=mask, block_duration_s=block_duration_s)
        self.__root_path = path
        self.excludes = excludes or []
        self.__load_tree(path)

    def __load_tree(self, path):
        logging.debug("Adding initial watches on tree: [%s]", path)
        q = [path]
        while q:
            current_path = q[0]
            del q[0]

            self._i.add_watch(current_path, self._mask)

            for filename in os.listdir(current_path):
                entry_filepath = os.path.join(current_path, filename)
                if os.path.isdir(entry_filepath) is False:
                    continue
                if any(ex in entry_filepath for ex in self.excludes):
                    continue
                q.append(entry_filepath)


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
                if data.endswith(END_MARKER):
                    payload += data.replace(END_MARKER, '')
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
    logging.info('started test runner subprocess %s', TEST_RUNNER_PROCESS)


def _watch():
    i = InotifyExcludedTree(
        os.getcwd(), mask=inotify.constants.IN_MODIFY,
        excludes=EXCLUDE_DIRS)
    for event in i.event_gen():
        if event is not None:
            header, type_names, watch_path, filename = event
            watch_path = watch_path.decode('utf8')
            filename = filename.decode('utf8')

            logging.debug("WD=(%d) MASK=(%d) COOKIE=(%d) LEN=(%d) "
                          "MASK->NAMES=%s "
                          "WATCH-PATH=[%s] FILENAME=[%s]",
                          header.wd, header.mask, header.cookie,
                          header.len, type_names,
                          watch_path, filename)
            # TODO: move excluded files to inotify
            if not any(ex in filename for ex in EXCLUDE_FILES):
                ppid = os.getppid()
                os.kill(ppid, signal.SIGHUP)
                logging.info(
                    'watch event: signal sent to pid %s due file %s changed',
                    ppid, os.path.join(watch_path, filename))


def start_watcher():
    global WATCHER_PROCESS
    WATCHER_PROCESS = Process(target=_watch)
    WATCHER_PROCESS.start()
    logging.info('started watcher subprocess %s', WATCHER_PROCESS)
