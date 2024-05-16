"""
General OCS object
"""

import logging
import tempfile

from src.ocs.ocp import OCP

log = logging.getLogger(__name__)


class OCS(object):
    """
    Base OCSClass
    """

    def __init__(self, **kwargs):
        """
        Initializer function
        Args:
            kwargs (dict):
                1) For existing resource, use OCP.reload() to get the
                resource's dictionary and use it to pass as **kwargs
                2) For new resource, use yaml files templates under
                /templates/CSI like:
                obj_dict = load_yaml(
                    os.path.join(
                        TEMPLATE_DIR, "some_resource.yaml"
                        )
                    )
        """
        self.data = kwargs
        self._api_version = self.data.get("api_version")
        self._kind = self.data.get("kind")
        self._namespace = None
        if "metadata" in self.data:
            self._namespace = self.data.get("metadata").get("namespace")
            self._name = self.data.get("metadata").get("name")
        if "threading_lock" in self.data:
            self.threading_lock = self.data.pop("threading_lock")
        else:
            self.threading_lock = None
        self.ocp = OCP(
            api_version=self._api_version,
            kind=self._kind,
            namespace=self._namespace,
            threading_lock=self.threading_lock,
        )
        with tempfile.NamedTemporaryFile(
            mode="w+", prefix=self._kind, delete=False
        ) as temp_file_info:
            self.temp_yaml = temp_file_info.name
        # This _is_delete flag is set to True if the delete method was called
        # on object of this class and was successfull.
        self._is_deleted = False

    def get(self, out_yaml_format=True):
        return self.ocp.get(resource_name=self.name, out_yaml_format=out_yaml_format)

    def add_label(self, label):
        """
        Addss a new label
        Args:
            label (str): New label to be assigned for this pod
                E.g: "label=app='rook-ceph-mds'"
        """
        status = self.ocp.add_label(resource_name=self.name, label=label)
        self.reload()
        return status

    def reload(self):
        """
        Reloading the OCS instance with the new information from its actual
        data.
        After creating a resource from a yaml file, the actual yaml file is
        being changed and more information about the resource is added.
        """
        cluster_kubeconfig = self.ocp.cluster_kubeconfig
        self.data = self.get()
        self.__init__(**self.data)
        self.ocp.cluster_kubeconfig = cluster_kubeconfig

    @property
    def api_version(self):
        return self._api_version

    @property
    def kind(self):
        return self._kind

    @property
    def namespace(self):
        return self._namespace

    @property
    def name(self):
        return self._name
