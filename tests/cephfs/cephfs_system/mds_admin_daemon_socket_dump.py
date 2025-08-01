import json
import random
import string
import traceback

from ceph.ceph import CommandFailed
from ceph.parallel import parallel
from tests.cephfs.cephfs_utilsV1 import FsUtils
from tests.cephfs.lib.cephfs_common_lib import CephFSCommonUtils
from tests.io.fs_io import fs_io
from utility.log import Log
from utility.retry import retry

log = Log(__name__)


def run(ceph_cluster, **kw):
    """
    Pre-requisite:
    1. Configure cluster and PG's in active + clean state.
    2. Make sure cluster is up and configured with Single CephFS, 3 MDS (2 active and 1 standby)
    3. required 2 clients. Configure minimum 2 clients with Fuse and kernel client.
    Steps:
    1. dmin daemon commands from active MDS node.
    2. Perform each dump command and make sure cluster health is ok before performing next command.
    3. Make sure Cluster is loaded enough before running all this commands.
    """
    try:
        tc = "CEPH-83572891"
        log.info(f"Running CephFS tests for -{tc}")
        test_data = kw.get("test_data")
        cephfs_common_utils = CephFSCommonUtils(ceph_cluster)
        fs_util = FsUtils(ceph_cluster, test_data=test_data)

        erasure = (
            FsUtils.get_custom_config_value(test_data, "erasure")
            if test_data
            else False
        )
        config = kw.get("config")
        clients = ceph_cluster.get_ceph_objects("client")
        mds_nodes = ceph_cluster.get_ceph_objects("mds")
        build = config.get("build", config.get("rhbuild"))
        fs_util.prepare_clients(clients, build)
        fs_util.auth_list(clients)
        client1 = clients[0]
        fs_name = "cephfs" if not erasure else "cephfs-ec"
        fs_details = fs_util.get_fs_info(client1, fs_name)

        if not fs_details:
            fs_util.create_fs(client1, fs_name)
        mounting_dir = "".join(
            random.choice(string.ascii_lowercase + string.digits)
            for _ in list(range(10))
        )
        retry_ceph_health = retry(CommandFailed, tries=4, delay=60)(
            cephfs_common_utils.wait_for_healthy_ceph
        )
        rc = retry_ceph_health(clients[0])
        if rc:
            return rc
        kernel_mounting_dir_1 = f"/mnt/cephfs_kernel{mounting_dir}_1/"
        mon_node_ips = fs_util.get_mon_node_ips()
        fs_util.kernel_mount(
            [client1],
            kernel_mounting_dir_1,
            ",".join(mon_node_ips),
            extra_params=f",fs={fs_name}",
        )
        fuse_mounting_dir_1 = f"/mnt/cephfs_fuse{mounting_dir}_1/"
        fs_util.fuse_mount(
            [client1], fuse_mounting_dir_1, extra_params=f" --client_fs {fs_name}"
        )
        cephfs = {
            "fill_data": 50,
            "io_tool": "smallfile",
            "mount": "fuse",
            "filesystem": "cephfs",
            "mount_dir": f"{fuse_mounting_dir_1}",
        }
        with parallel() as p:
            p.spawn(fs_io, client=clients[0], fs_config=cephfs, fs_util=fs_util)
        target_mds = mds_nodes[0]
        target_mds_name = target_mds.node.hostname
        dump_list = [
            "dump cache /",
            "dump tree /",
            "dump loads",
            "dump_blocked_ops",
            "dump_historic_ops",
            "dump_historic_ops_by_duration",
            "dump_mempools",
            "dump_ops_in_flight",
            "log dump",
            "perf dump",
            "perf histogram dump",
        ]
        out1, ec = client1.exec_command(
            sudo=True, cmd=f"ceph fs status {fs_name} -f json-pretty"
        )
        output1 = json.loads(out1)
        mdsmap = output1["mdsmap"]
        mds_1 = ""
        for mds in mdsmap:
            if target_mds_name in mds["name"]:
                mds_1 = mds["name"]
        admin_daemon = (
            f"cephadm shell ceph --admin-daemon /var/run/ceph/ceph-mds.{mds_1}.asok "
        )
        target_mds.exec_command(
            sudo=True, cmd=f"{admin_daemon} config set debug_mds 10"
        )
        target_mds.exec_command(
            sudo=True, cmd=f"{admin_daemon} config set debug_client 10"
        )
        for dump in dump_list:
            target_mds.exec_command(sudo=True, cmd=f"{admin_daemon} {dump}")
            if cephfs_common_utils.wait_for_healthy_ceph(client1, 300):
                log.error("Cluster health is not OK even after waiting for 300secs")
                return 1
        out2 = client1.exec_command(sudo=True, cmd="ceph fs dump")
        log.info(out2)
        return 0
    except Exception as e:
        log.error(e)
        log.error(traceback.format_exc())
        return 1
    finally:
        fs_util.client_clean_up(
            "umount", fuse_clients=[clients[0]], mounting_dir=kernel_mounting_dir_1
        )
        fs_util.client_clean_up(
            "umount", fuse_clients=[clients[0]], mounting_dir=fuse_mounting_dir_1
        )
