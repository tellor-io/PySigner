import os
import threading

import schedule

from .run_signer import run_signer


def run_threaded(job_func):
    job_thread = threading.Thread(target=job_func)
    job_thread.start()


for private_key in os.getenv("PRIVATEKEY").split(","):
    schedule.every(10).seconds.do(run_threaded, run_signer(private_key))

while True:
    try:
        schedule.run_pending()
    except KeyboardInterrupt:
        break
    except:
        continue  # this needs to be built out. for now, just catching exceptions to prevent termination
