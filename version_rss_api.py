#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import abc
import re
from typing import Optional

import atoma
import requests
import packaging.version
import requests.adapters
from flask import Flask, jsonify

__service__ = 'RSS Version Checker'
__version__ = '0.1.0'


class FixedTimeoutAdapter(requests.adapters.HTTPAdapter):
    def send(self, *pargs, **kwargs):
        if kwargs['timeout'] is None:
            kwargs['timeout'] = 10
        return super(FixedTimeoutAdapter, self).send(*pargs, **kwargs)


class VersionPlugin(abc.ABC):
    def __init__(self, user_agent: str):
        self.session = requests.session()
        self.session.mount('https://', FixedTimeoutAdapter())
        self.session.mount('http://', FixedTimeoutAdapter())
        self.session.headers = {'User-Agent': user_agent}
        self.semver_regex = re.compile(r'\d{1,4}\.\d{1,4}\.\d{1,4}')

    def __call__(self) -> Optional[str]:
        raise NotImplementedError()

    @property
    def software_name(self):
        raise NotImplementedError()


class WordpressPlugin(VersionPlugin):
    @property
    def software_name(self):
        return 'wordpress'

    def __call__(self) -> Optional[str]:
        response = self.session.get('https://api.wordpress.org/core/stable-check/1.0/')
        response.raise_for_status()
        for version, status in response.json().items():
            if status == 'latest':
                return version


class GithubReleases(VersionPlugin, abc.ABC):
    VERSION_BLOCKLIST = ['beta', 'rc']

    def __call__(self) -> Optional[str]:
        response = self.session.get(F'https://github.com/{self.user}/{self.repo}/releases.atom')
        response.raise_for_status()
        feed = atoma.parse_atom_bytes(response.content)
        versions = []
        for entry in feed.entries:
            title = entry.title.value
            if any(block in title.lower() for block in self.VERSION_BLOCKLIST):
                continue
            version = self.version_from_title(title)
            if version:
                versions.append(packaging.version.parse(version))

        return str(max(versions)) if len(versions) > 0 else None

    @property
    def user(self) -> str:
        raise NotImplementedError

    @property
    def repo(self) -> str:
        raise NotImplementedError

    def version_from_title(self, title: str) -> str:
        raise NotImplementedError


class GithubReleasesWithVPrefixAndSemVer(GithubReleases, abc.ABC):
    def version_from_title(self, title: str) -> Optional[str]:
        title = title.strip('v')
        if self.semver_regex.match(title):
            return title


class SignalCliPlugin(GithubReleases):
    @property
    def software_name(self):
        return 'signal-cli'

    @property
    def user(self) -> str:
        return 'AsamK'

    @property
    def repo(self) -> str:
        return 'signal-cli'

    def version_from_title(self, title: str) -> Optional[str]:
        if title.startswith('Version '):
            return title[8:]


class NextCloudPlugin(GithubReleasesWithVPrefixAndSemVer):
    @property
    def software_name(self):
        return 'nextcloud'

    @property
    def user(self) -> str:
        return 'nextcloud'

    @property
    def repo(self) -> str:
        return 'server'


class RoundcubePlugin(GithubReleases):
    @property
    def software_name(self):
        return 'roundcube'

    @property
    def user(self) -> str:
        return 'roundcube'

    @property
    def repo(self) -> str:
        return 'roundcubemail'

    def version_from_title(self, title: str) -> Optional[str]:
        if title.startswith('Roundcube Webmail '):
            return title[18:]


class RainloopPlugin(GithubReleasesWithVPrefixAndSemVer):
    @property
    def software_name(self):
        return 'rainloop'

    @property
    def user(self) -> str:
        return 'RainLoop'

    @property
    def repo(self) -> str:
        return 'rainloop-webmail'


class DolibarrPlugin(GithubReleases):
    @property
    def software_name(self):
        return 'dolibarr'

    @property
    def user(self) -> str:
        return 'Dolibarr'

    @property
    def repo(self) -> str:
        return 'dolibarr'

    def version_from_title(self, title: str) -> Optional[str]:
        return title


class HumhubPlugin(GithubReleases):
    @property
    def software_name(self):
        return 'humhub'

    @property
    def user(self) -> str:
        return 'humhub'

    @property
    def repo(self) -> str:
        return 'humhub'

    def version_from_title(self, title: str) -> Optional[str]:
        return title


class FroxlorPlugin(GithubReleases):
    @property
    def software_name(self):
        return 'froxlor'

    @property
    def user(self) -> str:
        return 'Froxlor'

    @property
    def repo(self) -> str:
        return 'Froxlor'

    def version_from_title(self, title: str) -> Optional[str]:
        if title.startswith('Froxlor '):
            return title.split(' ')[1]


class CyberchefPlugin(GithubReleasesWithVPrefixAndSemVer):
    @property
    def software_name(self):
        return 'cyberchef'

    @property
    def user(self) -> str:
        return 'gchq'

    @property
    def repo(self) -> str:
        return 'CyberChef'


class ArangoDBPlugin(GithubReleasesWithVPrefixAndSemVer):
    @property
    def software_name(self):
        return 'arangodb'

    @property
    def user(self) -> str:
        return 'arangodb'

    @property
    def repo(self) -> str:
        return 'ArangoDB'


app = Flask(__name__)
USER_AGENT = F'{__service__}/{__version__}'


@app.route('/v1/most_recent', methods=['GET'])
def most_recent():
    plugins = [cls(USER_AGENT) for cls in [
        WordpressPlugin,
        SignalCliPlugin,
        NextCloudPlugin,
        RoundcubePlugin,
        DolibarrPlugin,
        HumhubPlugin,
        FroxlorPlugin,
        RainloopPlugin,
        CyberchefPlugin,
        ArangoDBPlugin,
    ]]
    return jsonify(dict((pluign.software_name, pluign()) for pluign in plugins))
