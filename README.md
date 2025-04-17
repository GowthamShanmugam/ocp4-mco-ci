# OCP4MCO-CI

## Pre-requisite

### Secrets
1. `pull-secret` - Keep your pull secret under `data/pull-secret` file. Create `data` directory manually if not exists.
2. `auth.yaml` - Keep your quay token under `data/auth.yaml` to install ACM pre-release downstream build.
    In order to get a QUAY_TOKEN, go to your quay.io "Account Settings" page by selecting your username/icon in the top 
    right corner of the page, then "Generate Encrypted Password".  Choose "Kubernetes Secret" and copy just secret text 
    that follows .dockerconfigjson:. 
   ```
   quay:
     cli_password: 'your quay token'
   ```
3. To deploy ACM downstream pre-released version, Add the pull-secrets for the `quay.io:443` registry with access to the quay.io/acm-d repository in your OpenShift main pull-secret.  [For more](https://github.com/stolostron/deploy#deploying-downstream-builds-snapshots-for-product-quality-engineering-only-20)
4. To install ODF downstream pre-released version, Add the pull-secrets for the `quay.io/rhceph-dev` registry with access to the quay.io/rhceph-dev repository in your OpenShift main pull-secret.

## Installing
1. Setup a python 3.7 virtual environment. This is actually quite easy to do now. Use hidden .venv or normal venv folder for virtual env as we are ignoring this in flake8 configuration in tox.
```
python3.7 -m venv <path/to/venv>
source <path/to/.venv>/bin/activate
```
2. Upgrade pip and setuptools with `pip install --upgrade pip setuptools`

3. Build OCP4MCO-CI: `python setup.py  build`
3. Install OCP4MCO-CI: `python setup.py  install`

## Scheduler Configuration

1. If you want to run the scheduler scripts (like `scripts/deploy-uk-ocp.py`), follow these steps:

* Create the `env.yaml` file from the sample file and set the environment variables:
```
cp ./config/env.yaml.sample ./config/env.yaml
```

* Create the ocp config file (required to set the `ocp_config` env.yaml variable) from a sample file and customize it:
```
cp ./samples/deploy_ocp_cluster/override_config.yaml ./config/ocp_config.yaml
```

2. If you want to run the scheduler scripts for disaster recovery (like `scripts/deploy-dr-ocp.py`), follow these steps:

* Create the `env.dr.yaml` file from the sample file and set the environment variables:
```
cp ./config/env.dr.yaml.sample ./config/env.dr.yaml
```

* Create ocp config files (required to set the `*_config` env.dr.yaml variables) from a sample files and customize it:
```
cp ./samples/2_cluster_acm_setup/override_config.yaml ./config/2_cluster_acm_setup/override_config.yaml
cp ./samples/2_cluster_acm_setup/override_hub_config.yaml ./config/2_cluster_acm_setup/override_hub_config.yaml
cp ./samples/configure_submariner/override_config.yaml ./config/configure_submariner/override_config.yaml
cp ./samples/configure_submariner/override_hub_config.yaml ./config/configure_submariner/override_hub_config.yaml
```

## Usage
For full usage run: `deploy-ocp --help`

## Subcommand
`multicluster <int>` - to be used if multiple clusters needs to be handled by ocp4mco-ci,
For more information on the usage check examples section and deploy-ocp `multicluster --help`.

## Required arguments
`--cluster-path <path>` - path to the directory which will contain all the installation/authentication information about the cluster.
If you wish to deploy a new cluster, give a path to a new directory.

`--cluster-name <path>` - Name for the OCP cluster. If you wish to deploy a new cluster, give a path to a new cluster name.

## Email notification
`--email-ids`: A comma separated recipient emails to notifify the cluster credentials.

## Override default config
`--ocp4mco-conf` - with this configuration parameter you can overwrite the default OCP4MCO-CI config parameters defined in `default_config.yaml`

## Examples
### For single cluster deployment:
```commandline
Deploy single cluster:
deploy-ocp --cluster-name {cluster_name} --cluster-path {cluster_path}

Override default cluster config:
deploy-ocp --cluster-name {cluster_name} --cluster-path {cluster_path} --ocp4mcoci-conf {override yaml file}

Email notification:
deploy-ocp --cluster-name {cluster_name} --cluster-path {cluster_path} --email-ids {comma seperated mail ids without space}

Slack or Gchat notification (Default is slack message, for gchat override the default cluster config):
deploy-ocp --cluster-name {cluster_name} --cluster-path {cluster_path} --webhook-url "{webhook url}"
```
### For multiple cluster deployment:
```commandline
Deploy multiple cluster:
deploy-ocp  multicluster {cluster_count}  --cluster1 --cluster-name {cluster_name} --cluster-path {cluster_path} --cluster(n) --cluster-name {cluster_name} --cluster-path {cluster_path}

Override default cluster config:
deploy-ocp  multicluster {cluster_count}  --cluster1 --ocp4mcoci-conf {override yaml file} --cluster-name {cluster_name} --cluster-path {cluster_path} --cluster(n) --ocp4mcoci-conf {override yaml file} --cluster-name {cluster_name} --cluster-path {cluster_path}

Email notification:
deploy-ocp  multicluster {cluster_count} --email-ids {comma seperated mail ids without space} --cluster1 --cluster-name {cluster_name} --cluster-path {cluster_path}  --cluster(n) --cluster-name {cluster_name} --cluster-path {cluster_path}

Common argument for all clusters:
deploy-ocp  multicluster {cluster_count}  --ocp4mcoci-conf {override yaml file}  --email-ids {comma seperated mail ids without space} --cluster1 --cluster-name {cluster_name} --cluster-path {cluster_path} --cluster(n) --cluster-name {cluster_name} --cluster-path {cluster_path}

Slack or Gchat notification (Default is slack message, for gchat override the default cluster config):
deploy-ocp  multicluster {cluster_count}  --webhook-url "{webhook url}" --cluster1 --cluster-name {cluster_name} --cluster-path {cluster_path}  --cluster(n) --cluster-name {cluster_name} --cluster-path {cluster_path}
```

### Example override yaml file [For more example](https://github.com/GowthamShanmugam/ocp4-mco-ci/tree/master/samples)
```commandline
DEPLOYMENT:
  force_download_installer: false
  installer_version: "4.12.0-0.nightly-2022-07-25-055755"
  ocp_mirror_url: "https://mirror.openshift.com/pub/openshift-v4/x86_64/clients/ocp-dev-preview" 
```

## Email
To send cluster information to email ID’s, postfix should be installed on fedora
```commandline
    * sudo dnf install postfix
    * systemctl enable postfix.service
    * systemctl start postfix.service
```

## Logging

### CLI Log Level
You can control the verbosity of the logs using the `--log-cli-level` argument. This allows you to specify the logging level for the deployment process. The available levels are: `DEBUG`, `INFO`, `WARNING`, `ERROR`, and `CRITICAL`.

#### Example
```commandline
deploy-ocp --cluster-name mycluster --cluster-path /path/to/cluster --log-cli-level DEBUG
```
This will output detailed debugging information to the console during execution.

### Log File Output
All logs are also saved to a file for later inspection. The log file is created under a logs/ directory in the format:
```commandline
logs/deployment_<YYYYMMDD_HHMMSS>.log
```
This helps in tracking logs across multiple deployment runs without overwriting previous logs.