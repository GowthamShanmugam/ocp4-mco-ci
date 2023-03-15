import os

# Directories
TOP_DIR = os.path.abspath('.')
EXTERNAL_DIR = os.path.join(TOP_DIR, "external")
TEMPLATE_DIR = os.path.join(TOP_DIR, "src", "templates")
CATALOG_SOURCE_YAML = os.path.join(TEMPLATE_DIR, "catalog-source.yaml")
EMAIL_NOTIFICATION_HTML = os.path.join(TEMPLATE_DIR, "result-email-template.html")
LOG_FORMAT = "%(asctime)s - %(threadName)s - %(name)s - %(levelname)s %(clusterctx)s - %(message)s"
BASIC_FORMAT = "%(asctime)s - %(threadName)s - %(name)s - %(levelname)s - %(message)s"
OPERATOR_CATALOG_SOURCE_NAME = "redhat-operators"
PATCH_SPECIFIC_SOURCES_CMD = (
    "oc patch operatorhub.config.openshift.io/cluster -p="
    '\'{{"spec":{{"sources":[{{"disabled":{disable},"name":"{source_name}"'
    "}}]}}}}' --type=merge"
)
CATALOG_SOURCE_YAML = os.path.join(TEMPLATE_DIR, "catalog-source.yaml")
SUBSCRIPTION_ODF_YAML = os.path.join(TEMPLATE_DIR, "subscription_odf.yaml")
SUBSCRIPTION_MCO_YAML = os.path.join(TEMPLATE_DIR, "subscription_mco.yaml")
SUBSCRIPTION_YAML = os.path.join(TEMPLATE_DIR, "subscription.yaml")
MARKETPLACE_NAMESPACE = "openshift-marketplace"
OLM_YAML = os.path.join(TEMPLATE_DIR, "deploy-with-olm.yaml")
MCO_OLM_YAML = os.path.join(TEMPLATE_DIR, "mco-deploy-with-olm.yaml")
AWS_IAM_POLICY_JSON = os.path.join(TEMPLATE_DIR, "aws-iam-policy.json")
STORAGE_CLUSTER_YAML = os.path.join(TEMPLATE_DIR, "storage-cluster.yaml")

# Operators
OPERATOR_INTERNAL_SELECTOR = "ocs-operator-internal=true"
OPERATOR_SOURCE_NAME = "ocs-operatorsource"
SUBSCRIPTION = "subscriptions.v1alpha1.operators.coreos.com"
OPENSHIFT_STORAGE_NAMESPACE = "openshift-storage"
MCO_OPERATOR_NAMESPACE = "openshift-operators"
ACM_OPERATOR_NAMESPACE = "open-cluster-management"
OCS_PLUGIN_NAME = "odf-console"
MCO_PLUGIN_NAME = "odf-multicluster-console"

# ACM Hub Parameters
ACM_MULTICLUSTER_HUB = "MultiClusterHub"
ACM_HUB_NAMESPACE = "open-cluster-management"
ACM_MULTICLUSTER_RESOURCE = "multiclusterhub"
ACM_HUB_UNRELEASED_DEPLOY_REPO = "https://github.com/stolostron/deploy.git"
ACM_HUB_UNRELEASED_PULL_SECRET_TEMPLATE = "pull-secret.yaml.j2"
ACM_HUB_UNRELEASED_ICSP_YAML = os.path.join(
    TEMPLATE_DIR, "acm-deployment", "imagecontentsourcepolicy.yaml"
)

# Statuses
STATUS_RUNNING = "Running"

# Auth Yaml
AUTHYAML = "auth.yaml"

# URLs
AUTH_CONFIG_DOCS = (
    "https://ocs-ci.readthedocs.io/en/latest/docs/getting_started.html"
    "#authentication-config"
)

# Deployment constants
OCS_CSV_PREFIX = "ocs-operator"

# Submariner constants
SUBMARINER_GATEWAY_NODE_LABEL = "submariner.io/gateway=true"
SUBMARINER_DOWNLOAD_URL = "https://get.submariner.io"
AWS_IAM_POLICY_NAME = 'mirroring_pool'

# other
WORKER_MACHINE = "worker"

# labels
WORKER_LABEL = "node-role.kubernetes.io/worker"
ZONE_LABEL = "topology.kubernetes.io/zone"
INFRA_NODE_LABEL = "node-role.kubernetes.io/infra=''"
OPERATOR_NODE_LABEL = "cluster.ocs.openshift.io/openshift-storage=''"

# storage cluster
STORAGE_CLUSTER_NAME = "ocs-storagecluster"
