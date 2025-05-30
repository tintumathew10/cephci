import random
import string
import traceback

from tests.cephfs.cephfs_utilsV1 import FsUtils
from utility.log import Log

log = Log(__name__)


def run(ceph_cluster, **kw):
    """
    Test Cases Covered:
    CEPH-83573872   Explore kernel mount of more than 2 Filesystem on same client.
                    Also verify persistent mounts upon reboots.
    Pre-requisites :
    1. We need atleast one client node to execute this test case

    Test Case Flow:
    1. Create 2 file systems if not present
    2. mount both the file systems and usingkernel mount and fstab entry
    3. reboot the node
    4. validate if the mount points are still present
    """
    try:
        test_data = kw.get("test_data")
        fs_util = FsUtils(ceph_cluster, test_data=test_data)
        config = kw.get("config")
        clients = ceph_cluster.get_ceph_objects("client")
        build = config.get("build", config.get("rhbuild"))
        fs_util.prepare_clients(clients, build)
        fs_util.auth_list(clients)
        log.info("checking Pre-requisites")
        if not clients:
            log.info(
                f"This test requires minimum 1 client nodes.This has only {len(clients)} clients"
            )
            return 1
        client1 = clients[0]

        fs_name = "cephfs_fstab_kernel"
        fs_util.create_fs(client1, vol_name=fs_name)
        if not fs_util.wait_for_mds_process(client1, fs_name):
            log.error("Failed to create MDS for the filesystem {}".format(fs_name))
            return 1
        total_fs = fs_util.get_fs_details(client1)
        if len(total_fs) < 2:
            log.error(
                "We can't proceed with the test case as we are not able to create 2 filesystems"
            )

        fs_names = [fs["name"] for fs in total_fs]
        mounting_dir = "".join(
            random.choice(string.ascii_lowercase + string.digits)
            for _ in list(range(10))
        )
        kernel_mounting_dir_1 = f"/mnt/cephfs_kernel{mounting_dir}_1/"
        kernel_mounting_dir_2 = f"/mnt/cephfs_kernel{mounting_dir}_2/"
        mon_node_ips = fs_util.get_mon_node_ips()
        fs_util.kernel_mount(
            [clients[0]],
            kernel_mounting_dir_1,
            ",".join(mon_node_ips),
            extra_params=f",fs={fs_names[0]}",
            fstab=True,
        )
        fs_util.kernel_mount(
            [clients[0]],
            kernel_mounting_dir_2,
            ",".join(mon_node_ips),
            extra_params=f",fs={fs_names[1]}",
            fstab=True,
        )
        fs_util.reboot_node(client1)
        out, rc = client1.exec_command(cmd="mount")
        mount_output = out.split()
        log.info("validate kernel mount:")
        assert kernel_mounting_dir_1.rstrip("/") in mount_output, "Kernel mount failed"
        assert kernel_mounting_dir_2.rstrip("/") in mount_output, "Kernel mount failed"
        return 0
    except Exception as e:
        log.info(e)
        log.info(traceback.format_exc())
        return 1
    finally:
        fs_util.client_clean_up(
            "umount",
            kernel_clients=[clients[0]],
            mounting_dir=kernel_mounting_dir_1,
        )
        fs_util.client_clean_up(
            "umount",
            kernel_clients=[clients[0]],
            mounting_dir=kernel_mounting_dir_2,
        )

        commands = [
            "ceph config set mon mon_allow_pool_delete true",
            f"ceph fs volume rm {fs_name} --yes-i-really-mean-it",
        ]
        for command in commands:
            client1.exec_command(sudo=True, cmd=command)
        client1.exec_command(
            sudo=True, cmd="mv /etc/fstab.backup /etc/fstab", check_ec=False
        )
