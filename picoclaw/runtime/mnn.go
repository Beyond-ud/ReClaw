package runtime

import (
	"fmt"
	"log"
	"os"
	"os/exec"
	"strings"
)

// MNNRuntime wraps Alibaba's MNN inference engine.
// Optimized for MediaTek and HiSilicon (Kirin) SoCs commonly found
// in budget Android phones (Redmi, Realme, Honor, etc.).
//
// Model format: .mnn (converted from ONNX via MNNConvert)
type MNNRuntime struct {
	binaryPath string
	modelPath  string
	loaded     bool
}

func init() {
	Register(RuntimeMNN, &MNNRuntime{})
}

func (m *MNNRuntime) Name() string {
	return "MNN (Alibaba)"
}

func (m *MNNRuntime) Init(modelPath string, tokenizerPath string) error {
	log.Printf("[mnn] loading model: %s", modelPath)

	m.modelPath = modelPath

	// Find the MNN inference binary
	candidates := []string{
		"/data/local/tmp/mnn_infer",
		"./mnn_infer",
	}
	for _, c := range candidates {
		if _, err := os.Stat(c); err == nil {
			m.binaryPath = c
			break
		}
	}
	if m.binaryPath == "" {
		return fmt.Errorf("mnn inference binary not found")
	}

	if _, err := os.Stat(modelPath); err != nil {
		return fmt.Errorf("model file not found: %s", modelPath)
	}

	m.loaded = true
	log.Printf("[mnn] ready: model=%s", m.modelPath)
	return nil
}

func (m *MNNRuntime) Infer(prompt string, maxTokens int, temperature float64) (string, error) {
	if !m.loaded {
		return "", fmt.Errorf("MNN not initialized")
	}

	cmd := exec.Command(m.binaryPath,
		"--model", m.modelPath,
		"--max-tokens", fmt.Sprintf("%d", maxTokens),
		"--temperature", fmt.Sprintf("%.2f", temperature),
		"--prompt", prompt,
	)

	output, err := cmd.Output()
	if err != nil {
		return "", fmt.Errorf("mnn inference failed: %w", err)
	}

	return strings.TrimSpace(string(output)), nil
}

func (m *MNNRuntime) Close() error {
	m.loaded = false
	log.Println("[mnn] closed")
	return nil
}

func (m *MNNRuntime) IsAvailable() bool {
	candidates := []string{
		"/data/local/tmp/mnn_infer",
		"./mnn_infer",
	}
	for _, c := range candidates {
		if _, err := os.Stat(c); err == nil {
			return true
		}
	}
	return false
}
