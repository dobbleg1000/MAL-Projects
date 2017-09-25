import queue
import threading
import functools
import unittest
import time
import multiprocessing


class Agent:

    __Mailbox = lambda: queue.Queue(maxsize=1)
    __job_type_halt = 0
    __job_type_dowork = 1

    def __init__(self, method, n_threads=1):
        self.__worker_queue = queue.Queue()
        for i in range(n_threads):
            worker = Agent.__initialize_worker(method, self.__worker_queue)
            self.__worker_queue.put_nowait(worker)

        self._manager = Agent.__initialize_manager(self.__worker_queue)
        self.__can_do_more_work = True
        self.__work_lock = threading.Lock()

    def __initialize_worker(method, worker_queue):
        mailbox = Agent.__Mailbox()
        thread = threading.Thread(target=Agent.__worker_loop, args=(mailbox, method, worker_queue))
        thread.start()
        return (thread, mailbox)

    def __worker_loop(mailbox, method, worker_queue):
        while (True):
            (job_type, method_args, callback) = mailbox.get()

            if job_type == Agent.__job_type_dowork:
                try:
                    result = method(*method_args)
                    if callback:
                        threading.Thread(target=callback, args=(result,)).start()
                except:
                    if callback:
                        threading.Thread(target=callback, args=(None,)).start()
                    mailbox.task_done()

                    worker_queue.put_nowait(Agent.__initialize_worker(method, worker_queue))
                    raise
            elif job_type == Agent.__job_type_halt:
                if callback:
                    threading.Thread(target=callback).start()
                mailbox.task_done()
                break
            else:
                raise ValueError("job_type: agent worker received invalid job type")

            mailbox.task_done()
            worker_queue.put((threading.current_thread(), mailbox))

    def __initialize_manager(worker_queue):
        work_queue = queue.Queue()
        thread = threading.Thread(target=Agent.__manager_loop, args=(work_queue, worker_queue))
        thread.start()
        return (thread, work_queue)

    def __manager_loop(work_queue, worker_queue):
        n_threads = worker_queue.qsize()
        while (True):
            (job_type, method_args, callback) = work_queue.get()

            if job_type == Agent.__job_type_dowork:
                (worker_thread, worker_mailbox) = worker_queue.get()
                worker_mailbox.put_nowait((job_type, method_args, callback))
                worker_queue.task_done()
            elif job_type == Agent.__job_type_halt:
                for i in range(n_threads):
                    (worker_thread, worker_mailbox) = worker_queue.get()
                    worker_mailbox.put_nowait((job_type, None, None))
                    worker_queue.task_done()
                    worker_mailbox.join()

                if callback:
                    threading.Thread(target=callback).start()
                work_queue.task_done()
                break
            else:
                raise ValueError("job_type: agent manager received invalid job type")

            work_queue.task_done()

    def execute_async(self, *method_args, callback=None):
        with self.__work_lock:
            if self.__can_do_more_work:
                (manager_thread, work_queue) = self._manager
                work_queue.put_nowait((Agent.__job_type_dowork, method_args, callback))
            else:
                raise ValueError("self: agent has been finalized and cannot receive any more work")

    def __block(f_taking_callback):
        blocking_mailbox = Agent.__Mailbox()

        def return_callback(callback_input=None):
            blocking_mailbox.put_nowait(callback_input)

        f_taking_callback(callback=return_callback)

        callback_input = blocking_mailbox.get()
        blocking_mailbox.task_done()
        return callback_input

    def execute(self, *method_args):
        return Agent.__block(functools.partial(self.execute_async, *method_args))

    def finalize_async(self, callback=None):
        with self.__work_lock:
            if self.__can_do_more_work:
                self.__can_do_more_work = False
                (manager_thread, work_queue) = self._manager
                work_queue.put_nowait((Agent.__job_type_halt, None, callback))
            else:
                raise ValueError("self: agent has already been finalized")

    def finalize(self):
        Agent.__block(functools.partial(self.finalize_async))


