import os

# Directories
TOP_DIR = os.path.abspath(".")
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
ODF_OLM_YAML = os.path.join(TEMPLATE_DIR, "deploy-with-olm.yaml")
MCO_OLM_YAML = os.path.join(TEMPLATE_DIR, "mco-deploy-with-olm.yaml")
AWS_IAM_POLICY_JSON = os.path.join(TEMPLATE_DIR, "aws-iam-policy.json")
STORAGE_CLUSTER_YAML = os.path.join(TEMPLATE_DIR, "storage-cluster.yaml")
SSL_CERTIFICATE_YAML = os.path.join(TEMPLATE_DIR, "ssl-certificate.yaml")
NAMESPACE_TEMPLATE = os.path.join(TEMPLATE_DIR, "namespace.yaml")
GCHAT_MESSENGER_NOTIFICATION_STR = os.path.join(
    TEMPLATE_DIR, "result-gchat-messenger-template.txt"
)
SLACK_MESSENGER_NOTIFICATION_STR = os.path.join(
    TEMPLATE_DIR, "result-slack-messenger-template.json"
)


# Operators
OPERATOR_INTERNAL_SELECTOR = "ocs-operator-internal=true"
OPERATOR_SOURCE_NAME = "ocs-operatorsource"
SUBSCRIPTION = "subscriptions.v1alpha1.operators.coreos.com"
OPENSHIFT_STORAGE_NAMESPACE = "openshift-storage"
OPENSHIFT_OPERATORS = "openshift-operators"
ACM_OPERATOR_NAMESPACE = "open-cluster-management"
OCS_PLUGIN_NAME = "odf-console"
MCO_PLUGIN_NAME = "odf-multicluster-console"
OADP_NAMESPACE = "openshift-adp"
OADP_OPERATOR_NAME = "redhat-oadp-operator"
OADP_SUBSCRIPTION_YAML = os.path.join(
    TEMPLATE_DIR, "oadp-deployment", "subscription.yaml"
)
OADP_NS_YAML = os.path.join(TEMPLATE_DIR, "oadp-deployment", "namespace_opg_oadp.yaml")

# GitOps
GITOPS_NAMESPACE = "openshift-gitops"
GITOPS_OPERATOR_NAME = "openshift-gitops-operator"
GITOPS_CLUSTER_NAME = "gitops-cluster"
GITOPS_CLUSTER = "GitOpsCluster"
GITOPS_CLUSTER_NAMESPACE = "openshift-gitops"
GITOPS_CLUSTER_YAML = os.path.join(
    TEMPLATE_DIR, "gitops-deployment", "gitops_cluster.yaml"
)
GITOPS_PLACEMENT_YAML = os.path.join(
    TEMPLATE_DIR, "gitops-deployment", "gitops_placement.yaml"
)
GITOPS_MANAGEDCLUSTER_SETBINDING_YAML = os.path.join(
    TEMPLATE_DIR, "gitops-deployment", "managedcluster_setbinding.yaml"
)
GITOPS_SUBSCRIPTION_YAML = os.path.join(
    TEMPLATE_DIR, "gitops-deployment", "subscription.yaml"
)

# ACM Hub Parameters
ACM_HUB_OPERATORGROUP_YAML = os.path.join(
    TEMPLATE_DIR, "acm-deployment", "operatorgroup.yaml"
)
ACM_HUB_SUBSCRIPTION_YAML = os.path.join(
    TEMPLATE_DIR, "acm-deployment", "subscription.yaml"
)
ACM_HUB_MULTICLUSTERHUB_YAML = os.path.join(
    TEMPLATE_DIR, "acm-deployment", "multiclusterhub.yaml"
)
ACM_MULTICLUSTER_HUB = "MultiClusterHub"
ACM_HUB_NAMESPACE = "open-cluster-management"
ACM_HUB_OPERATOR_NAME = "advanced-cluster-management"
ACM_MULTICLUSTER_RESOURCE = "multiclusterhub"
ACM_HUB_UNRELEASED_DEPLOY_REPO = "https://github.com/stolostron/deploy.git"
ACM_HUB_UNRELEASED_PULL_SECRET_TEMPLATE = "pull-secret.yaml.j2"
ACM_HUB_UNRELEASED_ICSP_YAML = os.path.join(
    TEMPLATE_DIR, "acm-deployment", "imagecontentsourcepolicy.yaml"
)
ACM_MANAGEDCLUSTER = "managedclusters.cluster.open-cluster-management.io"
ACM_LOCAL_CLUSTER = "local-cluster"
ACM_CLUSTERSET_LABEL = "cluster.open-cluster-management.io/clusterset"

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
AWS_IAM_POLICY_NAME = "mirroring_pool"

# other
WORKER_MACHINE = "worker"
MASTER_MACHINE = "master"

# labels
WORKER_LABEL = "node-role.kubernetes.io/worker"
ZONE_LABEL = "topology.kubernetes.io/zone"
INFRA_NODE_LABEL = "node-role.kubernetes.io/infra=''"
OPERATOR_NODE_LABEL = "cluster.ocs.openshift.io/openshift-storage=''"

# storage cluster
STORAGE_CLUSTER_NAME = "ocs-storagecluster"

# Resources / Kinds
MACHINECONFIGPOOL = "MachineConfigPool"

# Provisioners
SUBSCRIPTION_WITH_ACM = "Subscription.operators.coreos.com"

# Messenger types
DEFUALT_MESSENGER_TYPE = "slack"

# Multicluster related yamls
MIRROR_PEER_RDR = os.path.join(TEMPLATE_DIR, "mirror_peer_rdr.yaml")
DR_POLICY_ACM_HUB = os.path.join(TEMPLATE_DIR, "dr_policy_acm_hub.yaml")
DPA_DISCOVERED_APPS_PATH = os.path.join(
    TEMPLATE_DIR, "oadp-deployment", "dpa_discovered_apps.yaml"
)
DR_RAMEN_HUB_OPERATOR_CONFIG = "ramen-hub-operator-config"
DR_RAMEN_CONFIG_MANAGER_KEY = "ramen_manager_config.yaml"
