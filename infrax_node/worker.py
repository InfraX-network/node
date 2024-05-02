# pytorch stuff to accept job of some format, run, and return result

import logging
from datetime import datetime
from multiprocessing import Process, Queue
from time import sleep
from typing import Any

from .types import Job, Result

logging.basicConfig(level=logging.INFO)

job_queue = Queue()
result_queue = Queue()


class Worker(Process):
    def __init__(self, inbox: Queue, outbox: Queue):
        super().__init__()
        self.inbox = inbox
        self.outbox = outbox
        self.daemon = True

    def run(self):
        logging.info("Worker started")
        while True:
            try:
                if self.inbox.empty():
                    continue
                if job := self.inbox.get():
                    result = Result(
                        job_id=job.id,
                        execution_time=0,
                        output=None,
                        success=True,
                        error=None,
                    )
                    start_ts = int(datetime.now().timestamp())
                    try:
                        work_results = self.do_work(job)
                        result.output = work_results
                    except Exception as e:
                        result.error = str(e)
                        result.success = False
                    finally:
                        end_ts = int(datetime.now().timestamp())
                        result.execution_time = end_ts - start_ts
                        self.outbox.put((job, result))
            except Exception as e:
                print(e)
            sleep(1)

    def do_work(self, job: Job) -> Any:
        # simulate work
        sleep(5)
        return "result"