class AgentSpec_Safety(unittest.TestCase):

    def __pause(delay):
        def it():
            time.sleep(delay)
        return it

    def __test_finalization(self, finalization, method_pause):
        p = multiprocessing.Process(target=finalization, args=(method_pause,))
        p.start()
        time_limit = method_pause + 0.3  # seconds
        p.join(time_limit)

        if p.is_alive():
            p.terminate()
            p.join()
            raise AssertionError("finalization did not clean up all threads.")

    def finalize_an_agent(method_pause):
        agent = Agent(AgentSpec_Safety.__pause(method_pause), n_threads=3)
        agent.execute_async()
        agent.finalize()

    def test_finalize(self):
        self.__test_finalization(AgentSpec_Safety.finalize_an_agent, method_pause=1)

    def finalize_an_agent_async(method_pause):
        agent = Agent(AgentSpec_Safety.__pause(method_pause), n_threads=3)
        agent.execute_async()
        agent.finalize_async()

    def test_finalize_async(self):
        self.__test_finalization(AgentSpec_Safety.finalize_an_agent_async, method_pause=1)


class AgentSpec(unittest.TestCase):

    def __TestMethodBasic(pause=None):
        def it(x):
            if pause:
                time.sleep(pause)
            return x * 2
        return it

    def __TestMethodMailbox(mailbox, pause=None):
        def it(x):
            if pause:
                time.sleep(pause)
            mailbox.put_nowait(x * 2)
        return it

    def __setup(self, *args, **kwargs):
        self._agent = Agent(*args, **kwargs)

    def __tearDown(self):
        self._agent.finalize()

    def assertExecutionTime(self, f, max_time, min_time=None):
        output = queue.Queue(maxsize=1)

        def run_function():
            output.put_nowait(f())

        f_thread = threading.Thread(target=run_function, daemon=True)
        start_time = time.time()
        f_thread.start()
        f_thread.join(max_time)
        end_time = time.time()

        if f_thread.is_alive():
            raise AssertionError("The function took too much time to produce a result.")
        elif min_time and (end_time - start_time) < min_time:
            raise AssertionError("The function didn't take enough time to produce a result.")
        else:
            result = output.get()
            output.task_done()
            return result

    def test_execute(self):
        mailbox = queue.Queue()
        self.__setup(AgentSpec.__TestMethodMailbox(mailbox), n_threads=3)

        try:
            self._agent.execute(3)
            self.assertEqual(6, mailbox.get_nowait())

            self._agent.execute(5)
            self._agent.execute(10)
            self.assertEqual(10, mailbox.get_nowait())
            self.assertEqual(20, mailbox.get_nowait())
        finally:
            self.__tearDown()

    def test_execute_blocks(self):
        pause = 0.4
        self.__setup(AgentSpec.__TestMethodBasic(pause), n_threads=3)

        try:
            result = self.assertExecutionTime(lambda: self._agent.execute(3), min_time=pause, max_time=(pause + 0.1))
            self.assertEqual(6, result)
        finally:
            self.__tearDown()

    def test_execute_async(self):
        mailbox = queue.Queue()
        self.__setup(AgentSpec.__TestMethodMailbox(mailbox, pause=0.4), n_threads=3)

        try:
            inputs = [1, 5, 10]
            outputs = [2, 10, 20]
            for input in inputs:
                self.assertExecutionTime(lambda: self._agent.execute_async(input), max_time=0.1)

            for i in range(len(outputs)):
                output = mailbox.get()
                self.assertTrue(output in outputs)
                outputs.remove(output)
                mailbox.task_done()

            self.assertTrue(mailbox.empty())
        finally:
            self.__tearDown()

    def test_error_handling(self):
        normal_input = 2
        error_input = 3

        def test_method_error(x):
            if x == error_input:
                raise Exception("This is a test error -- please ignore, this does not indicate a failed test")
            else:
                return x * 2

        self.__setup(test_method_error, n_threads=1)

        try:
            self.assertEqual(None, self._agent.execute(error_input))
            self.assertEqual(normal_input * 2, self.assertExecutionTime(lambda: self._agent.execute(normal_input), max_time=1))
        finally:
            self.__tearDown()


if __name__ == "__main__":
    print('Running safety tests to determine if Agents can be disposed of correctly...\n')
    safety_test = unittest.main(exit=False, defaultTest="AgentSpec_Safety");

    if len(safety_test.result.errors) == 0 and len(safety_test.result.failures) == 0:
        print('\n\nSafety tests passed. Running Agent unit tests...\n')
        time.sleep(0.5)
        unittest.main(exit=True, defaultTest="AgentSpec")
