import mock

from cvm.__main__ import server_main
from cvm import exceptions


@mock.patch("cvm.__main__.logger")
@mock.patch("cvm.__main__.sys")
@mock.patch("cvm.__main__.argparse.ArgumentParser")
@mock.patch("cvm.__main__.main")
def test_restarts_after_cvm_error(main_mock, _, sys_mock, log_mock):
    main_mock.side_effect = exceptions.CVMError()

    server_main()

    log_mock.error.assert_called_with("Restarting...")
    sys_mock.exit.assert_called_once_with(1)
