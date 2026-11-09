package runtime

import (
	"fmt"
	"log"
	"os"
	"os/exec"
	"strings"
)

// LiteRTRuntime wraps Google's LiteRT (formerly TensorFlow Lite) engine.
// Best for devices with GPU delegate support (OpenCL/Vulkan).
// Uses .tflite model format with optional GPU acceleration.
//
// Model format: .tflite (converted from PyTorch via ai_edge_torch)
type LiteRTRuntime struct {
	binaryPath string
	modelPath  string
	useGPU     bool
	loaded     bool
}

func init() {
	Register(RuntimeLiteRT, &LiteRTRuntime{})
}

func (l *LiteRTRuntime) Name() string {
	if l.useGPU {
		return "LiteRT (GPU delegate)"
	}
	return "LiteRT (CPU)"
}

func (l *LiteRTRuntime) Init(modelPath string, tokenizerPath string) error {
	log.Printf("[litert] loading model: %s", modelPath)

	// Check for GPU delegate availability
	l.useGPU = probeGPU()
	if l.useGPU {
		log.Println("[litert] GPU delegate available — enabling hardware acceleration")
	}

	l.modelPath = modelPath

	// Find the LiteRT inference binary
	candidates := []string{
		"/data/local/tmp/litert_infer",
		"./litert_infer",
	}
	for _, c := range candidates {
		if _, err := os.Stat(c); err == nil {
			l.binaryPath = c
			break
		}
	}
	if l.binaryPath == "" {
		return fmt.Errorf("litert inference binary not found")
	}

	if _, err := os.Stat(modelPath); err != nil {
		return fmt.Errorf("model file not found: %s", modelPath)
	}

	l.loaded = true
	log.Printf("[litert] ready: gpu=%v model=%s", l.useGPU, l.modelPath)
	return nil
}

func (l *LiteRTRuntime) Infer(prompt string, maxTokens int, temperature float64) (string, error) {
	if !l.loaded {
		return "", fmt.Errorf("LiteRT not initialized")
	}

	args := []string{
		"--model", l.modelPath,
		"--max-tokens", fmt.Sprintf("%d", maxTokens),
		"--temperature", fmt.Sprintf("%.2f", temperature),
		"--prompt", prompt,
	}
	if l.useGPU {
		args = append(args, "--gpu")
	}

	cmd := exec.Command(l.binaryPath, args...)
	output, err := cmd.Output()
	if err != nil {
		return "", fmt.Errorf("litert inference failed: %w", err)
	}

	return strings.TrimSpace(string(output)), nil
}

func (l *LiteRTRuntime) Close() error {
	l.loaded = false
	log.Println("[litert] closed")
	return nil
}

func (l *LiteRTRuntime) IsAvailable() bool {
	candidates := []string{
		"/data/local/tmp/litert_infer",
		"./litert_infer",
	}
	for _, c := range candidates {
		if _, err := os.Stat(c); err == nil {
			return true
		}
	}
	return false
}
