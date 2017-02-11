import os
import signal
import socket
import logging
import logging.handlers
from multiprocessing import Process, Pipe
from StringIO import StringIO
import inotify.adapters
from ttr.tstlib import run_program


ADDRESS = ('localhost', 25000)
TEST_RUNNER_PROCESS = None
WATCHER_PROCESS = None
TEST_RUNNER_CONN = None
EXCLUDE_DIRS = ['/.git', '/.tox', '/.eggs', '/__pycache__', '/doc', '/api-ref']
EXCLUDE_FILES = ['.#', '.pyc']
END_MARKER = '---'
IS_STOPPED = False
DATA_DIR = os.path.expanduser('~/.ttr/')
logger = logging.getLogger(__name__)


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
        logger.debug("Adding initial watches on tree: [%s]", path)
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


def _read_request(sock):
    """
    Infinite read request loop.
    Format of request: cmd|params--
    """
    while True:
        if IS_STOPPED:
            raise RuntimeError('stopped before sock.accept')
        logger.debug('waiting for connect %s', sock)
        conn, addr = sock.accept()
        logger.info('connection accepted %s, %s', conn, addr)
        # start multi-read cycle
        while True:
            end = False
            payload = ''
            # start reading one request cycle
            while True:
                logger.debug('waiting for data on %s', sock)
                data = conn.recv(1024).decode("utf-8")
                logger.debug(
                    'got data: "%s", hex repr: "%s"', data, data.encode('hex'))
                if data.endswith(END_MARKER):
                    payload += data.replace(END_MARKER, '')
                    logger.debug('got END_MARKER, breaking concatination loop')
                    break
                if not data:
                    logger.info('client closed connection')
                    end = True
                    break
                payload += data
                # end reading one request cycle
            if end:
                logger.debug('breaking receiving loop')
                # exit multi-read cycle
                break
            request = payload.split('|')
            if len(request) != 2:
                logger.info('got invalid request %s', request)
                continue
            logger.debug('finished data receiving from client %s', request)
            yield conn, request


def _restore_default_signal():
    logger.debug('restoring default signal')
    signal.signal(signal.SIGTERM, signal.SIG_DFL)


def _start_test_runner(conn):
    _restore_default_signal()
    run_program(conn, [''], StringIO())


def _start_watcher():
    _restore_default_signal()
    i = InotifyExcludedTree(
        os.getcwd(), mask=inotify.constants.IN_MODIFY,
        excludes=EXCLUDE_DIRS)
    for event in i.event_gen():
        if event is not None:
            header, type_names, watch_path, filename = event
            watch_path = watch_path.decode('utf8')
            filename = filename.decode('utf8')

            logger.debug("WD=(%d) MASK=(%d) COOKIE=(%d) LEN=(%d) "
                         "MASK->NAMES=%s "
                         "WATCH-PATH=[%s] FILENAME=[%s]",
                         header.wd, header.mask, header.cookie,
                         header.len, type_names,
                         watch_path, filename)
            # TODO: move excluded files to inotify
            if not any(ex in filename for ex in EXCLUDE_FILES):
                ppid = os.getppid()
                os.kill(ppid, signal.SIGHUP)
                logger.info(
                    'watch event: signal sent to pid %s due file %s changed',
                    ppid, os.path.join(watch_path, filename))


def _signal_handler(signum, frame):
    logger.debug('signal handler called with signal %s, %s', signum, frame)
    if signum == signal.SIGHUP:
        restart_test_runner()
    elif signum == signal.SIGTERM:
        kill()


def set_environment():
    # TODO: create config
    try:
        os.mkdir(DATA_DIR, 0755)
    except OSError:
        pass
    logger = logging.getLogger('ttr')
    logger.propagate = False
    logger.setLevel(logging.DEBUG)
    ch = logging.handlers.RotatingFileHandler(
        filename=os.path.join(DATA_DIR, 'ttr.log'), maxBytes=1024 * 1024 * 10)
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        ('%(asctime)s - %(name)s - %(levelname)s '
         '- %(process)s - %(processName)s - %(message)s'))
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    signal.signal(signal.SIGHUP, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)


def restart_test_runner():
    global TEST_RUNNER_PROCESS, TEST_RUNNER_CONN
    if TEST_RUNNER_PROCESS:
        logger.info('kill existing process %s', TEST_RUNNER_PROCESS)
        TEST_RUNNER_PROCESS.terminate()
    TEST_RUNNER_CONN, child_conn = Pipe()
    TEST_RUNNER_PROCESS = Process(
        target=_start_test_runner, args=(child_conn,), name='test_runner')
    TEST_RUNNER_PROCESS.start()
    logger.info('started test runner subprocess %s', TEST_RUNNER_PROCESS)


def start_watcher():
    global WATCHER_PROCESS
    WATCHER_PROCESS = Process(target=_start_watcher, name='watcher')
    WATCHER_PROCESS.start()
    logger.info('started watcher subprocess %s', WATCHER_PROCESS)


def kill():
    global IS_STOPPED
    IS_STOPPED = True
    logger.info('killing everybody ...')
    WATCHER_PROCESS.terminate()
    TEST_RUNNER_PROCESS.terminate()


def loop():
    try:
        _loop()
    except Exception as exc:
        logger.exception('server loop fails %s', exc)
        raise


def _loop():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(ADDRESS)
    sock.listen(5)
    logger.info('new listen socket is created %s', sock)
    while True:
        if IS_STOPPED:
            break
        try:
            for client, request in _read_request(sock):
                logger.debug('sending data to test runner %s', request)
                TEST_RUNNER_CONN.send(request)
                logger.debug('waiting for test runner result')
                result = TEST_RUNNER_CONN.recv()
                logger.debug('got result %s', [result])
                logger.debug('sending result to client')
                client.send(result)
        except (socket.error, RuntimeError) as exc:
            # if signal come (kill -s 1|15 pid) socket will be destroyed
            # with error [Errno 4] Interrupted system call
            # and we need to restart whole procedure
            # python process.terminate does things more smoothly
            # looks like socket is closed properly before killing
            # for the such case RuntimeError is raised in read_tests
            logger.exception('reading cycle was broken due %s', exc)
