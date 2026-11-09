#!/usr/bin/env python3
"""
ReClaw QAT Fine-Tuning Script — PyTorch + TorchAO

Quantization-Aware Training for on-device SLM deployment (default: Qwen3-0.6B).
No vendor lock-in. Pure PyTorch + TorchAO for framework-agnostic QAT.
Supports any HuggingFace causal LM via the --model flag.

Pipeline:
  1. Load base model (default: Qwen3-0.6B, configurable via --model)
  2. Apply INT8 dynamic activation + INT4 weight QAT via TorchAO
  3. Fine-tune on curated ReClaw dataset (1,700+ examples)
  4. Save QAT checkpoint for multi-format export

Usage (Colab T4 GPU):
  !pip install torch torchao transformers datasets accelerate
  !python ReClaw_QAT_Finetune.py --dataset ./dataset/ --output ./output/

Environment:
  - Google Colab T4 GPU (free tier sufficient)
  - PyTorch 2.4+
  - TorchAO latest
  - ~4GB VRAM required for Qwen3-0.6B QAT
"""

import argparse
import json
import os
import glob
from pathlib import Path

import torch
from torch.utils.data import Dataset, DataLoader

# ── These imports require the packages to be installed ──
# In Colab: !pip install torch torchao transformers datasets
try:
    from transformers import AutoModelForCausalLM, AutoTokenizer, get_scheduler
    from torchao.quantization import quantize_, int8_dynamic_activation_int4_weight
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False
    print("⚠️  Dependencies not installed. Run:")
    print("   pip install torch torchao transformers datasets accelerate")


# ══════════════════════════════════════════════════════════
#  Dataset
# ══════════════════════════════════════════════════════════

class ReClawDataset(Dataset):
    """Load curated JSONL training data in Alpaca instruction format.

    Each line in the JSONL files has:
        {"instruction": "...", "output": "..."}

    Tool calls in the output are formatted as:
        [CALL tool.name(args)] Human-readable confirmation.
    """

    def __init__(self, data_dir: str, tokenizer, max_length: int = 512):
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.examples = []

        # Load all JSONL files from the dataset directory
        jsonl_files = glob.glob(os.path.join(data_dir, "*.jsonl"))
        for filepath in sorted(jsonl_files):
            with open(filepath, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            example = json.loads(line)
                            self.examples.append(example)
                        except json.JSONDecodeError:
                            continue

        print(f"📊 Loaded {len(self.examples)} training examples from {len(jsonl_files)} files")

    def __len__(self):
        return len(self.examples)

    def __getitem__(self, idx):
        example = self.examples[idx]

        # Format as instruction-following prompt
        prompt = self._format_prompt(example["instruction"], example["output"])

        # Tokenize
        encoding = self.tokenizer(
            prompt,
            truncation=True,
            max_length=self.max_length,
            padding="max_length",
            return_tensors="pt",
        )

        input_ids = encoding["input_ids"].squeeze()
        attention_mask = encoding["attention_mask"].squeeze()

        return {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "labels": input_ids.clone(),  # Causal LM: labels = input_ids
        }

    @staticmethod
    def _format_prompt(instruction: str, output: str) -> str:
        """Format as a chat-style prompt for Qwen3."""
        return (
            f"<|im_start|>system\n"
            f"You are ReClaw, an AI assistant running on an old Android phone. "
            f"You control device settings and help the user with daily tasks. "
            f"Use [CALL tool.name(args)] to invoke device tools.<|im_end|>\n"
            f"<|im_start|>user\n{instruction}<|im_end|>\n"
            f"<|im_start|>assistant\n{output}<|im_end|>"
        )


# ══════════════════════════════════════════════════════════
#  QAT Fine-Tuning
# ══════════════════════════════════════════════════════════

def apply_qat(model):
    """Apply Quantization-Aware Training using TorchAO.

    Uses INT8 dynamic activation + INT4 weight quantization.
    This inserts fake-quantization nodes during training so the
    model learns to be robust to quantization noise.

    Key advantage over post-training quantization (PTQ):
      - Recovers ~70% of accuracy lost by naive PTQ
      - Same checkpoint exports to all runtime formats
    """
    print("🔧 Applying QAT: INT8 dynamic activation + INT4 weight...")

    # TorchAO's quantize_ modifies the model in-place,
    # inserting fake-quant observers for QAT
    quantize_(model, int8_dynamic_activation_int4_weight())

    print("✅ QAT applied successfully")
    return model


def train(
    model,
    tokenizer,
    dataset: ReClawDataset,
    output_dir: str,
    epochs: int = 3,
    batch_size: int = 4,
    learning_rate: float = 2e-5,
    warmup_steps: int = 100,
):
    """Fine-tune the QAT model on the ReClaw dataset."""

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"🖥️  Training device: {device}")

    model = model.to(device)
    model.train()

    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=0.01)
    num_training_steps = len(dataloader) * epochs
    scheduler = get_scheduler(
        "cosine",
        optimizer=optimizer,
        num_warmup_steps=warmup_steps,
        num_training_steps=num_training_steps,
    )

    print(f"🏋️ Training config:")
    print(f"   Epochs:          {epochs}")
    print(f"   Batch size:      {batch_size}")
    print(f"   Learning rate:   {learning_rate}")
    print(f"   Training steps:  {num_training_steps}")
    print(f"   Warmup steps:    {warmup_steps}")
    print(f"   Dataset size:    {len(dataset)}")
    print()

    global_step = 0
    for epoch in range(epochs):
        epoch_loss = 0.0
        for step, batch in enumerate(dataloader):
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["labels"].to(device)

            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                labels=labels,
            )
            loss = outputs.loss

            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
            optimizer.zero_grad()

            epoch_loss += loss.item()
            global_step += 1

            if step % 50 == 0:
                print(f"  Epoch {epoch+1}/{epochs} | Step {step}/{len(dataloader)} | "
                      f"Loss: {loss.item():.4f} | LR: {scheduler.get_last_lr()[0]:.2e}")

        avg_loss = epoch_loss / len(dataloader)
        print(f"📈 Epoch {epoch+1} complete | Avg Loss: {avg_loss:.4f}")

        # Save checkpoint after each epoch
        checkpoint_dir = os.path.join(output_dir, f"checkpoint-epoch-{epoch+1}")
        os.makedirs(checkpoint_dir, exist_ok=True)
        model.save_pretrained(checkpoint_dir)
        tokenizer.save_pretrained(checkpoint_dir)
        print(f"💾 Saved checkpoint: {checkpoint_dir}")

    # Save final model
    final_dir = os.path.join(output_dir, "final")
    os.makedirs(final_dir, exist_ok=True)
    model.save_pretrained(final_dir)
    tokenizer.save_pretrained(final_dir)
    print(f"\n✅ Training complete! Final model: {final_dir}")

    return model


