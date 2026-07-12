# Blender economic node library

`econ-node-library.blend` is the authored source of truth. The GLB is a validated runtime derivative. The production library contains 30 distinct ready instruments and no planned sphere fallbacks. Every entry point fails unless `bpy.app.version` is exactly `5.1.2`.

## Pinned runtime

Use this exact executable for scaffold, validation, tests, and export:

```powershell
$Blender = 'C:\Users\HP\AppData\Local\Programs\Blender\5.1.2-portable\blender-5.1.2-windows-x64\blender.exe'
& $Blender --version
```

Verified output begins with `Blender 5.1.2` (build hash `ec6e62d40fa9`). The portable archive came from:

```text
https://download.blender.org/release/Blender5.1/blender-5.1.2-windows-x64.zip
SHA256 345bedea7b0acf7cc9666423d8553f9129622aea34ded65c23e8cb70f83f14ff
```

The SHA-256 matches Blender's official `blender-5.1.2.sha256` manifest. The Microsoft Store installation is left untouched.

## Files and contracts

- `node-specs.py`: imports the canonical 30 IDs/categories from `data/nodes.js`, stores every model's exact pivot/child-translation contract and per-role minimum bevel coverage, and fails at import if the motion map drifts.
- `scaffold-econ-node-library.py`: creates the collection/material/root contract idempotently, authors the canonical 48-segment base/40-segment annulus `policy_rate`, and upgrades the legacy modifier-free policy mesh once.
- `hard_surface.py`: shared deterministic closed-manifold assembly, normalization, real-pivot rebasing, weighted-edge three-segment bevel authoring, and two-mesh finalization helpers.
- `author-proof-models.py`: deterministically rebuilds `policy_rate` from the shared scaffold source on every proof pass, then rebuilds any requested non-anchor proof models in canonical order while preserving all unrelated roots.
- `proof_models_external.py`, `proof_models_real.py`, `proof_models_psychology.py`: reproducible geometry builders for the five new proof instruments.
- `model_authoring.py`: validates the existing ready chain, snapshots unrelated geometry and the complete PBR node contract, authors one batch, serializes it to a sibling staging `.blend`, reopens it, enforces every frozen material/root hash, and atomically replaces the original only after every gate passes.
- `money_price_models.py`, `wage_external_models.py`, `real_equity_models.py`, `asset_policy_models.py`: scene-independent hard-surface builders for the remaining 24 instruments.
- `author-money-price-models.py`, `author-wage-external-models.py`, `author-real-equity-models.py`, `author-asset-policy-models.py`: ordered six-model authoring batches that preserve and revalidate every predecessor.
- `validate-econ-node-library.py`: validates evaluated Blender geometry, binary weighted-bevel contribution, unique mesh ownership, deterministic three-view occupancy masks, accent motion metadata, and the complete GLB container. GLB checks include JSON/BIN chunks, buffer/accessor byte ranges, decoded POSITION/INDEX payloads, and a triangle-list-order/cyclic-start-independent but winding-sensitive fingerprint and bounds comparison against the evaluated `.blend`. Asset discovery is collection-aware: `10_WIP` cutters/references and `90_QA` cameras/lights are allowed in the source but never selected or exported.
- `export-econ-node-library.py`: validates first, exports to a same-directory temporary GLB, post-validates it, and only then uses `os.replace`.
- `econ-node-library.blend`: authored source scene.
- `../../data/models/econ-node-library.glb`: runtime derivative.

Each ready model has one canonical empty root, one `${id}__body` mesh, and one `${id}__accent` mesh. Each mesh has exactly one material slot, so the library exports as exactly 60 GLB primitives. All accent transforms are source-locked in `node-specs.py`: child rotation and scale remain identity, Blender translation must match the stored numeric tuple, and GLB translation must equal `(x, z, -y)` with the exact canonical pivot label.

The common three-segment bevel is applied to visibly exposed hard-surface edges, with model/role minimum tagged-edge counts enforced by validation. Edge weights are binary: tagged edges must be approximately `1.0`, untagged edges approximately `0.0`; fractional values such as `0.51` fail even though Blender would evaluate them. Smooth turned stock (tori, capsules, spheres), smooth tessellation, and cylindrical ties whose end caps are buried inside adjoining parts are intentional exclusions. GDP service-gap rail caps, both oil boss shoulders and the rotating shaft/hub, and every housing portal, foundation beam, transfer beam, and gusset are explicitly tagged. This keeps curved/internal supports clean while preventing a one-shell token bevel from satisfying a complex model.

