import copy
import smtplib
import logging
import os

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from bs4 import BeautifulSoup

from src.framework import config
from src.utility.utils import is_cluster_running, get_ocp_version
from src.utility.constants import EMAIL_NOTIFICATION_HTML

logger = logging.getLogger(__name__)


def email_reports():
    mailids = config.REPORTING["email"]["recipients"]
    if mailids == "":
        logger.warning("No recipients found, Skipping email notification !")
        return
    recipients = []
    [recipients.append(mailid) for mailid in mailids.split(",")]
    sender = "ocpclusterbot@redhat.com"
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"ocp4mco-ci cluster deployment " f"(RUN ID: {config.run_id}) "
    msg["From"] = sender
    msg["To"] = ",".join(recipients)
    html = os.path.join(EMAIL_NOTIFICATION_HTML)
    with open(os.path.expanduser(html)) as fd:
        html_data = fd.read()
    soup = BeautifulSoup(html_data, "html.parser")
    parse_html_for_email(soup)
    part1 = MIMEText(soup, "html")
    msg.attach(part1)
    kube_config_path = os.path.join(
        config.ENV_DATA["cluster_path"], config.RUN["kubeconfig_location"]
    )
    is_kube_config_exists = os.path.exists(kube_config_path)
    if is_kube_config_exists:
        with open(kube_config_path) as fd:
            part2 = MIMEBase("application", "octet-stream")
            part2.set_payload(fd.read())
            encoders.encode_base64(part2)
            part2.add_header("Content-Disposition", 'attachment; filename="kubeconfig"')
            msg.attach(part2)
    try:
        s = smtplib.SMTP(config.REPORTING["email"]["smtp_server"])
        s.sendmail(sender, recipients, msg.as_string())
        s.quit()
        logger.info(f"Results have been emailed to {recipients}")
    except Exception:
        logger.exception("Sending email with results failed!")


def parse_html_for_email(soup):
    # email notification html
    div = soup.find("div")
    table = copy.deepcopy(soup.find("table"))
    # clear old table
    soup.find("table").clear()
    username = config.RUN["username"]
    password = ""
    rows = table.findAll("tr")
    for row in rows:
        column_header = row.find("th")
        column = row.find("td")
        if column_header.string == "Cluster name":
            column.string = config.ENV_DATA["cluster_name"]
        if column_header.string == "Username":
            column.string = config.RUN["username"]
        if column_header.string == "Password":
            auth_file_path = config.RUN["password_location"]
            auth_file_full_path = os.path.join(
                config.ENV_DATA["cluster_path"], auth_file_path
            )
            is_password_exist = os.path.exists(auth_file_full_path)
            if is_password_exist:
                with open(os.path.expanduser(auth_file_full_path)) as fd:
                    password = fd.read()
                    column.string = password
            else:
                column.string = ""
        if column_header.string == "Cluster role":
            column.string = (
                "ACM Cluster"
                if config.MULTICLUSTER["acm_cluster"]
                else "Non-ACM Cluster"
            )
        if column_header.string == "Cluster status":
            p_tag = column.find("p")
            status = (
                "Available"
                if is_cluster_running(config.ENV_DATA["cluster_path"])
                else "Not Available"
            )
            p_tag.string = status
            p_tag["style"] = "color: green;" if status == "Available" else "color: red;"
        if column_header.string == "Cluster version":
            column.string = get_ocp_version()
        if column_header.string == "Cluster URL":
            column.string = f"https://console-openshift-console.apps.{config.ENV_DATA['cluster_name']}.{config.ENV_DATA['base_domain']}"
        if column_header.string == "Server":
            column.string = f"https://api.{config.ENV_DATA['cluster_name']}.{config.ENV_DATA['base_domain']}:6443"
        if column_header.string == "Login command":
            column.string = f"oc login https://api.{config.ENV_DATA['cluster_name']}.{config.ENV_DATA['base_domain']}:6443 -u {username} -p {password}"
        div.insert(0, table)
