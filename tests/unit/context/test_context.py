import collections
import socket

import mock
import pytest

from cvm.context import CVMContext


@pytest.fixture
def context(config):
    return CVMContext(config)


@pytest.fixture
def config():
    return {
        "esxi": {},
        "vcenter": {},
        "vnc": {},
        "sandesh": {
            "collectors": "10.10.10.10:8086",
            "logging_level": "SYS_INFO",
            "log_file": "cvm.log",
            "http_server_ip": "10.10.10.10",
        },
    }


@pytest.fixture
def patched_libs(clients_lib, services_lib, controllers_lib):
    return {
        "clients_lib": clients_lib,
        "services_lib": services_lib,
        "controllers_lib": controllers_lib,
    }


@pytest.fixture
def clients():
    return {
        "vcenter_api_client": mock.Mock(),
        "esxi_api_client": mock.Mock(),
        "vnc_api_client": mock.Mock(),
        "vrouter_api_client": mock.Mock(),
    }


@pytest.fixture
def clients_lib(clients):
    with mock.patch("cvm.context.clients") as c_mock:
        c_mock.VCenterAPIClient.return_value = clients["vcenter_api_client"]
        c_mock.ESXiAPIClient.return_value = clients["esxi_api_client"]
        c_mock.VNCAPIClient.return_value = clients["vnc_api_client"]
        c_mock.VRouterAPIClient.return_value = clients["vrouter_api_client"]
        yield c_mock


@pytest.fixture
def services():
    return {
        "vm_service": mock.Mock(),
        "vmi_service": mock.Mock(),
        "vn_service": mock.Mock(),
        "vrouter_port_service": mock.Mock(),
        "vlan_id_service": mock.Mock(),
    }


@pytest.fixture
def services_lib(services):
    with mock.patch("cvm.context.services") as s_mock:
        s_mock.VirtualMachineService.return_value = services["vm_service"]
        s_mock.VirtualMachineInterfaceService.return_value = services[
            "vmi_service"
        ]
        s_mock.VirtualNetworkService.return_value = services["vn_service"]
        s_mock.VRouterPortService.return_value = services[
            "vrouter_port_service"
        ]
        s_mock.VlanIdService.return_value = services["vlan_id_service"]
        yield s_mock


@pytest.fixture
def handlers():
    return collections.OrderedDict(
        [
            ("vm_updated_handler", mock.Mock()),
            ("vm_renamed_handler", mock.Mock()),
            ("vm_reconfigured_handler", mock.Mock()),
            ("vm_removed_handler", mock.Mock()),
            ("vm_registered_handler", mock.Mock()),
            ("guest_net_handler", mock.Mock()),
            ("vmware_tools_status_handler", mock.Mock()),
            ("power_state_handler", mock.Mock()),
        ]
    )


@pytest.fixture
def update_handler():
    return mock.Mock()


@pytest.fixture
def controller():
    return mock.Mock()


@pytest.fixture
def controllers_lib(handlers, update_handler, controller):
    with mock.patch("cvm.context.controllers") as c_mock:
        c_mock.VmUpdatedHandler.return_value = handlers["vm_updated_handler"]
        c_mock.VmRenamedHandler.return_value = handlers["vm_renamed_handler"]
        c_mock.VmReconfiguredHandler.return_value = handlers[
            "vm_reconfigured_handler"
        ]
        c_mock.VmRemovedHandler.return_value = handlers["vm_removed_handler"]
        c_mock.VmRegisteredHandler.return_value = handlers[
            "vm_registered_handler"
        ]
        c_mock.GuestNetHandler.return_value = handlers["guest_net_handler"]
        c_mock.VmwareToolsStatusHandler.return_value = handlers[
            "vmware_tools_status_handler"
        ]
        c_mock.PowerStateHandler.return_value = handlers["power_state_handler"]
        c_mock.UpdateHandler.return_value = update_handler
        c_mock.VMwareController.return_value = controller
        yield c_mock


@pytest.fixture
def sandesh():
    return mock.Mock()
@pytest.fixture
def sandesh_config():
    return mock.Mock()

@pytest.fixture
def sandesh_base(sandesh, sandesh_config):
    with mock.patch("cvm.context.sandesh_base") as snd_base:
        snd_base.Sandesh.return_value = sandesh
        snd_base.SandeshConfig.return_value = sandesh_config
        yield snd_base


@pytest.fixture
def sandesh_handler():
    handler = mock.Mock()
    with mock.patch("cvm.context.sandesh_handler") as sh_mock:
        sh_mock.SandeshHandler.return_value = handler
        yield handler


@pytest.fixture
def connection_state():
    conn_state = mock.Mock()
    with mock.patch("cvm.context.connection_info") as conn_info:
        conn_info.ConnectionState = conn_state
        yield conn_state


