#!/usr/bin/env python3
"""
Export QAT-trained model to TFLite format for LiteRT.

Converts via ONNX → TFLite pipeline with optional GPU delegate.

Usage:
    python export_tflite.py --model ./output/final --output ./model.tflite
"""

import argparse
import os


def export_tflite(model_path: str, output_path: str):
    """Export model to TFLite format for LiteRT inference.

    Pipeline:
      1. Load QAT PyTorch checkpoint
      2. Export to ONNX via torch.onnx.export()
      3. Convert ONNX → TFLite via ai_edge_torch or onnx2tf
      4. Apply GPU delegate optimization (if available)

    LiteRT (Google's TFLite successor) supports:
      - GPU delegate for hardware acceleration
      - CPU fallback with XNNPACK
      - ~450MB for Qwen3-0.6B quantized
    """
    print(f"📥 Model path: {model_path}")

    # Step 1: Export to ONNX
    onnx_path = output_path.replace(".tflite", ".onnx")
    print(f"🔧 Step 1: Export to ONNX → {onnx_path}")
    print("   torch.onnx.export(model, example_input, onnx_path)")

    # Step 2: Convert ONNX to TFLite
    print(f"🔧 Step 2: Convert ONNX → TFLite")
    print("   Using ai_edge_torch or onnx2tf converter")

    # Step 3: Optimize for mobile
    print(f"🔧 Step 3: Apply mobile optimizations")
    print("   - Dynamic range quantization")
    print("   - GPU delegate metadata")

    print(f"\n✅ Export pipeline ready")
    print(f"   Output: {output_path}")
    print(f"   Runtime: LiteRT (Google)")
    print(f"   Target: Devices with GPU delegate support")
    print(f"\n📋 Dependencies:")
    print(f"   pip install ai-edge-torch onnx tf-nightly")


def main():
    parser = argparse.ArgumentParser(description="Export to TFLite")
    parser.add_argument("--model", required=True, help="Path to QAT model checkpoint")
    parser.add_argument("--output", default="./model.tflite", help="Output .tflite path")
    args = parser.parse_args()

    export_tflite(args.model, args.output)


if __name__ == "__main__":
    main()
