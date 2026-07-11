"""Atomically export validated ready economic node roots to one GLB."""

from __future__ import annotations

import argparse
import importlib.util
import os
from pathlib import Path
import sys
import tempfile

import bpy


SCRIPT_DIR = Path(__file__).resolve().parent


def _load_validator():
    module_path = SCRIPT_DIR / "validate-econ-node-library.py"
    spec = importlib.util.spec_from_file_location("econ_node_validator", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load validator: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VALIDATOR = _load_validator()


def _arguments(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", choices=("ready", "proof", "full"), default="ready")
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args(argv)


def _select_roots_and_descendants(roots: list[bpy.types.Object]) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    selected: list[bpy.types.Object] = []
    for root in roots:
        selected.append(root)
        selected.extend(root.children_recursive)
    for obj in selected:
        obj.hide_set(False)
        obj.hide_viewport = False
        obj.hide_render = False
        obj.select_set(True)
    if selected:
        bpy.context.view_layer.objects.active = selected[0]


def main(argv: list[str] | None = None) -> int:
    args = _arguments(sys.argv[sys.argv.index("--") + 1 :] if argv is None and "--" in sys.argv else (argv or []))
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    summary, roots = VALIDATOR.validate_scene(args.scope)
    if summary["errors"]:
        VALIDATOR.emit_summary(summary)
        return 1

    _select_roots_and_descendants(roots)
    handle = tempfile.NamedTemporaryFile(
        prefix=f".{output.stem}-",
        suffix=".glb",
        dir=output.parent,
        delete=False,
    )
    temp_glb = Path(handle.name)
    handle.close()
    try:
        bpy.ops.export_scene.gltf(
            filepath=str(temp_glb),
            export_format="GLB",
            use_selection=True,
            export_yup=True,
            export_apply=True,
            export_normals=True,
            export_tangents=False,
            export_texcoords=False,
            export_materials="EXPORT",
            export_image_format="NONE",
            export_vertex_color="NONE",
            export_cameras=False,
            export_lights=False,
            export_extras=True,
            export_animations=False,
            export_skins=False,
            export_morph=False,
            export_draco_mesh_compression_enable=False,
            use_mesh_edges=False,
            use_mesh_vertices=False,
        )
        summary = VALIDATOR.validate_glb(
            temp_glb,
            [root.name for root in roots],
            summary,
        )
        if summary["errors"]:
            VALIDATOR.emit_summary(summary)
            return 1
        os.replace(temp_glb, output)
        summary["bytes"] = output.stat().st_size
        VALIDATOR.emit_summary(summary)
        return 0
    except Exception as exc:
        VALIDATOR._append_error(summary, f"GLB export failed: {exc}")
        VALIDATOR.emit_summary(summary)
        return 1
    finally:
        if temp_glb.exists():
            temp_glb.unlink()


if __name__ == "__main__":
    raise SystemExit(main())
