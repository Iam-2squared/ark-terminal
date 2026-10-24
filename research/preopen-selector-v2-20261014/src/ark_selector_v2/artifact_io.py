"""Exclusive fsynced artifacts and defensive restores; hash alone is not trust."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any
import hashlib
import io
import json
import os
import tempfile
import zipfile
from .contracts import digest, code_hash
from .exact_math import V2Error


def sha_file(path: Path) -> tuple[str,int]:
    h=hashlib.sha256()
    size=0
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
            size+=len(chunk)
    return h.hexdigest(),size


def _unsafe_link(path: Path) -> bool:
    # On Windows NTFS, junctions/reparse points are not necessarily symlinks.
    if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
        return True
    if os.name == "nt":
        try:
            return bool(getattr(path.stat(), "st_file_attributes", 0) & 0x400)
        except FileNotFoundError:
            return False
    return False


def safe_path(root: Path, relative: str) -> Path:
    rel=PurePosixPath(relative)
    if rel.is_absolute() or ".." in rel.parts or "\\" in relative or ":" in relative or not rel.parts:
        raise V2Error("PATH_TRAVERSAL")
    if _unsafe_link(root) or any(_unsafe_link(p) for p in root.parents):
        raise V2Error("SYMLINK_ESCAPE")
    path=root/relative
    if any(_unsafe_link(p) for p in (path,*path.parents) if p==root or p.is_relative_to(root)):
        raise V2Error("SYMLINK_ESCAPE")
    if not path.resolve().is_relative_to(root.resolve()):
        raise V2Error("PATH_OUTSIDE_PRIVATE_ROOT")
    return path


def exclusive_bytes(path: Path, data: bytes) -> None:
    if _unsafe_link(path) or any(_unsafe_link(p) for p in path.parents):
        raise V2Error("SYMLINK_ESCAPE")
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix=".v2-tmp-",dir=path.parent)
    try:
        with os.fdopen(fd,"wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        # Hard-link publication is atomic and fails if a target already exists.
        # os.replace/ordinary POSIX rename would silently overwrite artifacts.
        os.link(tmp,path)
        if hasattr(os,"O_DIRECTORY"):
            d=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
            try: os.fsync(d)
            finally: os.close(d)
    finally:
        Path(tmp).unlink(missing_ok=True)


def exclusive_json(path: Path, data: Any) -> None:
    exclusive_bytes(path,(json.dumps(data,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+"\n").encode())


@dataclass(frozen=True)
class TrustedModelReceipt:
    receipt: dict[str,Any]
    pinned_receipt_hash: str
    trusted_producer: str


def write_model(path: Path, model: Any, *, producer: str) -> TrustedModelReceipt:
    if producer!="THIS_PROCESS_SYNTHETIC_FACTORY":
        raise V2Error("MARKET_MODEL_WRITER_NOT_ADMITTED")
    import joblib
    buf=io.BytesIO()
    joblib.dump(model,buf,compress=3)
    payload=buf.getvalue()
    receipt={"schema":"ARK_V2_SELF_PRODUCED_MODEL_RECEIPT_V1","producer":producer,
             "model_sha256":hashlib.sha256(payload).hexdigest(),"bytes":len(payload),
             "code_hash":code_hash(),"mode":"SYNTHETIC","model_contract":model.receipt}
    exclusive_bytes(path,payload)
    exclusive_json(path.with_suffix(path.suffix+".receipt.json"),receipt)
    # The pin is retained by the generating process / independent control plane.
    return TrustedModelReceipt(receipt,digest(receipt),producer)


def load_model(path: Path, *, trusted: TrustedModelReceipt | None,
               independently_pinned_receipts: frozenset[str]) -> Any:
    if trusted is None or not isinstance(trusted,TrustedModelReceipt):
        raise V2Error("UNTRUSTED_PICKLE_REFUSED")
    if (trusted.pinned_receipt_hash not in independently_pinned_receipts
            or digest(trusted.receipt)!=trusted.pinned_receipt_hash
            or trusted.trusted_producer!="THIS_PROCESS_SYNTHETIC_FACTORY"
            or trusted.receipt.get("producer")!=trusted.trusted_producer):
        raise V2Error("HASH_IS_NOT_MODEL_TRUST")
    receipt=trusted.receipt
    if receipt.get("code_hash")!=code_hash():
        raise V2Error("MODEL_CODE_DRIFT_NO_REFIT")
    if sha_file(path)!=(receipt["model_sha256"],receipt["bytes"]):
        raise V2Error("MODEL_HASH_OR_SIZE_MISMATCH_NO_REFIT")
    import joblib
    model=joblib.load(path)
    from .model import ModelBundle
    if not isinstance(model,ModelBundle) or model.receipt!=receipt["model_contract"]:
        raise V2Error("MODEL_SCHEMA_OR_RECEIPT_DRIFT")
    model.validate_identity()
    return model


def restore_zip(archive: Path, root: Path, expected_entries: dict[str,dict[str,Any]],
                *, archive_hash: str, max_bytes: int) -> None:
    if sha_file(archive)[0]!=archive_hash:
        raise V2Error("ARCHIVE_HASH_MISMATCH")
    with zipfile.ZipFile(archive) as z:
        infos=z.infolist()
        if len(infos)!=len(expected_entries) or {i.filename for i in infos}!=set(expected_entries):
            raise V2Error("RESTORE_MANIFEST_ENTRIES_MISMATCH")
        if len({i.filename for i in infos})!=len(infos) or sum(i.file_size for i in infos)>max_bytes:
            raise V2Error("DUPLICATE_ENTRIES_OR_RESTORE_SIZE_LIMIT")
        for i in infos:
            safe_path(root,i.filename)
            if (i.external_attr>>16)&0o170000==0o120000 or i.is_dir():
                raise V2Error("ARCHIVE_SYMLINK_OR_DIRECTORY_REFUSED")
            if i.file_size!=expected_entries[i.filename]["bytes"]:
                raise V2Error("ENTRY_SIZE_MISMATCH")
        # Verify ALL payload hashes before publishing any restored entry.
        for i in infos:
            h=hashlib.sha256()
            with z.open(i) as f:
                for chunk in iter(lambda:f.read(1024*1024),b""):
                    h.update(chunk)
            if h.hexdigest()!=expected_entries[i.filename]["sha256"]:
                raise V2Error("ENTRY_HASH_MISMATCH")
        root.mkdir(parents=True,exist_ok=False)
        for i in infos:
            p=safe_path(root,i.filename)
            p.parent.mkdir(parents=True,exist_ok=True)
            # Stream extraction: individual entries can be much larger than RAM.
            with z.open(i) as source, p.open("xb") as target:
                for chunk in iter(lambda:source.read(1024*1024),b""):
                    target.write(chunk)
                target.flush()
                os.fsync(target.fileno())
