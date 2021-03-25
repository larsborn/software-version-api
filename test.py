import os
import unittest

import requests

from version_rss_api import WordpressPlugin, SignalCliPlugin


class WordpressPluginTestCase(unittest.TestCase):
    def tearDown(self) -> None:
        self.OUT.session.close()

    def setUp(self) -> None:
        self.OUT = WordpressPlugin('TestUserAgent')

    def test_instantiate(self):
        self.assertTrue(self.OUT)

    def test_getVersion(self):
        version = self.OUT()
        self.assertTrue(version)
        self.assertTrue(isinstance(version, str))


class SignalCliTestCase(unittest.TestCase):
    def tearDown(self) -> None:
        self.OUT.session.close()

    def setUp(self) -> None:
        self.OUT = SignalCliPlugin('TestUserAgent')

    def test_instantiate(self):
        self.assertTrue(self.OUT)

    def test_getVersion(self):
        version = self.OUT()
        self.assertTrue(version)
        self.assertTrue(isinstance(version, str))


class ApiTestCase(unittest.TestCase):
    BASE_URL = os.environ.get('BASE_URL', 'http://127.0.0.1:5000')

    def setUp(self) -> None:
        self.session = requests.Session()

    def tearDown(self) -> None:
        self.session.close()

    def test_all(self):
        response = self.session.get(F'{self.BASE_URL}/v1/most_recent')
        response.raise_for_status()
        self.assertTrue('signal-cli' in response.json().keys())
        self.assertTrue('wordpress' in response.json().keys())


if __name__ == '__main__':
    unittest.main()
