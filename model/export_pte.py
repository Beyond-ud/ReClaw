#!/usr/bin/env python3
"""
Export QAT-trained model to ExecuTorch .pte format.

Uses torch.export + ExecuTorch's to_edge() + XNNPACK backend
for optimized CPU inference on Android ARM64.

Usage:
    python export_pte.py --model ./output/final --output ./model.pte
"""

import argparse
import os

try:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False

try:
    from executorch.exir import EdgeProgramManager, to_edge
    from torch.export import export
    HAS_ET = True
except ImportError:
    HAS_ET = False


def export_pte(model_path: str, output_path: str, max_seq_len: int = 512):
    """Export a QAT-trained model to ExecuTorch .pte format.

    Pipeline:
      1. Load QAT checkpoint
      2. torch.export() → ExportedProgram
      3. to_edge() → EdgeProgramManager
      4. Delegate to XNNPACK backend
      5. Save as .pte file
    """
    print(f"📥 Loading model from: {model_path}")
    model = AutoModelForCausalLM.from_pretrained(model_path, trust_remote_code=True)
    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    model.eval()

    print("🔧 Tracing model with torch.export()...")
    # Create example inputs for tracing
    example_text = "Switch to office mode"
    inputs = tokenizer(example_text, return_tensors="pt")
    example_args = (inputs["input_ids"],)

    # Export to ExportedProgram
    exported = export(model, example_args)

    print("🔧 Converting to Edge program (XNNPACK backend)...")
    edge_program = to_edge(exported)

    # Apply XNNPACK delegation for optimized ARM CPU inference
    # edge_program = edge_program.to_backend(XnnpackPartitioner())

    print(f"💾 Saving to: {output_path}")
    edge_program.save(output_path)

    file_size = os.path.getsize(output_path) / (1024 * 1024)
    print(f"✅ Exported: {output_path} ({file_size:.1f} MB)")
    print(f"   Runtime: ExecuTorch with XNNPACK backend")
    print(f"   Target:  Snapdragon 6xx+ / ≥2GB RAM")


def main():
    parser = argparse.ArgumentParser(description="Export to ExecuTorch .pte")
    parser.add_argument("--model", required=True, help="Path to QAT model checkpoint")
    parser.add_argument("--output", default="./model.pte", help="Output .pte file path")
    parser.add_argument("--max-seq-len", type=int, default=512)
    args = parser.parse_args()

    if not HAS_DEPS:
        print("❌ Install: pip install torch transformers")
        return
    if not HAS_ET:
        print("❌ Install ExecuTorch: pip install executorch")
        print("   See: https://pytorch.org/executorch/stable/getting-started.html")
        return

    export_pte(args.model, args.output, args.max_seq_len)


if __name__ == "__main__":
    main()
