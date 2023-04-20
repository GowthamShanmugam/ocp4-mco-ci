import schedule
import datetime
import time
import os

def get_suffix():
    nowtime = datetime.datetime.now()
    month = nowtime.strftime("%b").lower()
    day = str(nowtime.day)
    return month + '-' + day

def job(t):
    try:
        print("executing")
        suffix = get_suffix()
        os.system(f"deploy-ocp  --email-ids gshanmug@redhat.com,nthomas@redhat.com,badhikar@redhat.com,anbehl@redhat.com,vbadrina@redhat.com,tjeyasin@redhat.com,amohan@redhat.com,uchapaga@redhat.com,skatiyar@redhat.com,hdavid@redhat.com,chandkum@redhat.com,dkamboj@redhat.com,dpandit@redhat.com,almartin@redhat.com,ialmeida@redhat.com --ocp4mcoci-conf samples/deploy_ocp_cluster/override_config.yaml --cluster-name odfcluster-common-{suffix} --cluster-path /tmp/odfcluster-common-{suffix}")
    except Exception:
        pass

for i in ["10:00"]:
    schedule.every().monday.at(i).do(job, i)
    schedule.every().tuesday.at(i).do(job, i)
    schedule.every().wednesday.at(i).do(job, i)
    schedule.every().thursday.at(i).do(job, i)
    schedule.every().friday.at(i).do(job, i)

while True:
    schedule.run_pending()
    time.sleep(1)
