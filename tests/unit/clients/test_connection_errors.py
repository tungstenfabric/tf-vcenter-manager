import socket

import mock
import pytest
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
