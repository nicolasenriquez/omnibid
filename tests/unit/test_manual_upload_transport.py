from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from fastapi import HTTPException

from backend.api.manual_upload_transport import extract_manual_upload_multipart


class _FakeRequest:
    def __init__(self, *, content_type: str, body: bytes) -> None:
        self.headers = {"content-type": content_type}
        self._body = body

    async def body(self) -> bytes:
        return self._body


def _multipart_request(
    *,
    dataset_type: str,
    filename: str,
    payload: bytes,
    duplicate_file: bool = False,
) -> _FakeRequest:
    boundary = f"----manual-upload-{uuid4().hex}"
    parts: list[bytes] = [
        f"--{boundary}\r\n".encode("utf-8"),
        b'Content-Disposition: form-data; name="dataset_type"\r\n\r\n',
        dataset_type.encode("utf-8"),
        b"\r\n",
        f"--{boundary}\r\n".encode("utf-8"),
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode("utf-8"),
        b"Content-Type: text/csv\r\n\r\n",
        payload,
        b"\r\n",
    ]
    if duplicate_file:
        parts.extend(
            [
                f"--{boundary}\r\n".encode("utf-8"),
                b'Content-Disposition: form-data; name="file"; filename="extra.csv"\r\n',
                b"Content-Type: text/csv\r\n\r\n",
                payload,
                b"\r\n",
            ]
        )
    parts.append(f"--{boundary}--\r\n".encode("utf-8"))
    return _FakeRequest(
        content_type=f"multipart/form-data; boundary={boundary}",
        body=b"".join(parts),
    )


def _run_async(coro: object) -> object:
    return asyncio.run(coro)  # type: ignore[arg-type]


def test_extract_manual_upload_multipart_returns_single_dataset_and_file() -> None:
    request = _multipart_request(
        dataset_type="licitacion",
        filename="licitaciones.csv",
        payload=b"codigo;nombre\n1;test\n",
    )

    payload = _run_async(
        extract_manual_upload_multipart(
            request,  # type: ignore[arg-type]
            dataset_field_name="dataset_type",
        )
    )

    assert payload.dataset_type == "licitacion"
    assert payload.original_filename == "licitaciones.csv"
    assert payload.file_bytes.startswith(b"codigo;nombre")
    assert payload.file_content_type == "text/csv"


def test_extract_manual_upload_multipart_rejects_non_multipart_content_type() -> None:
    request = _FakeRequest(content_type="application/json", body=b"{}")

    with pytest.raises(HTTPException, match="multipart/form-data"):
        _run_async(
            extract_manual_upload_multipart(
                request,  # type: ignore[arg-type]
                dataset_field_name="dataset_type",
            )
        )


def test_extract_manual_upload_multipart_rejects_empty_body() -> None:
    request = _FakeRequest(content_type="multipart/form-data; boundary=x", body=b"")

    with pytest.raises(HTTPException, match="body is empty"):
        _run_async(
            extract_manual_upload_multipart(
                request,  # type: ignore[arg-type]
                dataset_field_name="dataset_type",
            )
        )


def test_extract_manual_upload_multipart_rejects_malformed_multipart() -> None:
    request = _FakeRequest(
        content_type="multipart/form-data; boundary=x",
        body=b"this is not a valid multipart message",
    )

    with pytest.raises(HTTPException, match="part is malformed"):
        _run_async(
            extract_manual_upload_multipart(
                request,  # type: ignore[arg-type]
                dataset_field_name="dataset_type",
            )
        )


def test_extract_manual_upload_multipart_requires_dataset_selection() -> None:
    request = _multipart_request(
        dataset_type="",
        filename="licitaciones.csv",
        payload=b"codigo;nombre\n1;test\n",
    )

    with pytest.raises(HTTPException, match="Select licitacion or orden_compra"):
        _run_async(
            extract_manual_upload_multipart(
                request,  # type: ignore[arg-type]
                dataset_field_name="dataset_type",
            )
        )


def test_extract_manual_upload_multipart_rejects_multiple_files() -> None:
    request = _multipart_request(
        dataset_type="licitacion",
        filename="licitaciones.csv",
        payload=b"codigo;nombre\n1;test\n",
        duplicate_file=True,
    )

    with pytest.raises(HTTPException, match="Exactly one CSV file"):
        _run_async(
            extract_manual_upload_multipart(
                request,  # type: ignore[arg-type]
                dataset_field_name="dataset_type",
            )
        )
