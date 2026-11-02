import httpx
from app.infrastructure.api.v1.checkpoints import save_failure_detail


def failure(code, status=400):
    return httpx.HTTPStatusError("secret", request=httpx.Request("POST", "https://example.test"),
        response=httpx.Response(status, json={"code": code, "message": "private payload"}))


def test_save_failures_are_specific_and_do_not_expose_upstream_secrets():
    assert "missing" in save_failure_detail(failure("PGRST202", 404))
    assert "permissions" in save_failure_detail(failure("42501", 403))
    assert "23505" in save_failure_detail(failure("23505"))
    assert "statement timeout" in save_failure_detail(failure("57014"))
    assert "may have completed" in save_failure_detail(httpx.ReadTimeout("secret"))
    for error in [failure("23505"), failure("PGRST202"), httpx.ConnectError("secret")]:
        detail = save_failure_detail(error)
        assert "private" not in detail and "secret" not in detail
