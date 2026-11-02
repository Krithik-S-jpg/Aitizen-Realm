import pytest
from tools.observer_connector import destination, read_config


def test_default_destination_and_hidden_token(monkeypatch, capsys):
    for key in ("OBSERVATORY_SITE_URL", "OBSERVATORY_PROVIDER", "OBSERVATORY_INGEST_TOKEN", "OBSERVATORY_SERVICE_TOKEN"):
        monkeypatch.delenv(key, raising=False)
    token = "private-token-" * 4
    monkeypatch.setattr("tools.observer_connector.getpass.getpass", lambda prompt: token)
    config = read_config()
    assert config["url"] == "https://aitizen-realm-observer.netlify.app"
    assert config["token"] == token
    assert token not in capsys.readouterr().out


def test_sites_still_uses_dispatch_header():
    site, headers = destination({"url": "https://example.chatgpt.site/", "token": "secret"})
    assert site == "https://example.chatgpt.site"
    assert headers == {"OAI-Sites-Authorization": "Bearer secret"}


def test_netlify_uses_separate_ingest_token():
    _, headers = destination({"url": "https://example.netlify.app", "token": "x" * 32})
    assert headers == {"Authorization": "Bearer " + "x" * 32}
    destination({"url": "https://monitor.example.com", "provider": "netlify", "token": "x" * 32})


@pytest.mark.parametrize("url", ["http://example.netlify.app", "https://user:pass@example.netlify.app", "https://example.netlify.app/api", "https://example.netlify.app#secret", "https://example.netlify.app?key=secret", "https://example.netlify.app:8080", "https://example.com"])
def test_connector_rejects_ambiguous_destinations(url):
    with pytest.raises(ValueError):
        destination({"url": url, "token": "x" * 32})
