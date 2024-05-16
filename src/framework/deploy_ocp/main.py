import argparse
import os
import re
import sys
import yaml
import time

from src import framework
from src.utility.exceptions import UnSupportedPlatformException
from src.utility import utils
from src.framework.deployment import Deployment


def check_config_requirements():
    """
    Checking if all required parameters were passed
    Raises:
        MissingRequiredConfigKeyError: In case of some required parameter is
            not defined.
    """
    # Check for vSphere required parameters
    if hasattr(framework.config, "ENV_DATA") and (
        framework.config.ENV_DATA.get("platform", "").lower() != "aws"
    ):
        raise UnSupportedPlatformException("Only AWS platform is supported")


def load_config(config_files):
    """
    This function load the conf files in the order defined in config_files
    list.
    Args:
        config_files (list): conf file paths
    """
    for config_file in config_files:
        with open(os.path.abspath(os.path.expanduser(config_file))) as file_stream:
            custom_config_data = yaml.safe_load(file_stream)
            framework.config.update(custom_config_data)


def init_ocp4mcoci_conf(arguments=None):
    """
    Update the conf object with any files passed via the CLI
    Args:
        arguments (list): Arguments for pytest execution
    """
    framework.config.run_id = int(time.time())
    if "multicluster" in arguments:
        parser = argparse.ArgumentParser(add_help=False)
        subparser = parser.add_subparsers(title="subcommand", dest="subcommand")
        mcluster_parser = subparser.add_parser(
            "multicluster",
            description="multicluster nclusters --cluster1 <> --cluster2 <> ...",
        )

        # We need this nclusters here itself to do add_arguments for
        # N number of clusters in the function init_multicluster_ocsci_conf()
        mcluster_parser.add_argument(
            "nclusters", type=int, help="Number of clusters to be deployed"
        )
        args, _ = parser.parse_known_args(arguments)
        init_multicluster_ocp4mcoci_conf(arguments, args.nclusters)
    else:
        framework.config.init_cluster_configs()
        process_ocp4mcoci_conf(arguments)
        process_cluster_name_conf(arguments)
        process_cluster_path_conf(arguments)
        process_email_recipients(arguments)
        check_config_requirements()


def init_multicluster_ocp4mcoci_conf(args, nclusters):
    """
    Parse multicluster specific arguments and seperate out each cluster's configuration.
    Then instantiate Config class for each cluster
    Params:
        args (list): of arguments passed
        nclusters (int): Number of clusters (>1)
    """
    parser = argparse.ArgumentParser(add_help=False)
    # Dynamically adding the argument --cluster$i to enforce
    # user's to pass --cluster$i param followed by normal cluster conf
    # options so that separation of per cluster conf will be easier
    for i in range(nclusters):
        parser.add_argument(
            f"--cluster{i+1}",
            required=True,
            action="store_true",
            help=(
                "Index argument for per cluster args, "
                "this marks the start of the cluster{i} args"
                "any args between --cluster{i} and --cluster{i+1} will be",
                "considered as arguments for cluster{i}",
            ),
        )

    # Parsing just to enforce `nclusters` number of  --cluster{i} arguments are passed
    _, _ = parser.parse_known_args(args[2:])
    multicluster_conf, common_argv = tokenize_per_cluster_args(args[2:], nclusters)

    # We need to seperate common arguments and cluster specific arguments
    framework.config.multicluster = True
    framework.config.nclusters = nclusters
    framework.config.init_cluster_configs()
    framework.config.reset_ctx()
    for index in range(nclusters):
        framework.config.switch_ctx(index)
        process_ocp4mcoci_conf(common_argv + multicluster_conf[index][1:])
        process_cluster_name_conf(common_argv + multicluster_conf[index][1:])
        process_cluster_path_conf(common_argv + multicluster_conf[index][1:])
        process_email_recipients(common_argv + multicluster_conf[index][1:])
        check_config_requirements()
    # Set context to default_cluster_context_index
    framework.config.switch_default_cluster_ctx()


def tokenize_per_cluster_args(args, nclusters):
    """
    Seperate per cluster arguments so that parsing becomes easy
    Params:
        args: Combined arguments
        nclusters(int): total number of clusters
    Returns:
        list of lists: Each cluster conf per list
            ex: [[cluster1_conf], [cluster2_conf]...]
    """
    per_cluster_argv = list()
    multi_cluster_argv = list()
    common_argv = list()
    cluster_ctx = False
    regexp = re.compile(r"--cluster[0-9]+")
    index = 0

    for i in range(1, nclusters + 1):
        while index < len(args):
            if args[index] == f"--cluster{i}":
                cluster_ctx = True
            elif regexp.search(args[index]):
                cluster_ctx = False
                break
            if cluster_ctx:
                per_cluster_argv.append(args[index])
            else:
                common_argv.append(args[index])
            index = index + 1
        multi_cluster_argv.append(per_cluster_argv)
        per_cluster_argv = []
    return multi_cluster_argv, common_argv


def process_ocp4mcoci_conf(arguments):
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--ocp4mcoci-conf", action="append", default=[])
    args, _ = parser.parse_known_args(args=arguments)
    load_config(args.ocp4mcoci_conf)
    bin_dir = framework.config.RUN.get("bin_dir")
    if bin_dir:
        framework.config.update(
            {
                "RUN": {
                    "bin_dir": os.path.abspath(
                        os.path.expanduser(framework.config.RUN["bin_dir"])
                    )
                }
            }
        )
        utils.add_path_to_env_path(framework.config.RUN["bin_dir"])


def process_cluster_path_conf(arguments):
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--cluster-path", default=framework.config.ENV_DATA["cluster_path"]
    )
    args, _ = parser.parse_known_args(args=arguments)
    framework.config.update({"ENV_DATA": {"cluster_path": args.cluster_path}})


def process_cluster_name_conf(arguments):
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--cluster-name", default=framework.config.ENV_DATA["cluster_name"]
    )
    args, _ = parser.parse_known_args(args=arguments)
    framework.config.update({"ENV_DATA": {"cluster_name": args.cluster_name}})


def process_log_level_arg(arguments):
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--log-cli-level", default="INFO", help="OCP installer log level"
    )
    args, _ = parser.parse_known_args(args=arguments)
    return args.log_cli_level


def process_email_recipients(arguments):
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--email-ids", default="INFO", help="recipient email ids")
    args, _ = parser.parse_known_args(args=arguments)
    framework.config.update({"REPORTING": {"email": {"recipients": args.email_ids}}})


def main(argv=None):
    arguments = argv or sys.argv[1:]
    init_ocp4mcoci_conf(arguments)
    log_cli_level = process_log_level_arg(arguments)
    deployment = Deployment()
    # Deploy OCP
    deployment.deploy_ocp(log_cli_level)
    # Deploy OCS
    deployment.deploy_ocs(log_cli_level)
    # Deploy MCO
    deployment.deploy_mco()
    # Deploy ACM
    deployment.deploy_acm()
    # Configure submariner
    deployment.configure_submariner()
    # import managed cluster
    deployment.aws_import_cluster()
    # Deploy GitOps
    deployment.deploy_gitops()
    # SSL certificate exchange
    deployment.ssl_certificate()
    # Send email report
    deployment.send_email()
    # Send gchat message
    deployment.send_message()
