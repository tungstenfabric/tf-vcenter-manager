import mock
import pytest

from cvm import controllers, exceptions, services


class DummyChangeHandler(controllers.AbstractChangeHandler):

    PROPERTY_NAME = "dummy_name"

    def _handle_change(self, obj, value):
        self._vm_service.raise_cvm_error()

    def _log_managed_object_not_found(self, value):
        pass


class DummyEventHandler(controllers.AbstractEventHandler):

    EVENTS = (mock.Mock,)

    def _handle_event(self, event):
        self._vm_service.raise_cvm_error()


class DummyVMService(services.Service):
    def raise_cvm_error(self):
        raise exceptions.CVMError("Bad things happened")


@pytest.fixture
def vm_service():
    return DummyVMService(
        mock.Mock(),
        mock.Mock(),
        mock.Mock(),
        mock.Mock(),
        mock.Mock(),
        mock.Mock(),
    )


@pytest.fixture
def change_handler(vm_service):
    return DummyChangeHandler(
        vm_service, mock.Mock(), mock.Mock(), mock.Mock(), mock.Mock()
    )


@pytest.fixture
def event_handler(vm_service):
    return DummyEventHandler(
        vm_service, mock.Mock(), mock.Mock(), mock.Mock(), mock.Mock()
    )


def test_change_handlers_reraise_cvm_error(change_handler):
    property_change = mock.Mock(val=mock.Mock())
    property_change.configure_mock(name="dummy_name")

    with pytest.raises(exceptions.CVMError):
        change_handler.handle_change(mock.Mock(), property_change)


def test_event_handlers_reraise_cvm_error(event_handler):
    property_change = mock.Mock(val=mock.Mock())
    property_change.configure_mock(name="latestPage")

    with pytest.raises(exceptions.CVMError):
        event_handler.handle_change(mock.Mock(), property_change)