# ══════════════════════════════════════════════════════════
#  Main
# ══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="ReClaw QAT Fine-Tuning")
    parser.add_argument("--model", default="Qwen/Qwen3-0.6B",
                        help="Base model name or path")
    parser.add_argument("--dataset", default="./dataset/",
                        help="Path to JSONL dataset directory")
    parser.add_argument("--output", default="./output/",
                        help="Output directory for checkpoints")
    parser.add_argument("--epochs", type=int, default=3,
                        help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=4,
                        help="Training batch size")
    parser.add_argument("--lr", type=float, default=2e-5,
                        help="Learning rate")
    parser.add_argument("--max-length", type=int, default=512,
                        help="Max sequence length")
    args = parser.parse_args()

    if not HAS_DEPS:
        print("❌ Missing dependencies. Install them first.")
        return

    print("🦞 ReClaw QAT Fine-Tuning")
    print("═══════════════════════════════════════")
    print(f"  Base model:  {args.model}")
    print(f"  Dataset:     {args.dataset}")
    print(f"  Output:      {args.output}")
    print("═══════════════════════════════════════")

    # Load tokenizer and model
    print("\n📥 Loading base model...")
    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        torch_dtype=torch.float32,  # QAT requires FP32 for fake-quant
        trust_remote_code=True,
    )

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Apply QAT
    model = apply_qat(model)

    # Load dataset
    print("\n📊 Loading dataset...")
    dataset = ReClawDataset(args.dataset, tokenizer, max_length=args.max_length)

    if len(dataset) == 0:
        print("❌ No training examples found. Check dataset directory.")
        return

    # Train
    print("\n🏋️ Starting fine-tuning...")
    train(
        model=model,
        tokenizer=tokenizer,
        dataset=dataset,
        output_dir=args.output,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
    )

    print("\n🎉 Done! Next steps:")
    print(f"  1. Export to ExecuTorch: python export_pte.py --model {args.output}/final")
    print(f"  2. Export to GGUF:       python export_gguf.py --model {args.output}/final")
    print(f"  3. Export to TFLite:     python export_tflite.py --model {args.output}/final")


if __name__ == "__main__":
    main()
