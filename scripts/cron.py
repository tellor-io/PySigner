import subprocess
import time

import schedule

from run_signer import run_signer

schedule.every(10).seconds.do(run_signer)

while True:
    try:
        schedule.run_pending()
    except:
        continue # this needs to be built out. for now, just catching exceptions to prevent termination