"""Extended unit tests for platform.errors — error classes and handlers.

Complements test_problem_details.py with coverage for all error subclasses,
the http_exception_handler, and ProblemDetail serialization.
"""

import json

from fastapi import HTTPException
from starlette.requests import Request

from veupath_chatbot.platform.errors import (
    AppError,
    ErrorCode,
    ForbiddenError,
    InternalError,
    NotFoundError,
    ProblemDetail,
    UnauthorizedError,
    ValidationError,
    WDKError,
    app_error_handler,
    http_exception_handler,
)


def _make_request(path: str = "/test") -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": path,
            "raw_path": path.encode(),
            "headers": [],
            "query_string": b"",
            "server": ("testserver", 80),
            "scheme": "http",
            "client": ("127.0.0.1", 12345),
        }
    )


class TestErrorClasses:
    def test_app_error_defaults(self):
        err = AppError(code=ErrorCode.INTERNAL_ERROR, title="Boom")
        assert err.code == ErrorCode.INTERNAL_ERROR
        assert err.title == "Boom"
        assert err.status == 400
        assert err.detail is None
        assert err.errors is None
        assert str(err) == "Boom"

    def test_internal_error(self):
        err = InternalError(title="Server crashed", detail="stack trace")
        assert err.code == ErrorCode.INTERNAL_ERROR
        assert err.status == 500
        assert err.detail == "stack trace"

    def test_internal_error_defaults(self):
        err = InternalError()
        assert err.title == "Internal error"
        assert err.status == 500

    def test_not_found_error(self):
        err = NotFoundError(detail="Gene not found")
        assert err.code == ErrorCode.NOT_FOUND
        assert err.status == 404
        assert err.detail == "Gene not found"

    def test_not_found_error_custom_code(self):
        err = NotFoundError(
            code=ErrorCode.STRATEGY_NOT_FOUND, detail="Strategy 123 missing"
        )
        assert err.code == ErrorCode.STRATEGY_NOT_FOUND
        assert err.status == 404

    def test_unauthorized_error(self):
        err = UnauthorizedError(detail="Token expired")
        assert err.code == ErrorCode.UNAUTHORIZED
        assert err.status == 401

    def test_forbidden_error(self):
        err = ForbiddenError(detail="Not your strategy")
        assert err.code == ErrorCode.FORBIDDEN
        assert err.status == 403

    def test_validation_error(self):
        errors = [{"loc": ["field"], "msg": "required"}]
        err = ValidationError(title="Bad input", detail="Check fields", errors=errors)
        assert err.code == ErrorCode.VALIDATION_ERROR
        assert err.status == 422
        assert err.errors == errors

    def test_wdk_error(self):
        err = WDKError(detail="WDK timeout", status=504)
        assert err.code == ErrorCode.WDK_ERROR
        assert err.status == 504
        assert err.title == "VEuPathDB service error"

    def test_wdk_error_default_status(self):
        err = WDKError(detail="Upstream failure")
        assert err.status == 502


class TestProblemDetail:
    def test_serialization_excludes_none(self):
        problem = ProblemDetail(
            title="Not Found",
            status=404,
            code=ErrorCode.NOT_FOUND,
        )
        data = problem.model_dump(exclude_none=True)
        assert "detail" not in data
        assert "instance" not in data
        assert "errors" not in data
        assert data["title"] == "Not Found"
        assert data["status"] == 404
        assert data["code"] == "NOT_FOUND"

    def test_serialization_includes_all_fields(self):
        problem = ProblemDetail(
            type="https://example.com/errors/NOT_FOUND",
            title="Not Found",
            status=404,
            detail="Resource with id=123 not found",
            instance="/strategies/123",
            code=ErrorCode.NOT_FOUND,
            errors=[{"loc": ["id"], "msg": "invalid"}],
        )
        data = problem.model_dump()
        assert data["type"] == "https://example.com/errors/NOT_FOUND"
        assert data["detail"] == "Resource with id=123 not found"
        assert data["instance"] == "/strategies/123"
        assert len(data["errors"]) == 1


class TestAppErrorHandler:
    async def test_not_found_response(self):
        req = _make_request("/strategies/123")
        err = NotFoundError(
            code=ErrorCode.STRATEGY_NOT_FOUND, detail="Strategy 123 not found"
        )
        resp = await app_error_handler(req, err)
        assert resp.status_code == 404
        assert resp.media_type == "application/problem+json"

        body = json.loads(resp.body.decode())
        assert body["code"] == "STRATEGY_NOT_FOUND"
        assert body["status"] == 404
        assert body["detail"] == "Strategy 123 not found"
        assert "instance" in body

    async def test_validation_error_includes_errors_array(self):
        req = _make_request()
        errors = [{"loc": ["text_expression"], "msg": "required"}]
        err = ValidationError(errors=errors)
        resp = await app_error_handler(req, err)
        assert resp.status_code == 422

        body = json.loads(resp.body.decode())
        assert body["code"] == "VALIDATION_ERROR"
        assert body["errors"] == errors


class TestHttpExceptionHandler:
    async def test_404_maps_to_not_found(self):
        req = _make_request("/missing")
        exc = HTTPException(status_code=404, detail="Not found")
        resp = await http_exception_handler(req, exc)
        assert resp.status_code == 404

        body = json.loads(resp.body.decode())
        assert body["code"] == "NOT_FOUND"
        assert body["title"] == "Not found"

    async def test_401_maps_to_unauthorized(self):
        req = _make_request()
        exc = HTTPException(status_code=401, detail="Unauthorized")
        resp = await http_exception_handler(req, exc)
        assert resp.status_code == 401

        body = json.loads(resp.body.decode())
        assert body["code"] == "UNAUTHORIZED"

    async def test_403_maps_to_forbidden(self):
        req = _make_request()
        exc = HTTPException(status_code=403, detail="Forbidden")
        resp = await http_exception_handler(req, exc)
        assert resp.status_code == 403

        body = json.loads(resp.body.decode())
        assert body["code"] == "FORBIDDEN"

    async def test_429_maps_to_rate_limited(self):
        req = _make_request()
        exc = HTTPException(status_code=429, detail="Too many requests")
        resp = await http_exception_handler(req, exc)
        assert resp.status_code == 429

        body = json.loads(resp.body.decode())
        assert body["code"] == "RATE_LIMITED"

    async def test_500_maps_to_internal_error(self):
        req = _make_request()
        exc = HTTPException(status_code=500, detail="Server error")
        resp = await http_exception_handler(req, exc)
        assert resp.status_code == 500

        body = json.loads(resp.body.decode())
        assert body["code"] == "INTERNAL_ERROR"

    async def test_unknown_status_maps_to_internal_error(self):
        req = _make_request()
        exc = HTTPException(status_code=418, detail="I'm a teapot")
        resp = await http_exception_handler(req, exc)
        assert resp.status_code == 418

        body = json.loads(resp.body.decode())
        assert body["code"] == "INTERNAL_ERROR"

    async def test_response_is_problem_json(self):
        req = _make_request()
        exc = HTTPException(status_code=404, detail="Gone")
        resp = await http_exception_handler(req, exc)
        assert resp.media_type == "application/problem+json"
