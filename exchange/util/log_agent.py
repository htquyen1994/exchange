import multiprocessing
import os
from logging.handlers import RotatingFileHandler
from multiprocessing import Process, Queue, queues
import logging


from config.config import LogSetting, Message


def initialize():
    project_root_directory = os.getcwd()
    log_file_path = os.path.join(project_root_directory, "logs", "app.log")

    logger = logging.getLogger(log_file_path)
    handler = RotatingFileHandler(log_file_path, maxBytes=100 * 1024 * 1024,
                                  backupCount=2)
    formatter = logging.Formatter('%(asctime)s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    LoggerAgent.init_finished = True
    print("__initialize")


class LoggerAgent(queues.Queue):
    # Initialization flag
    # Log file path
    project_root_directory = os.getcwd()
    log_file_path = os.path.join(project_root_directory, "logs", "app.log")
    full_path = log_file_path
    # Log object
    logger = None
    # Process worker
    __worker_process = None

    __instance = None

    # Initialization flag
    init_finished = False

    @staticmethod
    def get_instance():
        if LoggerAgent.__instance is None:
            _instance = LoggerAgent("Sync_Data")
        return LoggerAgent.__instance

    def __init__(self, proc_name):
        try:
            ctx = multiprocessing.get_context()
            print(multiprocessing)
            super(LoggerAgent, self).__init__(ctx=ctx)
            LoggerAgent.__instance = self
            self.proc_name = proc_name
            LoggerAgent.__worker_process = None
            self.__start_worker()

        except Exception as ex:
            print("LogAgent.__init__:{}".format(ex.__str__()))

    def __enter__(self):
        try:
            self.__start_worker()
            return self
        except Exception as ex:
            print("LogAgent.__enter__:{}".format(ex.__str__()))

    def __exit__(self, exception_type, exception_value, traceback):
        try:
            self.__stop_worker()
        except Exception as ex:
            print("LogAgent.__exit__:{}".format(ex.__str__()))

    def __del__(self):
        try:
            self.__stop_worker()
        except Exception as ex:
            print("LogAgent.__del__:{}".format(ex.__str__()))

    def close(self):
        try:
            self.__stop_worker()
        except Exception as ex:
            print("LogAgent.close:{}".format(ex.__str__()))

    # Multi processing log info
    def info(self, output):

        try:
            # Put in queue
            self.put(output)
        except Exception as ex:
            print("LogAgent.info:{}".format(ex.__str__()))

    # Multi processing log error
    def error(self, output):
        try:
            # Put in queue
            self.put("ERROR: " + output)
        except Exception as ex:
            print("LogAgent.error:{}".format(ex.__str__()))


    # Multi processing log warning
    def warning(self, output):
        try:
            # Put in queue
            self.put("WARNING: " + output)
        except Exception as ex:
            print("LogAgent.warning:{}".format(ex.__str__()))

    # Multi processing log warning
    def exception(self, output):
        try:
            # Put in queue
            self.put("EXCEPTION: " + output.__str__())
        except Exception as ex:
            print("LogAgent.exception:{}".format(ex.__str__()))

    def __start_worker(self):
        """Start worker process. Worker process get log form queue the save to file
        :return: -
        """
        if LoggerAgent.__worker_process is None:
            print("__start_worker init process")
            LoggerAgent.__worker_process = multiprocessing.Process(
                target=LoggerAgent.worker_handler,
                args=(self, self.proc_name)
            )
            LoggerAgent.__worker_process.daemon = False
            LoggerAgent.__worker_process.start()

    def __stop_worker(self):
        if LoggerAgent.__worker_process is not None:
            self.put(Message.MSG_CLOSE_MONITOR)
            LoggerAgent.__worker_process.join()
            LoggerAgent.__worker_process = None

    def worker_handler(queue, proc_name):
            """
            Worker process function
            :type queue: multiprocessing.queues.Queue
            :param queue: (multiprocessing.queues.Queue) log queue
            :param proc_name: process name
            :return: -
            """
            try:
                if not LoggerAgent.init_finished:
                    # Initialize
                    print("LoggerAgent: not LoggerAgent.init_finished")
                    initialize()

                # Get log instance
                logger = logging.getLogger(LoggerAgent.full_path)

                while True:
                    msg = queue.get()
                    # Finish message
                    if isinstance(msg, str):
                        if msg == Message.MSG_CLOSE_MONITOR.value:
                            break
                    # Save log
                    logger.info(msg)

            except Exception as ex:
                print("LogAgent.worker_handler::".format(ex.__str__()))


