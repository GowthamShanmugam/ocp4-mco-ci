import schedule
import datetime
import time
import os
import yaml

with open('./config/env.dr.yaml', 'r') as env_file:
    environment = yaml.safe_load(env_file)

def get_suffix():
    nowtime = datetime.datetime.now()
    month = nowtime.strftime("%b").lower()
    day = str(nowtime.day)
    year = str(nowtime.year)[2:]
    return month + '-' + day + '-' + year 

def job():
    try:
        print("executing")
        suffix = get_suffix()
        multicluster_cmd =  "deploy-ocp multicluster 2"
        if 'webhook_url' in environment:
            multicluster_cmd += f" --webhook-url '{environment['webhook_url']}'"
        if 'email_ids' in environment:
            multicluster_cmd += f" --email-ids {environment['email_ids']}"
        deploy_cmd = multicluster_cmd + (f" --cluster1 --cluster-name dr1-{suffix} --cluster-path /tmp/dr1-{suffix} --ocp4mcoci-conf {environment['ocp_config']}"
            f" --cluster2 --cluster-name dr2-{suffix} --cluster-path /tmp/dr2-{suffix} --ocp4mcoci-conf {environment['ocp_hub_config']}"
        )
        os.system(deploy_cmd)
    except Exception:
        pass
    
def job_submariner():
    try:
        print("executing")
        suffix = get_suffix()
        multicluster_cmd =  "deploy-ocp multicluster 2"
        if 'webhook_url' in environment:
            multicluster_cmd += f" --webhook-url '{environment['webhook_url']}'"
        if 'email_ids' in environment:
            multicluster_cmd += f" --email-ids {environment['email_ids']}"
        deploy_cmd = multicluster_cmd + (f" --cluster1 --cluster-name dr1-{suffix} --cluster-path /tmp/dr1-{suffix} --ocp4mcoci-conf {environment['ocp_sub_config']}"
            f" --cluster2 --cluster-name dr2-{suffix} --cluster-path /tmp/dr2-{suffix} --ocp4mcoci-conf {environment['ocp_hub_sub_config']}"
        )
        os.system(deploy_cmd)
    except Exception:
        pass

for i in [environment['schedule_time_deploy']]:
    schedule.every().monday.at(i).do(job)
    schedule.every().tuesday.at(i).do(job)
    schedule.every().wednesday.at(i).do(job)
    schedule.every().thursday.at(i).do(job)
    schedule.every().friday.at(i).do(job)

# rerun submariner script, Most of the time submariner won't be deployed successfully on previous cron job.
for i in [environment['schedule_time_deploy_sub']]:
    schedule.every().monday.at(i).do(job_submariner)
    schedule.every().tuesday.at(i).do(job_submariner)
    schedule.every().wednesday.at(i).do(job_submariner)
    schedule.every().thursday.at(i).do(job_submariner)
    schedule.every().friday.at(i).do(job_submariner)

while True:
    schedule.run_pending()
    time.sleep(1)