## Reproduce

Run from the project root:

```powershell
$Project = (Resolve-Path '.').Path
$Blender = 'C:\Users\HP\AppData\Local\Programs\Blender\5.1.2-portable\blender-5.1.2-windows-x64\blender.exe'
$Blend = "$Project\scripts\blender\econ-node-library.blend"
$Glb = "$Project\data\models\econ-node-library.glb"

& $Blender --background --factory-startup --disable-autoexec --python-exit-code 1 `
  --python "$Project\scripts\blender\scaffold-econ-node-library.py" -- --output $Blend

& $Blender --background --factory-startup --disable-autoexec $Blend --python-exit-code 1 `
  --python "$Project\scripts\blender\author-proof-models.py" -- --output $Blend

& $Blender --background --factory-startup --disable-autoexec $Blend --python-exit-code 1 `
  --python "$Project\scripts\blender\author-money-price-models.py" -- --output $Blend

& $Blender --background --factory-startup --disable-autoexec $Blend --python-exit-code 1 `
  --python "$Project\scripts\blender\author-wage-external-models.py" -- --output $Blend

& $Blender --background --factory-startup --disable-autoexec $Blend --python-exit-code 1 `
  --python "$Project\scripts\blender\author-real-equity-models.py" -- --output $Blend

& $Blender --background --factory-startup --disable-autoexec $Blend --python-exit-code 1 `
  --python "$Project\scripts\blender\author-asset-policy-models.py" -- --output $Blend

& $Blender --background --factory-startup --disable-autoexec $Blend --python-exit-code 1 `
  --python "$Project\scripts\blender\validate-econ-node-library.py" -- --scope full

& $Blender --background --factory-startup --disable-autoexec $Blend --python-exit-code 1 `
  --python "$Project\scripts\blender\export-econ-node-library.py" -- --scope full --output $Glb
```

The scaffold reopens an existing output before making changes. A current beveled `policy_rate` reports `"policyRate":"preserved"`; a legacy non-beveled mesh is rebuilt from the canonical 48/40 source and reports `"policyRate":"upgraded"`. Proof authoring always rebuilds that same policy source, which makes legacy migration and repeated GLB export byte-stable.

## Validation-first RED

Create a deliberate no-ready fixture outside the repository and verify it fails for the expected reason:

```powershell
$RedBlend = Join-Path $env:TEMP 'econ-node-library-red.blend'
& $Blender --background --factory-startup --disable-autoexec --python-exit-code 1 `
  --python "$Project\scripts\blender\scaffold-econ-node-library.py" -- --output $RedBlend --scaffold-only
& $Blender --background --factory-startup --disable-autoexec $RedBlend --python-exit-code 1 `
  --python "$Project\scripts\blender\validate-econ-node-library.py" -- --scope ready
```

Expected: exit code `1`, `readyCount=0`, and the sole error `no ready roots for scope=ready`.

## Tests

```powershell
python -m unittest discover -s scripts/blender/tests -p "test_*.py" -v
```

The integration suite covers the RED fixture, exact six-ID proof scope, the ordered 6→12→18→24→30 authoring chain, per-model and total triangle bands, accent area, normalized bounds, 60 primitives, real weighted three-segment bevels, fractional-weight rejection, CPU-rasterized three-view silhouette separation, canonical one-owner mesh data, accent motion/pivot drift, decoded GLB geometry-payload and reversed-winding drift, deterministic GLB export, full PBR/node-link preservation, and preservation of a sentinel output when an invalid export is attempted.

The v2.5.0 release gate passes all 35 Blender/Python contract tests. It includes a valid-but-off-contract post-author mutation proving that a failed serialized frozen-root check leaves the original `.blend` byte-for-byte untouched.

The proof gate remains available for focused review and validates `readyCount=6`, `fallbackCount=24`, `primitives=12`, 10,600–13,000 total triangles, and a proof GLB no larger than 600,000 bytes. The full gate requires `readyCount=30`, `fallbackCount=0`, `primitives=60`, no model above 3,000 triangles, no library above 100,000 triangles, and a GLB no larger than 3,000,000 bytes. Ignored QA tooling under `.superpowers/sdd/` renders isolated FRONT/SIDE/TOP, PBR perspective, true 48px, and alpha-mask tiles so framing and pairwise silhouette checks remain reproducible without polluting the authored scene.

Scopes are progressive: `ready` validates every currently ready root, `proof` requires the six proof IDs, and `full` requires all 30 canonical IDs.
