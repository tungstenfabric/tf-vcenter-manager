from builtins import object
import logging
import random
import socket

import gevent.lock
import gevent.queue

from cfgm_common.uve.nodeinfo.ttypes import NodeStatus, NodeStatusUVE
from pysandesh import connection_info, sandesh_base, sandesh_logger
from sandesh_common.vns.constants import (
    INSTANCE_ID_DEFAULT,
    Module2NodeType,
    ModuleNames,
    NodeTypeNames,
    ServiceHttpPortMap,
)
from sandesh_common.vns.ttypes import Module

from cvm import clients, services, controllers, sandesh_handler
from cvm import database as db
from cvm import constants as const
from cvm.event_listener import EventListener
from cvm.models import VlanIdPool
from cvm.monitors import VMwareMonitor
from cvm.supervisor import Supervisor

logger = logging.getLogger("cvm")


def translate_log_level(level):
    # Default logging level during contrail deployment is SYS_NOTICE,
    # but python logging library hasn't notice level, so we have to translate
    # SYS_NOTICE to logging.INFO, because next available level is logging.WARN,
    # what is too high for normal vcenter-manager logging.
    if level == "SYS_NOTICE":
        return "SYS_INFO"
    return level


class CVMContext(object):
    def __init__(self, config):
        self.config = config

        self.lock = gevent.lock.BoundedSemaphore()
        self.database = db.Database()
        self.update_set_queue = gevent.queue.Queue()
        self.vlan_id_pool = VlanIdPool(
            const.VLAN_ID_RANGE_START, const.VLAN_ID_RANGE_END
        )

        self.update_handler = None
        self.vmware_controller = None
        self.vmware_monitor = None
        self.event_listener = None
        self.supervisor = None
        self.clients = {}
        self.services = {}
        self.handlers = {}

    def build(self):
        self._build_clients()
        self._build_services()
        self._build_handlers()
        self._build_controller()

        self.vmware_monitor = VMwareMonitor(
            self.vmware_controller, self.update_set_queue
        )
        self.event_listener = EventListener(
            self.vmware_controller,
            self.update_set_queue,
            self.clients["esxi_api_client"],
            self.database,
        )
        self.supervisor = Supervisor(
            self.event_listener, self.clients["esxi_api_client"]
        )

    def load_introspect_config(self):
        sandesh_config = self.config["sandesh"]
        introspect_config = dict()
        introspect_config.update(
            {
                "id": Module.VCENTER_MANAGER,
                "hostname": socket.gethostname(),
                "table": "ObjectContrailvCenterManagerNode",
                "instance_id": INSTANCE_ID_DEFAULT,
                "introspect_port": ServiceHttpPortMap[
                    "contrail-vcenter-manager"
                ],
                "collectors": sandesh_config["collectors"].split(),
                "log_file": sandesh_config["log_file"],
                "logging_level": translate_log_level(
                    sandesh_config["logging_level"]
                ),
            }
        )
        introspect_config["name"] = ModuleNames[introspect_config["id"]]
        introspect_config["node_type"] = Module2NodeType[
            introspect_config["id"]
        ]
        introspect_config["node_type_name"] = NodeTypeNames[
            introspect_config["node_type"]
        ]
        random.shuffle(introspect_config["collectors"])
        self.config["introspect_config"] = introspect_config

    def run_sandesh(self):
        sandesh_config = self.config["sandesh"]
        sandesh = sandesh_base.Sandesh()
        s_handler = sandesh_handler.SandeshHandler(self.database, self.lock)
        s_handler.bind_handlers()
        config = sandesh_base.SandeshConfig(
            http_server_ip=sandesh_config["http_server_ip"]
        )
        introspect_config = self.config["introspect_config"]
        sandesh.init_generator(
            module="cvm",
            source=introspect_config["hostname"],
            node_type=introspect_config["node_type_name"],
            instance_id=introspect_config["instance_id"],
            collectors=introspect_config["collectors"],
            client_context="cvm_context",
            http_port=introspect_config["introspect_port"],
            sandesh_req_uve_pkg_list=["cfgm_common", "cvm"],
            config=config,
        )
        connection_info.ConnectionState.init(
            sandesh=sandesh,
            hostname=introspect_config["hostname"],
            module_id=introspect_config["name"],
            instance_id=introspect_config["instance_id"],
            conn_status_cb=staticmethod(
                connection_info.ConnectionState.get_conn_state_cb
            ),
            uve_type_cls=NodeStatusUVE,
            uve_data_type_cls=NodeStatus,
            table=introspect_config["table"],
        )

    def configure_logger(self):
        introspect_config = self.config["introspect_config"]
        s_logger = sandesh_logger.SandeshLogger("cvm")
        sandesh_logger.SandeshLogger.set_logger_params(
            logger=s_logger.logger(),
            enable_local_log=True,
            level=introspect_config["logging_level"],
            file=introspect_config["log_file"],
            enable_syslog=False,
            syslog_facility=None,
        )

    def _build_controller(self):
        self.vmware_controller = controllers.VmwareController(
            update_handler=self.update_handler, lock=self.lock, **self.services
        )

    def _build_handlers(self):
        controller_kwargs = self.services
        self.handlers = [
            controllers.VmUpdatedHandler(**controller_kwargs),
            controllers.VmRenamedHandler(**controller_kwargs),
            controllers.VmReconfiguredHandler(**controller_kwargs),
            controllers.VmRemovedHandler(**controller_kwargs),
            controllers.VmRegisteredHandler(**controller_kwargs),
            controllers.GuestNetHandler(**controller_kwargs),
            controllers.VmwareToolsStatusHandler(**controller_kwargs),
            controllers.PowerStateHandler(**controller_kwargs),
        ]
        self.update_handler = controllers.UpdateHandler(self.handlers)

    def _build_services(self):
        service_kwargs = {
            "database": self.database,
            "vnc_api_client": self.clients["vnc_api_client"],
            "esxi_api_client": self.clients["esxi_api_client"],
            "vcenter_api_client": self.clients["vcenter_api_client"],
            "vrouter_api_client": self.clients["vrouter_api_client"],
            "vlan_id_pool": self.vlan_id_pool,
        }
        vm_service = services.VirtualMachineService(**service_kwargs)
        vn_service = services.VirtualNetworkService(**service_kwargs)
        vmi_service = services.VirtualMachineInterfaceService(**service_kwargs)
        vrouter_port_service = services.VRouterPortService(**service_kwargs)
        vlan_id_service = services.VlanIdService(**service_kwargs)
        self.services = {
            "vm_service": vm_service,
            "vn_service": vn_service,
            "vmi_service": vmi_service,
            "vrouter_port_service": vrouter_port_service,
            "vlan_id_service": vlan_id_service,
        }

    def _build_clients(self):
        esxi_cfg, vcenter_cfg, vnc_cfg = (
            self.config["esxi"],
            self.config["vcenter"],
            self.config["vnc"],
        )
        esxi_api_client = clients.ESXiAPIClient(esxi_cfg)
        vcenter_api_client = clients.VCenterAPIClient(vcenter_cfg)
        vnc_api_client = clients.VNCAPIClient(vnc_cfg)
        vrouter_api_client = clients.VRouterAPIClient()
        self.clients = {
            "esxi_api_client": esxi_api_client,
            "vcenter_api_client": vcenter_api_client,
            "vnc_api_client": vnc_api_client,
            "vrouter_api_client": vrouter_api_client,
        }