def test_build_context_clients(context, config, clients, patched_libs):
    context.build()

    clients_lib = patched_libs["clients_lib"]
    clients_lib.VCenterAPIClient.assert_called_once_with(config["vcenter"])
    clients_lib.ESXiAPIClient.assert_called_once_with(config["esxi"])
    clients_lib.VNCAPIClient.assert_called_once_with(config["vnc"])
    clients_lib.VRouterAPIClient.assert_called_once()

    assert context.clients == {
        "vcenter_api_client": clients["vcenter_api_client"],
        "esxi_api_client": clients["esxi_api_client"],
        "vnc_api_client": clients["vnc_api_client"],
        "vrouter_api_client": clients["vrouter_api_client"],
    }


def test_build_context_services(context, services, patched_libs):
    context.build()

    s_lib = patched_libs["services_lib"]
    s_kwargs = {
        "database": context.database,
        "vnc_api_client": context.clients["vnc_api_client"],
        "esxi_api_client": context.clients["esxi_api_client"],
        "vcenter_api_client": context.clients["vcenter_api_client"],
        "vrouter_api_client": context.clients["vrouter_api_client"],
        "vlan_id_pool": context.vlan_id_pool,
    }

    s_lib.VirtualMachineService.assert_called_once_with(**s_kwargs)
    s_lib.VirtualMachineInterfaceService.assert_called_once_with(**s_kwargs)
    s_lib.VirtualNetworkService.assert_called_once_with(**s_kwargs)
    s_lib.VRouterPortService.assert_called_once_with(**s_kwargs)
    s_lib.VlanIdService.assert_called_once_with(**s_kwargs)

    assert context.services == services


def test_context_handlers(context, handlers, services, patched_libs):
    context.build()

    c_lib = patched_libs["controllers_lib"]
    c_lib.VmUpdatedHandler.assert_called_once_with(**services)
    c_lib.VmRenamedHandler.assert_called_once_with(**services)
    c_lib.VmReconfiguredHandler.assert_called_once_with(**services)
    c_lib.VmRemovedHandler.assert_called_once_with(**services)
    c_lib.VmRegisteredHandler.assert_called_once_with(**services)
    c_lib.GuestNetHandler.assert_called_once_with(**services)
    c_lib.VmwareToolsStatusHandler.assert_called_once_with(**services)
    c_lib.PowerStateHandler.assert_called_once_with(**services)

    c_lib.UpdateHandler.assert_called_once_with(list(handlers.values()))


def test_context_vmware_controller(context, services, patched_libs):
    context.build()

    c_lib = patched_libs["controllers_lib"]
    c_lib.VmwareController.assert_called_once_with(
        update_handler=context.update_handler, lock=context.lock, **services
    )


def test_introspect_config(context, patched_libs):
    context.load_introspect_config()
    introspect_config = context.config["introspect_config"]

    assert introspect_config == {
        "id": 35,
        "hostname": socket.gethostname(),
        "table": "ObjectContrailvCenterManagerNode",
        "instance_id": "0",
        "introspect_port": 9090,
        "name": "contrail-vcenter-manager",
        "node_type": 6,
        "node_type_name": "Compute",
        "collectors": ["10.10.10.10:8086"],
        "logging_level": "SYS_INFO",
        "log_file": "cvm.log",
    }


def test_run_sandesh(
    context,
    sandesh,
    sandesh_config,
    sandesh_base,
    sandesh_handler,
    connection_state,
    patched_libs,
    config,
):
    context.load_introspect_config()

    context.run_sandesh()

    sandesh_handler.bind_handlers.assert_called_once()

    introspect_config = config["introspect_config"]
    sandesh.init_generator.assert_called_once_with(
        **{
            "module": "cvm",
            "source": introspect_config["hostname"],
            "node_type": introspect_config["node_type_name"],
            "instance_id": introspect_config["instance_id"],
            "collectors": introspect_config["collectors"],
            "client_context": "cvm_context",
            "http_port": introspect_config["introspect_port"],
            "sandesh_req_uve_pkg_list": ["cfgm_common", "cvm"],
            "config": sandesh_config,
        }
    )

    sandesh_base.SandeshConfig.assert_called_once_with(
        http_server_ip=config["sandesh"]["http_server_ip"]
    )

    connection_state.init.assert_called_once_with(
        sandesh=sandesh,
        hostname=introspect_config["hostname"],
        module_id=introspect_config["name"],
        instance_id=introspect_config["instance_id"],
        conn_status_cb=mock.ANY,
        uve_type_cls=mock.ANY,
        uve_data_type_cls=mock.ANY,
        table=introspect_config["table"],
    )
