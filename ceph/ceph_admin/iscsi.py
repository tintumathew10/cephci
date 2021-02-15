"""Module to deploy and manage Ceph's iSCSI service."""
from typing import Dict

from .apply import ApplyMixin
from .orch import Orch


class ISCSI(ApplyMixin, Orch):
    """Interface to Ceph's iSCSI service via cephadm CLI."""

    SERVICE_NAME = "iscsi"

    def apply(self, config: Dict) -> None:
        """
        Deploy ISCSI client daemon using the provided arguments.

        Args:
            config: Key/value pairs provided from the test scenario

        Example:
            config:
                command: apply
                service: iscsi
                base_cmd_args:          # arguments to ceph orch
                    concise: true
                    verbose: true
                    input_file: <name of spec>
                pos_args:
                    - india             # name of the pool
                    - api_user          # name of the API user
                    - api_pass          # password of the api_user.
                    - trusted_ip_list   # space separate list of IPs
                args:
                    placement:
                        label: iscsi    # either label or node.
                        nodes:
                            - node1
                        limit: 3    # no of daemons
                        sep: " "    # separator to be used for placements
                    dry-run: true
                    unmanaged: true
                temp_args:              # In place till OSD object is implemented.
                    pool_pg_num: <count>
                    pool_pgp_num: <count>
        """
        # Temp workaround that needs to be removed
        pool = config["ps_args"][0]
        temp_args = config.pop("temp_args", {})
        pg_num = temp_args.get("pool_pg_num", 3)
        pgp_num = temp_args.get("pool_pgp_num", 3)

        # Execute pre-requisites
        self.shell(
            args=[
                "ceph",
                "osd",
                "pool",
                "create",
                pool,
                str(pg_num),
                str(pgp_num),
                "replicated",
            ],
        )

        # Associate pool to RBD application
        self.shell(args=["ceph", "osd", "pool", "application", "enable", pool, "rbd"])

        super().apply(config=config)
