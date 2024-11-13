import schedule
import datetime
import time
import os
import yaml

with open('./config/env.yaml', 'r') as env_file:
    environment = yaml.safe_load(env_file)

def get_suffix():
    nowtime = datetime.datetime.now()
    month = nowtime.strftime("%b").lower()
    day = str(nowtime.day)
    return month + '-' + day

def job():
    try:
        print("executing")
        suffix = get_suffix()
        os.system(f"cleanup-ocp --cluster-paths /tmp/odfcluster-common-{suffix}")
    except Exception:
        pass

for i in [environment['schedule_time_cleanup']]:
    schedule.every().tuesday.at(i).do(job)
    schedule.every().wednesday.at(i).do(job)
    schedule.every().thursday.at(i).do(job)
    schedule.every().friday.at(i).do(job)
    schedule.every().saturday.at(i).do(job)

while True:
    schedule.run_pending()
    time.sleep(1)
