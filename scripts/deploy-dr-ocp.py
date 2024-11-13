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
        deploy_cmd = (f"deploy-ocp multicluster 2 --cluster1 --cluster-name drcluster1-{suffix} --cluster-path /tmp/drcluster1-{suffix} --ocp4mcoci-conf {environment['ocp_config']} "
            f"--cluster2 --cluster-name drcluster2-{suffix} --cluster-path /tmp/drcluster2-{suffix}  --ocp4mcoci-conf --ocp4mcoci-conf {environment['ocp_hub_config']}"
        )
        if 'webhook_url' in environment:
            deploy_cmd += f" --webhook-url '{environment['webhook_url']}'"
        if 'email_ids' in environment:
            deploy_cmd += f" --email-ids {environment['email_ids']}"

        os.system(deploy_cmd)
    except Exception:
        pass

for i in [environment['schedule_time_deploy']]:
    schedule.every().monday.at(i).do(job)
    schedule.every().tuesday.at(i).do(job)
    schedule.every().wednesday.at(i).do(job)
    schedule.every().thursday.at(i).do(job)
    schedule.every().friday.at(i).do(job)

while True:
    schedule.run_pending()
    time.sleep(1)

