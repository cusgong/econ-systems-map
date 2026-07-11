# Blender economic node library

`econ-node-library.blend` is the authored source of truth. The GLB is a validated runtime derivative. This slice intentionally contains one ready model, `policy_rate`; the other 29 canonical roots remain scaffolded with `econ_ready=false`. There is no Three.js integration in this task.

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

- `node-specs.py`: imports the canonical 30 IDs/categories from `data/nodes.js` and fails at import if the motion map drifts.
- `scaffold-econ-node-library.py`: creates the collection/material/root contract idempotently and never replaces an existing non-empty mesh.
- `validate-econ-node-library.py`: validates evaluated Blender geometry and, optionally, a parsed GLB JSON chunk.
- `export-econ-node-library.py`: validates first, exports to a same-directory temporary GLB, post-validates it, and only then uses `os.replace`.
- `econ-node-library.blend`: authored source scene.
- `../../data/models/econ-node-library.glb`: runtime derivative.

Each ready model has one canonical empty root, one `${id}__body` mesh, and one `${id}__accent` mesh. Each mesh has exactly one material slot, so each model exports as exactly two GLB primitives.

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
  --python "$Project\scripts\blender\validate-econ-node-library.py" -- --scope ready

& $Blender --background --factory-startup --disable-autoexec $Blend --python-exit-code 1 `
  --python "$Project\scripts\blender\export-econ-node-library.py" -- --scope ready --output $Glb
```

The scaffold reopens an existing output before making changes. When it finds non-empty `policy_rate` geometry it reports `"policyRate":"preserved"` and leaves the mesh untouched.

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

The integration test covers the RED fixture, ready-scene GREEN, exact body triangle band, two-primitives contract, GLB size, and preservation of a sentinel output when an invalid export is attempted.

Scopes are progressive: `ready` validates every currently ready root, `proof` requires the six proof IDs, and `full` requires all 30 canonical IDs.
