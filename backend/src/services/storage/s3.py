"""S3-compatible storage backend (boto3).

Works against any S3-compatible endpoint: Oracle Object Storage
(``https://<namespace>.compat.objectstorage.<region>.oraclecloud.com``),
AWS S3, MinIO, Cloudflare R2, ... Only the endpoint/credentials settings
change when switching provider.
"""

from __future__ import annotations

from src.services.storage.base import StorageError, StorageKeyNotFoundError

_NOT_FOUND_CODES = {"NoSuchKey", "404", "NotFound"}


class S3StorageBackend:
    """Object storage over the S3 API on a configurable endpoint."""

    def __init__(
        self,
        *,
        endpoint_url: str | None,
        region: str | None,
        bucket: str | None,
        access_key_id: str | None,
        secret_access_key: str | None,
    ) -> None:
        if not bucket:
            msg = "S3_BUCKET must be set when STORAGE_BACKEND is 's3'."
            raise ValueError(msg)
        # boto3 stays a lazy import so the local backend never requires it configured.
        import boto3  # noqa: PLC0415
        from botocore.config import Config  # noqa: PLC0415
        from botocore.exceptions import BotoCoreError, ClientError  # noqa: PLC0415

        self._client_error: type[Exception] = ClientError
        self._botocore_error: type[Exception] = BotoCoreError
        self._bucket = bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            region_name=region,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            # boto3 >= 1.36 defaults to streaming checksums ("aws-chunked"
            # encoding), which S3-compatible providers like Oracle Object
            # Storage reject with NotImplemented. Only checksum when the
            # operation requires it.
            config=Config(
                request_checksum_calculation="when_required",
                response_checksum_validation="when_required",
            ),
        )

    def _error_code(self, err: Exception) -> str:
        response = getattr(err, "response", None) or {}
        return str(response.get("Error", {}).get("Code", ""))

    def put(self, key: str, data: bytes, *, content_type: str | None = None) -> None:
        extra = {"ContentType": content_type} if content_type else {}
        try:
            self._client.put_object(Bucket=self._bucket, Key=key, Body=data, **extra)
        except (self._client_error, self._botocore_error) as err:
            msg = f"Failed to store object {key!r}: {err}"
            raise StorageError(msg) from err

    def get(self, key: str) -> bytes:
        try:
            response = self._client.get_object(Bucket=self._bucket, Key=key)
            return response["Body"].read()
        except self._client_error as err:
            if self._error_code(err) in _NOT_FOUND_CODES:
                msg = f"No object stored at key {key!r}"
                raise StorageKeyNotFoundError(msg) from err
            msg = f"Failed to read object {key!r}: {err}"
            raise StorageError(msg) from err
        except self._botocore_error as err:
            msg = f"Failed to read object {key!r}: {err}"
            raise StorageError(msg) from err

    def exists(self, key: str) -> bool:
        try:
            self._client.head_object(Bucket=self._bucket, Key=key)
        except self._client_error as err:
            if self._error_code(err) in _NOT_FOUND_CODES:
                return False
            msg = f"Failed to check object {key!r}: {err}"
            raise StorageError(msg) from err
        except self._botocore_error as err:
            msg = f"Failed to check object {key!r}: {err}"
            raise StorageError(msg) from err
        else:
            return True

    def delete(self, key: str) -> None:
        try:
            self._client.delete_object(Bucket=self._bucket, Key=key)
        except (self._client_error, self._botocore_error) as err:
            msg = f"Failed to delete object {key!r}: {err}"
            raise StorageError(msg) from err
