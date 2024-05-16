"""Send a message on Google Chat group.
```
webhook_url='https://chat.googleapis.com/v1/spaces/SPACE_ID/messages?key=KEY&token=TOKEN'
```
Ref:
- https://developers.google.com/hangouts/chat/quickstart/incoming-bot-python
- https://developers.google.com/hangouts/chat/reference/message-formats
"""

import os
import requests

from src.framework import config
from src.utility.constants import MESSENGER_NOTIFICATION_STR
from src.utility.utils import is_cluster_running, get_ocp_version


def message_reports():
    webhook_url = config.REPORTING["messenger"]["webhook_url"]
    html_str = os.path.join(MESSENGER_NOTIFICATION_STR)
    with open(os.path.expanduser(html_str)) as fd:
        html_data = fd.read()
    send_text_message(
        paragraph=parse_html_for_message(html_data),
        webhook_url=webhook_url,
    )


def send_text_message(paragraph: str, webhook_url: str):
    widget = {"textParagraph": {"text": paragraph}}
    cards = [
        {
            "sections": [{"widgets": [widget]}],
        },
    ]
    return requests.post(webhook_url, json={"cards": cards})


def parse_html_for_message(html_data: str):
    # cluster name
    cluster_name = config.ENV_DATA["cluster_name"]

    # username
    username = config.RUN["username"]

    # password
    password = ""
    auth_file_path = config.RUN["password_location"]
    auth_file_full_path = os.path.join(config.ENV_DATA["cluster_path"], auth_file_path)
    is_password_exist = os.path.exists(auth_file_full_path)
    if is_password_exist:
        with open(os.path.expanduser(auth_file_full_path)) as fd:
            password = fd.read()

    # cluster role
    cluster_role = (
        "ACM Cluster" if config.MULTICLUSTER["acm_cluster"] else "Non-ACM Cluster"
    )

    # cluster status
    status = (
        "Available"
        if is_cluster_running(config.ENV_DATA["cluster_path"])
        else "Not Available"
    )
    status_tag = (
        (
            "<font color='#4BB543'>"
            if status == "Available"
            else "<font color='#ff0000'>"
        )
        + status
        + "</font>"
    )

    # cluster version
    cluster_version = get_ocp_version()

    # cluster URL
    cluster_url = f"https://console-openshift-console.apps.{config.ENV_DATA['cluster_name']}.{config.ENV_DATA['base_domain']}"
    cluster_url_tag = f"<a href={cluster_url}> {cluster_url} </a>"

    # server
    server_api = f"https://api.{config.ENV_DATA['cluster_name']}.{config.ENV_DATA['base_domain']}:6443"
    server_api_tag = f"<a href={server_api}> {server_api} </a>"

    # login command
    login_cmd = f"oc login https://api.{config.ENV_DATA['cluster_name']}.{config.ENV_DATA['base_domain']}:6443 -u {username} -p {password}"

    html_data = html_data.replace("{ clustername }", cluster_name)
    html_data = html_data.replace("{ username }", username)
    html_data = html_data.replace("{ password }", password)
    html_data = html_data.replace("{ cluster_role }", cluster_role)
    html_data = html_data.replace("{ ocp_cluster_status }", status_tag)
    html_data = html_data.replace("{ ocp_cluster_version }", cluster_version)
    html_data = html_data.replace("{ url }", cluster_url_tag)
    html_data = html_data.replace("{ server }", server_api_tag)
    html_data = html_data.replace("{ login_command }", login_cmd)
    return html_data
