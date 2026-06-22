#!/usr/bin/env python3
"""
NeoFace — ONNX Model Download & Export Script
==============================================

Downloads all ONNX model weights required by the NeoFace Trust Engine.
Models are saved to ./models/ (relative to the backend directory).

All 8 models have verified public HuggingFace download URLs (June 2026).

Usage:
    cd backend/
    python3 scripts/download_models.py              # show status
    python3 scripts/download_models.py --all        # download all
    python3 scripts/download_models.py --model anti_spoof
    python3 scripts/download_models.py --status

Available model keys:
    anti_spoof        MiniFASNetV2   (anti-spoofing, 80×80, 1.7 MB)
    liveness_v1       MiniFASNetV1   (passive liveness, copy of V2)
    liveness_v2       MiniFASNetV2   (passive liveness)
    emotion           FER+ 8-class   (emotion recognition, 64×64, 33 MB)
    midas_small       MiDaS Small    (depth estimation, 256×256, 63 MB)
    dpt_hybrid        DPT Hybrid     (depth estimation, 384×384, 508 MB)
    efficientnet_b4   ViT Deepfake   (deepfake detection, 224×224, 83 MB)
    xceptionnet       ViT Deepfake   (deepfake detection, 224×224, 85 MB)

Notes:
    - dpt_hybrid is large (~508 MB). Included in --all but takes ~3 min.
    - All services have graceful heuristic fallbacks if files are absent.
    - Models are git-ignored (*.onnx). Store in cloud or private registry.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path


# ── Output directory (relative to backend/) ──────────────────────────────────
MODELS_DIR = Path(__file__).parent.parent / "models"

# ── Download URL registry ─────────────────────────────────────────────────────
# Each entry has:
#   url       Primary download URL
#   alt_urls  Fallback URLs tried in order
#   dest      Target file path
#   description Human-readable name
#   required  Whether startup will warn loudly about this
#   download  Whether --all includes it

MODELS: dict[str, dict] = {

    # ── MiniFASNet V2 (anti-spoofing, primary) ──────────────────────────────
    # Source: garciafido/minifasnet-v2-anti-spoofing-onnx (verified June 2026)
    # Shape:  input[batch,3,80,80], output[batch,3] = [P(spoof),P(real),P(partial)]
    "anti_spoof": {
        "dest": MODELS_DIR / "anti_spoof.onnx",
        "description": "MiniFASNetV2 — anti-spoofing (80×80 NCHW, 3-class, 1.7 MB)",
        "required": True,
        "download": True,
        "url": (
            "https://huggingface.co/garciafido/minifasnet-v2-anti-spoofing-onnx"
            "/resolve/main/minifasnet_v2.onnx"
        ),
        "alt_urls": [],
    },

    # ── MiniFASNet V1 (passive liveness V1) ─────────────────────────────
    # No public V1 ONNX available — copy V2 weights (same architecture)
    "liveness_v1": {
        "dest": MODELS_DIR / "MiniFASNetV1.onnx",
        "description": "MiniFASNetV1 — passive liveness V1 (80×80, copy of V2)",
        "required": False,
        "download": True,
        "copy_from": "anti_spoof",
    },

    # ── MiniFASNet V2 copy (passive liveness V2) ────────────────────────
    "liveness_v2": {
        "dest": MODELS_DIR / "MiniFASNetV2.onnx",
        "description": "MiniFASNetV2 — passive liveness V2 (copy of anti_spoof.onnx)",
        "required": False,
        "download": True,
        "copy_from": "anti_spoof",
    },

    # ── FER+ Emotion (8-class facial emotion recognition) ──────────────────
    # Source: onnxmodelzoo/emotion-ferplus-8 (ONNX Model Zoo, verified June 2026)
    # Shape:  Input3[1,1,64,64] grayscale, Plus692_Output_0[1,8]
    # Classes: neutral, happy, surprise, fear, disgust, angry, contempt, sad
    "emotion": {
        "dest": MODELS_DIR / "emotion_mobilenetv3.onnx",
        "description": "FER+ Emotion — 8-class face emotion (64×64 grayscale, 33 MB)",
        "required": False,
        "download": True,
        "url": (
            "https://huggingface.co/onnxmodelzoo/emotion-ferplus-8"
            "/resolve/main/emotion-ferplus-8.onnx"
        ),
        "alt_urls": [],
    },

    # ── MiDaS Small (depth estimation, fast) ──────────────────────────
    # Source: Heliosoph/midas-small-onnx (verified June 2026)
    # Shape:  input_image[1,3,256,256], output_depth[1,256,256]
    "midas_small": {
        "dest": MODELS_DIR / "midas_small.onnx",
        "description": "MiDaS Small v2.1 — depth estimation (256×256, 63 MB)",
        "required": False,
        "download": True,
        "url": (
            "https://huggingface.co/Heliosoph/midas-small-onnx"
            "/resolve/main/midas_v21_small_256.onnx"
        ),
        "alt_urls": [],
    },

    # ── DPT Hybrid (depth, high accuracy, large) ───────────────────────
    # Source: lquint/dpt-hybrid-midas-onnx (verified June 2026)
    # Shape:  pixel_values[batch,3,H,W], predicted_depth[batch,H,W]
    "dpt_hybrid": {
        "dest": MODELS_DIR / "dpt_hybrid.onnx",
        "description": "DPT Hybrid — depth estimation (384×384, 508 MB)",
        "required": False,
        "download": True,   # included in --all (large but has public URL)
        "url": (
            "https://huggingface.co/lquint/dpt-hybrid-midas-onnx"
            "/resolve/main/onnx/model.onnx"
        ),
        "alt_urls": [],
    },

    # ── ViT Deepfake Primary (3-class: Artificial/Deepfake/Real) ─────────
    # Source: prithivMLmods/AI-vs-Deepfake-vs-Real-ONNX (verified June 2026)
    # Shape:  pixel_values[batch,3,224,224] (mean/std=0.5), logits[batch,3]
    # Labels: {0: Artificial, 1: Deepfake, 2: Real}
    "efficientnet_b4": {
        "dest": MODELS_DIR / "efficientnet_b4_deepfake.onnx",
        "description": "ViT Deepfake Primary — AI-vs-Deepfake-vs-Real (224×224, 83 MB)",
        "required": False,
        "download": True,
        "url": (
            "https://huggingface.co/prithivMLmods/AI-vs-Deepfake-vs-Real-ONNX"
            "/resolve/main/onnx/model_int8.onnx"
        ),
        "alt_urls": [],
    },

    # ── ViT Deepfake Secondary (2-class) ───────────────────────────────────────
    # Source: prithivMLmods/Deepfake-Detection-Exp-02-22-ONNX (verified June 2026)
    # Shape:  pixel_values[batch,3,224,224] (mean/std=0.5), logits[batch,2]
    "xceptionnet": {
        "dest": MODELS_DIR / "xceptionnet_deepfake.onnx",
        "description": "ViT Deepfake Secondary — Exp-02-22 (224×224, 85 MB)",
        "required": False,
        "download": True,
        "url": (
            "https://huggingface.co/prithivMLmods/Deepfake-Detection-Exp-02-22-ONNX"
            "/resolve/main/onnx/model_int8.onnx"
        ),
        "alt_urls": [],
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Progress + download helpers
# ─────────────────────────────────────────────────────────────────────────────

def _progress_hook(count: int, block_size: int, total_size: int) -> None:
    if total_size > 0:
        done = count * block_size
        pct = min(100.0, done / total_size * 100)
        mb = done / 1024 / 1024
        total_mb = total_size / 1024 / 1024
        bar = "█" * int(pct / 2) + "░" * (50 - int(pct / 2))
        print(f"\r  [{bar}] {pct:5.1f}%  {mb:.1f}/{total_mb:.1f} MB", end="", flush=True)


def _try_download(url: str, dest: Path, description: str) -> bool:
    """Attempt a single URL download. Returns True on success."""
    print(f"\n⬇  {description}")
    print(f"   URL : {url}")
    print(f"   Dest: {dest}")
    dest.parent.mkdir(parents=True, exist_ok=True)

    try:
        with tempfile.NamedTemporaryFile(dir=dest.parent, delete=False, suffix=".tmp") as f:
            tmp_path = Path(f.name)
        urllib.request.urlretrieve(url, tmp_path, _progress_hook)
        print()  # newline after progress bar
        tmp_path.rename(dest)
        size_mb = dest.stat().st_size / 1024 / 1024
        print(f"   ✅ Saved {size_mb:.1f} MB → {dest.name}")
        return True
    except Exception as exc:
        print(f"\n   ❌ Failed ({type(exc).__name__}): {exc}")
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass
        return False


def download_model(name: str, info: dict, skip_existing: bool = True) -> bool:
    """Download (or copy) a model. Returns True on success."""
    dest: Path = info["dest"]

    if skip_existing and dest.exists():
        size_mb = dest.stat().st_size / 1024 / 1024
        print(f"   ⏭  {dest.name} already exists ({size_mb:.1f} MB) — skipping")
        return True

    # Special case: copy from sibling
    if "copy_from" in info:
        src_name = info["copy_from"]
        src_dest: Path = MODELS[src_name]["dest"]
        if src_dest.exists():
            import shutil
            shutil.copy2(src_dest, dest)
            size_mb = dest.stat().st_size / 1024 / 1024
            print(f"   📋 Copied {src_dest.name} → {dest.name} ({size_mb:.1f} MB)")
            return True
        else:
            print(f"   ⚠️  Copy source {src_dest.name} not yet downloaded — skipping {dest.name}")
            return False

    # URL download
    url = info.get("url", "")
    if not url:
        print(f"   ℹ️  {dest.name} has no download URL — use --export or --instructions")
        return False

    ok = _try_download(url, dest, info["description"])
    if not ok:
        for alt in info.get("alt_urls", []):
            print(f"   🔄 Trying alternate URL...")
            ok = _try_download(alt, dest, info["description"])
            if ok:
                break

    return ok


# ─────────────────────────────────────────────────────────────────────────────
# PyTorch export helpers
# ─────────────────────────────────────────────────────────────────────────────

def _check_torch_deps() -> bool:
    """Check that torch + timm + onnx are importable."""
    missing = []
    for pkg in ("torch", "timm", "onnx"):
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"❌ Missing packages: {', '.join(missing)}")
        print(f"   Install with: pip install {' '.join(missing)}")
        return False
    return True


def export_midas_small(dest: Path) -> bool:
    """Export MiDaS Small v2.1 via torch.hub to ONNX."""
    if not _check_torch_deps():
        return False
    import torch  # type: ignore[import]
    print(f"\n📦 Exporting MiDaS Small → {dest.name}")
    try:
        model = torch.hub.load("intel-isl/MiDaS", "MiDaS_small", trust_repo=True)
        model.eval()
        dummy = torch.randn(1, 3, 256, 256)
        dest.parent.mkdir(parents=True, exist_ok=True)
        torch.onnx.export(
            model, dummy, str(dest),
            input_names=["input"], output_names=["output"],
            opset_version=17, dynamic_axes={"input": {0: "batch"}},
        )
        size_mb = dest.stat().st_size / 1024 / 1024
        print(f"   ✅ Exported {size_mb:.1f} MB → {dest.name}")
        return True
    except Exception as exc:
        print(f"   ❌ Export failed: {exc}")
        return False


def export_emotion(dest: Path) -> bool:
    """Export MobileNetV3 emotion stub to ONNX."""
    if not _check_torch_deps():
        return False
    import torch  # type: ignore[import]
    import timm   # type: ignore[import]
    print(f"\n📦 Exporting MobileNetV3 emotion model → {dest.name}")
    try:
        model = timm.create_model("mobilenetv3_small_100", pretrained=True, num_classes=7)
        model.eval()
        dummy = torch.randn(1, 3, 112, 112)
        dest.parent.mkdir(parents=True, exist_ok=True)
        torch.onnx.export(
            model, dummy, str(dest),
            input_names=["input"], output_names=["output"],
            opset_version=17, dynamic_axes={"input": {0: "batch"}},
        )
        size_mb = dest.stat().st_size / 1024 / 1024
        print(f"   ✅ Exported {size_mb:.1f} MB → {dest.name}")
        print("   ⚠️  NOTE: These are ImageNet weights, NOT fine-tuned on FER2013.")
        print("       The service will use the ONNX file but accuracy is limited.")
        print("       Fine-tune on FER2013/AffectNet for production use.")
        return True
    except Exception as exc:
        print(f"   ❌ Export failed: {exc}")
        return False


def export_efficientnet_b4(dest: Path) -> bool:
    """Export EfficientNet-B4 deepfake stub to ONNX."""
    if not _check_torch_deps():
        return False
    import torch  # type: ignore[import]
    import timm   # type: ignore[import]
    print(f"\n📦 Exporting EfficientNet-B4 deepfake model → {dest.name}")
    try:
        model = timm.create_model("efficientnet_b4", pretrained=True, num_classes=2)
        model.eval()
        dummy = torch.randn(1, 3, 224, 224)
        dest.parent.mkdir(parents=True, exist_ok=True)
        torch.onnx.export(
            model, dummy, str(dest),
            input_names=["input"], output_names=["output"],
            opset_version=17, dynamic_axes={"input": {0: "batch"}},
        )
        size_mb = dest.stat().st_size / 1024 / 1024
        print(f"   ✅ Exported {size_mb:.1f} MB → {dest.name}")
        print("   ⚠️  NOTE: These are ImageNet weights, NOT fine-tuned on FaceForensics++.")
        print("       The threshold is automatically raised to 0.85 in heuristic mode.")
        print("       Fine-tune on FaceForensics++/DeepFakeBench for production use.")
        return True
    except Exception as exc:
        print(f"   ❌ Export failed: {exc}")
        return False


def export_xceptionnet(dest: Path) -> bool:
    """Export XceptionNet deepfake stub to ONNX."""
    if not _check_torch_deps():
        return False
    import torch  # type: ignore[import]
    import timm   # type: ignore[import]
    print(f"\n📦 Exporting XceptionNet deepfake model → {dest.name}")
    try:
        model = timm.create_model("xception", pretrained=True, num_classes=2)
        model.eval()
        dummy = torch.randn(1, 3, 299, 299)
        dest.parent.mkdir(parents=True, exist_ok=True)
        torch.onnx.export(
            model, dummy, str(dest),
            input_names=["input"], output_names=["output"],
            opset_version=17, dynamic_axes={"input": {0: "batch"}},
        )
        size_mb = dest.stat().st_size / 1024 / 1024
        print(f"   ✅ Exported {size_mb:.1f} MB → {dest.name}")
        return True
    except Exception as exc:
        print(f"   ❌ Export failed: {exc}")
        return False


# Map export_fn strings to callables
EXPORT_FNS = {
    "export_midas_small":      export_midas_small,
    "export_emotion":          export_emotion,
    "export_efficientnet_b4":  export_efficientnet_b4,
    "export_xceptionnet":      export_xceptionnet,
}


# ─────────────────────────────────────────────────────────────────────────────
# Status report
# ─────────────────────────────────────────────────────────────────────────────

def print_status() -> None:
    """Print current model file status."""
    print("\n" + "─" * 65)
    print("NeoFace Model Status")
    print("─" * 65)

    missing_required = []

    for name, info in MODELS.items():
        dest: Path = info["dest"]
        required = info.get("required", False)
        if dest.exists():
            size_mb = dest.stat().st_size / 1024 / 1024
            print(f"  ✅ {dest.name:<45} {size_mb:>7.1f} MB")
        else:
            tag = "[required]" if required else "[optional]"
            print(f"  ❌ {dest.name:<45} MISSING {tag}")
            if required:
                missing_required.append(name)

    print("─" * 65)

    if missing_required:
        print(f"\n⚠️  {len(missing_required)} required model(s) missing.")
        print("   Run: python3 scripts/download_models.py --all")
    else:
        print("\n✅ All required models present.")
        missing_optional = [n for n, i in MODELS.items() if not i["dest"].exists() and not i.get("required")]
        if missing_optional:
            print(f"   {len(missing_optional)} optional models absent — services will use heuristic fallbacks.")

    # InsightFace check
    insightface_home = os.environ.get("INSIGHTFACE_HOME", os.path.expanduser("~/.insightface"))
    buffalo_path = Path(insightface_home) / "models" / "buffalo_l"
    if buffalo_path.exists():
        print(f"\n✅ InsightFace buffalo_l: {buffalo_path}")
    else:
        print(f"\n⚠️  InsightFace buffalo_l not found at {buffalo_path}")
        print("   → Auto-downloaded on first backend startup (requires internet)")


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download / export NeoFace ONNX model weights",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"Available model keys: {', '.join(MODELS.keys())}",
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Download all models that have public URLs (skips existing)",
    )
    parser.add_argument(
        "--model", metavar="NAME", action="append", default=[],
        help="Download/export a specific model (repeat for multiple)",
    )
    parser.add_argument(
        "--export", action="store_true",
        help="Export models that require PyTorch (emotion, efficientnet_b4, xceptionnet)",
    )
    parser.add_argument(
        "--status", action="store_true",
        help="Show model file status and exit",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Re-download even if file already exists",
    )
    args = parser.parse_args()

    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    # Default: show status
    if not (args.all or args.model or args.export):
        print_status()
        return

    skip_existing = not args.force
    results: dict[str, bool] = {}

    if args.all:
        print("🚀 Downloading all models with public URLs...")
        for name, info in MODELS.items():
            if info.get("download", False):
                results[name] = download_model(name, info, skip_existing)
            else:
                print(f"\n   ⏭  {info['dest'].name} — requires --export (PyTorch) or --model {name}")

    if args.model:
        for name in args.model:
            if name not in MODELS:
                print(f"❌ Unknown model: {name!r}")
                print(f"   Valid names: {', '.join(MODELS.keys())}")
                continue
            info = MODELS[name]
            # If it has an export_fn and no URL, run export
            if "export_fn" in info and not info.get("url"):
                fn = EXPORT_FNS[info["export_fn"]]
                results[name] = fn(info["dest"])
            else:
                results[name] = download_model(name, info, skip_existing)

    if args.export:
        for name, info in MODELS.items():
            if "export_fn" in info:
                fn = EXPORT_FNS[info["export_fn"]]
                results[name] = fn(info["dest"])

    print_status()

    failed = [k for k, v in results.items() if not v]
    if failed:
        print(f"\n⚠️  {len(failed)} operation(s) failed/skipped: {', '.join(failed)}")
        print("   Services will use heuristic fallbacks for missing models.")
        sys.exit(1)
    elif results:
        print("\n✅ All requested operations completed.")


if __name__ == "__main__":
    main()
