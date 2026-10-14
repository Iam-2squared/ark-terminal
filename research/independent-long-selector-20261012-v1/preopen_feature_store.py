"""Private float64 columnar cache. Exact price labels remain separate strings."""
from __future__ import annotations

import json
import os
from collections.abc import Mapping, Sequence
from pathlib import Path

import numpy as np

from preopen_io import private_path, verify_entry, sha_file, write_json
from preopen_selector import digest, PreopenError
from preopen_feature_policy import policy_hash, source_code_hash, cache_binding


class FeatureView(Mapping):
    def __init__(self, values, columns, indexes):
        self.values_array = values
        self.columns = columns
        self.indexes = indexes

    def __len__(self):
        return len(self.columns)

    def __iter__(self):
        return iter(self.columns)

    def __getitem__(self, name):
        value = float(self.values_array[self.indexes[name]])
        if np.isnan(value):
            return None
        if not np.isfinite(value):
            raise PreopenError("CORRUPT_COLUMNAR_NONFINITE_VALUE")
        return value

    def vector(self, names):
        return self.values_array[[self.indexes[n] for n in names]]


class FeatureStore(Sequence):
    def __init__(self, manifest_path, *, private_root):
        path = private_path(manifest_path, private_root)
        self.manifest = json.loads(path.read_text())
        if self.manifest.get("schema") != "ARK_PREOPEN_COLUMNAR_FEATURES_V2":
            raise PreopenError("WRONG_COLUMNAR_FEATURE_SCHEMA")
        bound = self.manifest.get("cacheBinding", {})
        if bound.get("featurePolicyHash") != policy_hash() or bound.get("codeHash") != source_code_hash():
            raise PreopenError("STALE_COLUMNAR_CODE_OR_FEATURE_POLICY")
        try:
            rebuilt = cache_binding(code_hash=bound["codeHash"], input_hash=bound["inputHash"],
                calendar_hash=bound["calendarHash"], basis_hash=bound["basisHash"],
                schema_hash=bound["featureSchemaHash"])
        except (KeyError, ValueError) as exc:
            raise PreopenError("INVALID_COLUMNAR_CACHE_BINDING") from exc
        if (rebuilt != bound or bound["inputHash"] != self.manifest["inputManifestHash"]
                or bound["featureSchemaHash"] != self.manifest["featureSchemaHash"]):
            raise PreopenError("COLUMNAR_CACHE_INPUT_SCHEMA_BINDING_MISMATCH")
        self.columns = tuple(self.manifest["columns"])
        if list(self.columns) != sorted(set(self.columns)):
            raise PreopenError("COLUMNAR_COLUMNS_NOT_UNIQUE_CANONICAL")
        self.indexes = {k: i for i,k in enumerate(self.columns)}
        data_path = verify_entry(self.manifest["matrix"], private_root)
        meta_path = verify_entry(self.manifest["metadata"], private_root)
        # Avoid simultaneously holding a full metadata string, split copies and
        # parsed dictionaries. Repeated missingness patterns share one mapping;
        # values, reason names and row identity are unchanged.
        import sys
        patterns = {}
        self.rows = []
        def shared_keys(pairs):
            return {sys.intern(k):v for k,v in pairs}
        with meta_path.open(encoding="utf-8") as stream:
            for line in stream:
                if not line.strip():
                    continue
                row = json.loads(line, object_pairs_hook=shared_keys)
                missing = row.get("missingReasons")
                if missing is not None:
                    key = tuple(sorted((k,sys.intern(v)) for k,v in missing.items()))
                    row["missingReasons"] = patterns.setdefault(key,dict(key))
                self.rows.append(row)
        count = self.manifest["rowN"]
        if len(self.rows) != count or self.manifest["matrix"]["bytes"] != count*len(self.columns)*8:
            raise PreopenError("COLUMNAR_CARDINALITY_OR_BYTES")
        self.matrix = (np.memmap(data_path, dtype="<f8", mode="r",
                                shape=(count,len(self.columns))) if count else None)
        if digest(self.columns) != self.manifest["featureSchemaHash"]:
            raise PreopenError("COLUMNAR_SCHEMA_HASH")

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, index):
        if isinstance(index, slice):
            return [self[i] for i in range(*index.indices(len(self)))]
        row = dict(self.rows[index])
        row["features"] = FeatureView(self.matrix[index], self.columns, self.indexes)
        return row


def write_feature_store(rows, directory, *, private_root, input_manifest_hash,
                        cache_context, schema_if_empty=()):
    directory = private_path(directory, private_root)
    directory.mkdir(parents=True, exist_ok=False, mode=0o700)
    matrix_file, metadata_file = directory/"features.f64", directory/"metadata.jsonl"
    columns = None
    observed = None
    count = 0
    with matrix_file.open("xb") as binary, metadata_file.open("x",encoding="utf-8") as meta:
        os.chmod(matrix_file,0o600)
        os.chmod(metadata_file,0o600)
        for row in rows:
            names = tuple(sorted(row["features"]))
            if columns is None:
                columns = names
                observed = np.zeros(len(names),dtype=np.int64)
            if names != columns:
                raise PreopenError("CHANGING_NATIVE_FEATURE_SCHEMA")
            values = np.asarray([np.nan if row["features"][k] is None
                                 else row["features"][k] for k in columns],dtype="<f8")
            if np.isinf(values).any():
                raise PreopenError("NATIVE_FEATURE_INFINITY")
            binary.write(values.tobytes())
            observed += ~np.isnan(values)
            body = {k:v for k,v in row.items() if k != "features"}
            meta.write(json.dumps(body,ensure_ascii=False,allow_nan=False,sort_keys=True)+"\n")
            count += 1
    columns = columns or tuple(schema_if_empty)
    for p in (matrix_file, metadata_file):
        with p.open("rb") as stream:
            os.fsync(stream.fileno())
    msha, mbytes = sha_file(matrix_file)
    rsha, rbytes = sha_file(metadata_file)
    binding = cache_binding(code_hash=source_code_hash(), input_hash=input_manifest_hash,
        calendar_hash=cache_context["calendarHash"], basis_hash=cache_context["basisHash"],
        schema_hash=digest(columns))
    manifest = {"schema":"ARK_PREOPEN_COLUMNAR_FEATURES_V2", "cacheBinding":binding,
                "inputManifestHash":input_manifest_hash,"rowN":count,
                "columns":columns,"featureSchemaHash":digest(columns),
                "matrix":{"path":str(matrix_file),"sha256":msha,"bytes":mbytes},
                "metadata":{"path":str(metadata_file),"sha256":rsha,"bytes":rbytes},
                "observedCounts":observed.tolist() if observed is not None else [0]*len(columns),
                "featurePrecision":"FLOAT64","priceLabels":"SEPARATE_EXACT_DECIMAL_STRINGS"}
    entry = write_json(directory/"manifest.json",manifest)
    entry["format"] = "ARK_PREOPEN_COLUMNAR_FEATURES_V2"
    return entry
