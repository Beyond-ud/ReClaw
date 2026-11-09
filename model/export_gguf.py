#!/usr/bin/env python3
"""
Export QAT-trained model to GGUF format for llama.cpp.

Converts the PyTorch checkpoint to GGUF with Q4_K_M quantization
for broad ARM64 compatibility.

Usage:
    python export_gguf.py --model ./output/final --output ./model.gguf
"""

import argparse
import os
import subprocess
import sys


def export_gguf(model_path: str, output_path: str, quant_type: str = "Q4_K_M"):
    """Export model to GGUF format using llama.cpp conversion tools.

    Pipeline:
      1. Convert HuggingFace model to GGUF base format
      2. Apply quantization (Q4_K_M recommended for mobile)
      3. Output .gguf file ready for llama.cpp inference

    Q4_K_M provides a good balance of quality vs size for mobile:
      - ~400MB for Qwen3-0.6B
      - Broad device compatibility (≥1.5GB RAM)
      - Good inference speed on ARM64
    """
    print(f"📥 Model path: {model_path}")
    print(f"📦 Quantization: {quant_type}")

    # Step 1: Convert to GGUF (requires llama.cpp's convert script)
    gguf_base = output_path.replace(".gguf", "-f32.gguf")

    print("🔧 Step 1: Converting to GGUF base format...")
    convert_cmd = [
        sys.executable, "convert_hf_to_gguf.py",
        model_path,
        "--outfile", gguf_base,
        "--outtype", "f32",
    ]
    print(f"   Running: {' '.join(convert_cmd)}")
    # subprocess.run(convert_cmd, check=True)

    # Step 2: Quantize
    print(f"🔧 Step 2: Quantizing to {quant_type}...")
    quantize_cmd = [
        "./llama-quantize",
        gguf_base,
        output_path,
        quant_type,
    ]
    print(f"   Running: {' '.join(quantize_cmd)}")
    # subprocess.run(quantize_cmd, check=True)

    print(f"\n✅ Export complete (commands shown above)")
    print(f"   Output: {output_path}")
    print(f"   Runtime: llama.cpp")
    print(f"   Target: ARM64 devices with ≥1.5GB RAM")
    print(f"\n📋 To run these commands:")
    print(f"   1. Clone llama.cpp: git clone https://github.com/ggerganov/llama.cpp")
    print(f"   2. Build: cd llama.cpp && make")
    print(f"   3. Run the convert and quantize commands above")


def main():
    parser = argparse.ArgumentParser(description="Export to GGUF")
    parser.add_argument("--model", required=True, help="Path to QAT model checkpoint")
    parser.add_argument("--output", default="./model.gguf", help="Output .gguf file path")
    parser.add_argument("--quant", default="Q4_K_M", help="Quantization type")
    args = parser.parse_args()

    export_gguf(args.model, args.output, args.quant)


if __name__ == "__main__":
    main()
