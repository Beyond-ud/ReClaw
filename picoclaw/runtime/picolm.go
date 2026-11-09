package runtime

import (
	"fmt"
	"log"
	"os"
	"os/exec"
	"strings"
)

// PicoLMRuntime wraps our forked/customised PicoLM inference engine.
// Designed for ultra-constrained devices with <1GB RAM.
// Uses a custom model format optimized for extreme edge deployment.
//
// PicoLM is a lightweight C inference engine forked from a minimal
// transformer implementation. We've customised it with:
//   - Aggressive memory pooling (no malloc during inference)
//   - Streaming token generation (one token at a time)
//   - INT4-only weight loading (smallest possible footprint)
//   - ARM NEON SIMD optimizations
//
// Model format: custom binary format (.picolm)
type PicoLMRuntime struct {
	binaryPath string
	modelPath  string
	loaded     bool
}

func init() {
	Register(RuntimePicoLM, &PicoLMRuntime{})
}

func (p *PicoLMRuntime) Name() string {
	return "PicoLM (forked/customised)"
}

func (p *PicoLMRuntime) Init(modelPath string, tokenizerPath string) error {
	log.Printf("[picolm] initializing with model: %s", modelPath)

	// PicoLM runs as a separate native binary that we communicate with via stdin/stdout.
	// This keeps the memory footprint isolated and allows aggressive optimization.
	p.modelPath = modelPath

	// Find the PicoLM binary
	candidates := []string{
		"/data/local/tmp/picolm",
		"./picolm",
		"/usr/local/bin/picolm",
	}
	for _, c := range candidates {
		if _, err := os.Stat(c); err == nil {
			p.binaryPath = c
			break
		}
	}

	if p.binaryPath == "" {
		return fmt.Errorf("picolm binary not found")
	}

	// Verify the model file exists
	if _, err := os.Stat(modelPath); err != nil {
		return fmt.Errorf("model file not found: %s", modelPath)
	}

	p.loaded = true
	log.Printf("[picolm] ready: binary=%s model=%s", p.binaryPath, p.modelPath)
	return nil
}

func (p *PicoLMRuntime) Infer(prompt string, maxTokens int, temperature float64) (string, error) {
	if !p.loaded {
		return "", fmt.Errorf("PicoLM not initialized")
	}

	// Run PicoLM as a subprocess for memory isolation.
	// On ultra-constrained devices, this prevents the Go runtime's memory
	// overhead from competing with the model's memory needs.
	cmd := exec.Command(p.binaryPath,
		"--model", p.modelPath,
		"--max-tokens", fmt.Sprintf("%d", maxTokens),
		"--temperature", fmt.Sprintf("%.2f", temperature),
		"--prompt", prompt,
	)

	output, err := cmd.Output()
	if err != nil {
		return "", fmt.Errorf("picolm inference failed: %w", err)
	}

	result := strings.TrimSpace(string(output))
	return result, nil
}

func (p *PicoLMRuntime) Close() error {
	p.loaded = false
	log.Println("[picolm] closed")
	return nil
}

func (p *PicoLMRuntime) IsAvailable() bool {
	// Check if PicoLM binary exists
	candidates := []string{
		"/data/local/tmp/picolm",
		"./picolm",
	}
	for _, c := range candidates {
		if _, err := os.Stat(c); err == nil {
			return true
		}
	}
	return false
}
