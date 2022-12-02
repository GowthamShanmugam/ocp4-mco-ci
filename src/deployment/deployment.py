import logging
import multiprocessing as mp

from src.deployment.ocp import OCPDeployment
from src import framework


def set_log_level(ci_logs_dir="", log_cli_level="DEBUG"):
    logging.basicConfig(
        filename=ci_logs_dir or "DEBUG",
        filemode='w',
        format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s', datefmt='%d-%b-%y %H:%M:%S',
        level=log_cli_level
    )

class Deployment(object):
    def __init__(self, ci_logs_dir="", log_cli_level="DEBUG"):
        self.log_cli_level = log_cli_level
        set_log_level(ci_logs_dir, self.log_cli_level)

    def deploy_ocp(self, ocpDeployment, log_cli_level):
        ocpDeployment.deploy_ocp(log_cli_level)

    def run(self):
        processes = []

        for i in range(framework.config.nclusters):
            framework.config.switch_ctx(i)
            ocpDeployment = OCPDeployment(framework.config.clusters[i])
            p = mp.Process(target=self.deploy_ocp, args=(ocpDeployment, self.log_cli_level,))
            processes.append(p)

        [x.start() for x in processes]