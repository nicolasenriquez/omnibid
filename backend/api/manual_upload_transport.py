from __future__ import annotations

from dataclasses import dataclass
from email.parser import BytesParser
from email.policy import default as email_default_policy
from typing import Any, cast

from fastapi import HTTPException, Request


@dataclass(frozen=True)
class ManualUploadMultipartPayload:
    dataset_type: str
    original_filename: str
    file_bytes: bytes
    file_content_type: str | None


async def extract_manual_upload_multipart(
    request: Request,
    *,
    dataset_field_name: str,
) -> ManualUploadMultipartPayload:
    content_type = request.headers.get("content-type") or ""
    if "multipart/form-data" not in content_type.lower():
        raise HTTPException(
            status_code=400,
            detail="Manual CSV upload must use multipart/form-data",
        )

    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="Manual CSV upload body is empty")

    dataset_values: list[str] = []
    file_items: list[tuple[str, str, bytes, str | None]] = []
    message = cast(
        Any,
        BytesParser(policy=email_default_policy).parsebytes(
            f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("utf-8") + body
        ),
    )
    if not message.is_multipart():
        raise HTTPException(status_code=400, detail="Manual CSV upload part is malformed")

    for part in message.iter_parts():
        if part.get_content_disposition() != "form-data":
            continue

        field_name = part.get_param("name", header="content-disposition") or ""
        file_name = part.get_filename()
        payload = part.get_payload(decode=True)
        payload_bytes = payload if isinstance(payload, bytes) else b""
        if file_name:
            file_items.append(
                (
                    field_name,
                    file_name,
                    payload_bytes,
                    part.get_content_type() if part.get_content_type() else None,
                )
            )
            continue

        if field_name == dataset_field_name:
            charset = part.get_content_charset() or "utf-8"
            dataset_values.append(payload_bytes.decode(charset).strip())

    if len(dataset_values) != 1 or not dataset_values[0]:
        raise HTTPException(
            status_code=400,
            detail="Select licitacion or orden_compra before uploading",
        )
    if len(file_items) != 1:
        raise HTTPException(
            status_code=400,
            detail="Exactly one CSV file must be uploaded",
        )

    _, original_filename, file_bytes, file_content_type = file_items[0]
    return ManualUploadMultipartPayload(
        dataset_type=dataset_values[0],
        original_filename=original_filename,
        file_bytes=bytes(file_bytes),
        file_content_type=file_content_type,
    )
