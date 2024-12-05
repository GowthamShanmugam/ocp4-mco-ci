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
import logging
import json

from src.framework import config
from src.utility.constants import (
    GCHAT_MESSENGER_NOTIFICATION_STR,
    SLACK_MESSENGER_NOTIFICATION_STR,
)
from src.utility.utils import is_cluster_running, get_ocp_version

logger = logging.getLogger(__name__)


def get_username():
    return config.RUN["username"]


def get_password():
    password = ""
    auth_file_path = config.RUN["password_location"]
    auth_file_full_path = os.path.join(config.ENV_DATA["cluster_path"], auth_file_path)
    is_password_exist = os.path.exists(auth_file_full_path)
    if is_password_exist:
        with open(os.path.expanduser(auth_file_full_path)) as fd:
            password = fd.read()
    return password


def get_cluster_status():
    return (
        "Available"
        if is_cluster_running(config.ENV_DATA["cluster_path"])
        else "Not Available"
    )


def get_cluster_url():
    return f"https://console-openshift-console.apps.{config.ENV_DATA['cluster_name']}.{config.ENV_DATA['base_domain']}"


def get_cluster_api():
    return f"https://api.{config.ENV_DATA['cluster_name']}.{config.ENV_DATA['base_domain']}:6443"


def get_cluster_command(username: str, password: str):
    return f"oc login https://api.{config.ENV_DATA['cluster_name']}.{config.ENV_DATA['base_domain']}:6443 -u {username} -p {password}"


def message_reports():
    webhook_url = config.REPORTING["messenger"]["webhook_url"]
    if webhook_url == "":
        logger.warning("No webhook rul found, Skipping gchat message notification !")
        return

    # send_gchat_message(webhook_url=webhook_url)
    send_slack_message(webhook_url=webhook_url)


def send_gchat_message(webhook_url: str):
    html_str = os.path.join(GCHAT_MESSENGER_NOTIFICATION_STR)
    with open(os.path.expanduser(html_str)) as fd:
        html_data = fd.read()
    title = config.ENV_DATA["cluster_name"]
    subtitle = get_cluster_role()
    paragraph = parse_html_for_message(html_data)
    header = {"title": title, "subtitle": subtitle}
    widget = {"textParagraph": {"text": paragraph}}
    cards = [
        {
            "header": header,
            "sections": [{"widgets": [widget]}],
        },
    ]
    return requests.post(webhook_url, json={"cards": cards})


def send_slack_message(webhook_url: str):
    json_str = os.path.join(SLACK_MESSENGER_NOTIFICATION_STR)
    with open(os.path.expanduser(json_str)) as fd:
        json_data = fd.read()
    data = parse_json_for_message(json_data)
    return requests.post(webhook_url, json=data)


def send_text_message(title: str, subtitle: str, paragraph: str, webhook_url: str):
    header = {"title": title, "subtitle": subtitle}
    widget = {"textParagraph": {"text": paragraph}}
    cards = [
        {
            "header": header,
            "sections": [{"widgets": [widget]}],
        },
    ]
    return requests.post(webhook_url, json={"cards": cards})


def get_cluster_role():
    # cluster role
    return "ACM Cluster" if config.MULTICLUSTER["acm_cluster"] else "ODF Cluster"


def parse_html_for_message(html_data: str):
    # username
    username = get_username()

    # password
    password = get_password()

    # cluster status
    status = get_cluster_status()
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
    cluster_url = get_cluster_url()
    cluster_url_tag = f"<a href={cluster_url}> {cluster_url} </a>"

    # server
    server_api = get_cluster_api()
    server_api_tag = f"<a href={server_api}> {server_api} </a>"

    # login command
    login_cmd = get_cluster_command(username, password)

    html_data = html_data.replace("{ username }", username)
    html_data = html_data.replace("{ password }", password)
    html_data = html_data.replace("{ ocp_cluster_status }", status_tag)
    html_data = html_data.replace("{ ocp_cluster_version }", cluster_version)
    html_data = html_data.replace("{ url }", cluster_url_tag)
    html_data = html_data.replace("{ server }", server_api_tag)
    html_data = html_data.replace("{ login_command }", login_cmd)
    return html_data


def parse_json_for_message(json_data: str):
    # username
    username = get_username()

    # password
    password = get_password()

    # cluster status
    status = get_cluster_status()

    # cluster version
    cluster_version = get_ocp_version()

    # cluster URL
    cluster_url = get_cluster_url()

    # server
    server_api = get_cluster_api()

    # login command
    login_cmd = get_cluster_command(username, password)

    json_data = json_data.replace("{ username }", username)
    json_data = json_data.replace("{ password }", password)
    json_data = json_data.replace("{ ocp_cluster_status }", status)
    json_data = json_data.replace("{ emoji }", ":fire:")
    json_data = json_data.replace("{ ocp_cluster_version }", cluster_version)
    json_data = json_data.replace("{ url }", cluster_url)
    json_data = json_data.replace("{ server }", server_api)
    json_data = json_data.replace("{ login_command }", login_cmd)
    json_data = json_data.replace("{ slack_channel }", "#odf-cluster-messenger")
    json_data = json_data.replace("{ color }", "#ad1721")
    json_object = json.loads(json_data)
    return json_object
