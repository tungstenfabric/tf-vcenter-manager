import socket

import mock
import pytest
from vnc_api import vnc_api

from cvm import clients, exceptions


@pytest.fixture
def service_instance():
    si = mock.Mock()
    datacenter = mock.Mock()
    host = mock.Mock(host=[mock.Mock()])
    datacenter.hostFolder.childEntity = [host]
    si.content.rootFolder.childEntity = [datacenter]
    return si


@pytest.fixture
def esxi_api_client(service_instance):
    with mock.patch("cvm.clients.SmartConnectNoSSL") as si:
        si.return_value = service_instance
        return clients.ESXiAPIClient({})


@pytest.fixture
def vcenter_api_client():
    with mock.patch("cvm.clients.SmartConnectNoSSL"):
        return clients.VCenterAPIClient({})


@pytest.fixture
def vnc_api_client():
    with mock.patch("cvm.clients.vnc_api.VncApi"):
        return clients.VNCAPIClient({
            "api_server_host": "",
            "auth_host": "",
        })


def test_esxi_connection_lost(service_instance, esxi_api_client):
    service_instance.content.propertyCollector.WaitForUpdatesEx.side_effect = (
        socket.error
    )

    with pytest.raises(exceptions.APIClientConnectionLostError):
        esxi_api_client.wait_for_updates()


def test_vcenter_connection_lost(service_instance, vcenter_api_client):
    service_instance.content.viewManager.CreateContainerView.side_effect = (
        socket.error
    )

    with mock.patch("cvm.clients.SmartConnectNoSSL") as si:
        si.return_value = service_instance
        with pytest.raises(exceptions.APIClientConnectionLostError):
            with vcenter_api_client:
                pass


def test_vnc_connections_lost(vnc_api_client):
    with mock.patch.object(vnc_api_client, "vnc_lib") as vnc_lib:
        vnc_lib.virtual_machines_list.side_effect = vnc_api.ConnectionError
        with pytest.raises(exceptions.APIClientConnectionLostError):
            vnc_api_client.get_all_vms()
