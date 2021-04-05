#!/usr/bin/env python3
"""
Script to integrate the API shipped with this repository with Zabbix. See the following blag for details:

https://blag.nullteilerfrei.de/2021/03/25/zabbix-use-low-level-discovery-for-software-update-notifications/
"""
import json
import os
import subprocess
import logging
import re
from typing import List

import requests


class ZabbixSenderException(Exception):
    pass


class ZabbixSender(object):
    def __init__(self, logger: logging.Logger, sender_path: str, config_path: str):
        self.logger = logger
        self.sender_path = sender_path
        self.config_path = config_path

        self.r_processed = re.compile(r'processed: (\d+);')
        self.r_failed = re.compile(r'failed: (\d+);')
        self.r_total = re.compile(r'total: (\d+);')
        self.last_command = None

    def _execute_sender(self, arguments: List[str], verbose: bool = False) -> str:
        self.last_command = [self.sender_path]
        if verbose:
            self.last_command.append('-vv')
        self.last_command += ['-c', self.config_path]
        self.last_command += arguments
        self.logger.debug(F'Executing: {" ".join(self.last_command)}')
        p = subprocess.Popen(
            self.last_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        output, error = p.communicate()
        if p.returncode:
            self.logger.debug('StdErr Output:')
            for line in error.decode('utf-8').strip().split('\n'):
                self.logger.debug(line)
            self.logger.debug('StdOut Output:')
            for line in output.decode('utf-8').strip().split('\n'):
                self.logger.debug(line)

            raise ZabbixSenderException(F'Returncode {p.returncode}')
        if not verbose and error:
            raise ZabbixSenderException(error)

        return output.decode('utf-8')

    def _parse_output(self, output: str):
        processed_item_count = int(self.r_processed.search(output).group(1))
        failed_item_count = int(self.r_failed.search(output).group(1))
        total_item_count = int(self.r_total.search(output).group(1))

        if failed_item_count:
            raise ZabbixSenderException('%i failed Items during %s' % (failed_item_count, self.last_command))
        if processed_item_count != total_item_count:
            raise ZabbixSenderException('Mismatching: %i != %i' % (processed_item_count, total_item_count))

    def send_item(self, name, value):
        self._parse_output(self._execute_sender(['-k', name, '-o', '%s' % value]))

        return '%s: %s' % (name, value)


def main():
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger()
    logger.info('Zabbix Sender started.')
    sender = ZabbixSender(logger, '/usr/bin/zabbix_sender', '/etc/zabbix/zabbix_agentd.conf')
    response = requests.get(os.environ.get('API_URL'))

    response.raise_for_status()
    response_data = response.json()
    discovery = []
    for software_name in sorted(response_data.keys()):
        discovery.append({'{#SOFTWARENAME}': software_name})
    print(sender.send_item('software_versions.discovery', json.dumps({'data': discovery})))
    logger.info(F'Discovered {len(discovery)} software names.')

    for software_name, current_version in response_data.items():
        try:
            print(sender.send_item(F'software_versions.most_recent_version[{software_name}]', current_version))
        except ZabbixSenderException as e:
            logger.exception(e)
            logger.error('Cannot send item, maybe a new software was discovered, just re-run the script in a minute.')


if __name__ == '__main__':
    main()
