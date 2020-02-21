#!/usr/bin/env python

import argparse
import logging
import sys
import yaml
import gevent

from cvm import exceptions
from cvm.context import CVMContext

gevent.monkey.patch_all()

logger = logging.getLogger("cvm")


def load_config(config_file):
    with open(config_file, "r") as ymlfile:
        return yaml.load(ymlfile)


def main(args):
    cfg = load_config(args.config_file)
    context = CVMContext(cfg)
    context.load_introspect_config()
    context.configure_logger()
    context.build()
    context.run_sandesh()
    greenlets = [
        gevent.spawn(context.supervisor.supervise),
        gevent.spawn(context.vmware_monitor.monitor),
    ]
    gevent.joinall(greenlets, raise_error=True)


def server_main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c",
        action="store",
        dest="config_file",
        default="/etc/contrail/contrail-vcenter-manager/config.yaml",
    )
    parsed_args = parser.parse_args()
    try:
        main(parsed_args)
        sys.exit(0)
    except exceptions.CVMError as exc:
        logger.exception(exc)
        logger.error("Restarting...")
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception:
        logger.critical("", exc_info=True)
        raise


if __name__ == "__main__":
    server_main()
