import schedule
import datetime
import time
import os

def get_suffix():
    nowtime = datetime.datetime.now()
    month = nowtime.strftime("%b").lower()
    day = str(nowtime.day-1)
    return month + '-' + day

def job(t):
    try:
        print("executing")
        suffix = get_suffix()
        os.system(f"cleanup-ocp  --cluster-name rdrcluster1-{suffix} --cluster-path /tmp/rdrcluster1-{suffix}")
        os.system(f"cleanup-ocp  --cluster-name rdrcluster2-{suffix} --cluster-path /tmp/rdrcluster2-{suffix}")
    except Exception:
        pass

for i in ["07:00"]:
    schedule.every().tuesday.at(i).do(job, i)
    schedule.every().wednesday.at(i).do(job, i)
    schedule.every().thursday.at(i).do(job, i)
    schedule.every().friday.at(i).do(job, i)
    schedule.every().saturday.at(i).do(job, i)

while True:
    schedule.run_pending()
    time.sleep(1)
