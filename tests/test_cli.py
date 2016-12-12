import json
from click.testing import CliRunner
from unittest.mock import MagicMock
from zign.cli_zign import cli_zign


def test_create_list_delete(monkeypatch):
    token = 'abc-123'

    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {'access_token': token}

    monkeypatch.setattr('keyring.set_password', MagicMock())
    monkeypatch.setattr('requests.get', MagicMock(return_value=response))
    monkeypatch.setattr('stups_cli.config.store_config', MagicMock())

    runner = CliRunner()

    with runner.isolated_filesystem():
        result = runner.invoke(cli_zign, ['token', '-n', 'mytok', '--password', 'mypass'], catch_exceptions=False,
                               input='localhost\n')

        assert token == result.output.rstrip().split('\n')[-1]

        result = runner.invoke(cli_zign, ['list', '-o', 'json'], catch_exceptions=False)
        data = json.loads(result.output)
        assert len(data) >= 1
        assert 'mytok' in [r['name'] for r in data]

        result = runner.invoke(cli_zign, ['delete', 'mytok'], catch_exceptions=False)
        result = runner.invoke(cli_zign, ['list', '-o', 'json'], catch_exceptions=False)
        data = json.loads(result.output)
        assert 'mytok' not in [r['name'] for r in data]

        # should work again for already deleted tokens
        result = runner.invoke(cli_zign, ['delete', 'mytok'], catch_exceptions=False)


def test_empty_config(monkeypatch):
    token = 'abc-123'

    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {'access_token': token}

    monkeypatch.setattr('keyring.set_password', MagicMock())
    monkeypatch.setattr('stups_cli.config.load_config', lambda x: {})
    monkeypatch.setattr('stups_cli.config.store_config', lambda x, y: None)
    monkeypatch.setattr('requests.get', MagicMock(return_value=response))

    runner = CliRunner()

    with runner.isolated_filesystem():
        result = runner.invoke(cli_zign, ['token', '-n', 'mytok', '--password', 'mypass'], catch_exceptions=False,
                               input='localhost\n')
        assert token == result.output.rstrip().split('\n')[-1]


def test_auth_failure(monkeypatch):
    token = 'abc-123'

    def get(url, auth, **kwargs):
        response = MagicMock()
        if auth[1] == 'correctpass':
            response.status_code = 200
            response.json.return_value = {'access_token': token}
        else:
            response.status_code = 401
        return response

    monkeypatch.setattr('keyring.set_password', MagicMock())
    monkeypatch.setattr('stups_cli.config.load_config', lambda x: {'url': 'http://localhost'})
    monkeypatch.setattr('stups_cli.config.store_config', lambda x, y: None)
    monkeypatch.setattr('requests.get', get)

    runner = CliRunner()

    with runner.isolated_filesystem():
        result = runner.invoke(cli_zign, ['token', '-n', 'mytok', '-U', 'myusr', '--password', 'mypass'],
                               catch_exceptions=False, input='wrongpw\ncorrectpass\n')
        assert 'Authentication failed: Token Service returned ' in result.output
        assert 'Please check your username and password and try again.' in result.output
        assert 'Password for myusr: ' in result.output
        assert token == result.output.rstrip().split('\n')[-1]


def test_server_error(monkeypatch):
    def get(url, **kwargs):
        response = MagicMock()
        response.status_code = 503
        return response

    monkeypatch.setattr('keyring.set_password', MagicMock())
    monkeypatch.setattr('stups_cli.config.load_config', lambda x: {'url': 'http://localhost'})
    monkeypatch.setattr('stups_cli.config.store_config', lambda x, y: None)
    monkeypatch.setattr('requests.get', get)

    runner = CliRunner()

    with runner.isolated_filesystem():
        result = runner.invoke(cli_zign, ['token', '-n', 'mytok', '-U', 'myusr', '--password', 'mypass'],
                               catch_exceptions=False)
        assert 'Server error: Token Service returned HTTP status 503' in result.output


def test_user_config(monkeypatch):
    token = 'abc-123'

    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {'access_token': token}

    def get_token(url, auth, **kwargs):
        assert url == 'https://localhost/access_token'
        user, passwd = auth
        assert user == 'jdoe'
        return response

    monkeypatch.setattr('keyring.set_password', MagicMock())
    monkeypatch.setattr('stups_cli.config.load_config',
                        lambda x: {'user': 'jdoe', 'url': 'https://localhost/access_token'})
    monkeypatch.setattr('stups_cli.config.store_config', lambda x, y: None)
    monkeypatch.setattr('requests.get', get_token)

    runner = CliRunner()

    with runner.isolated_filesystem():
        result = runner.invoke(cli_zign, ['token', '-n', 'mytok', '--password', 'mypass'], catch_exceptions=False)
        assert token == result.output.rstrip().split('\n')[-1]
