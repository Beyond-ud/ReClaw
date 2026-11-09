// Package runtime provides adaptive multi-runtime inference for PicoClaw.
//
// PicoClaw does NOT lock into a single inference backend. On first launch,
// it benchmarks the device (RAM, SoC, Android version, available acceleration)
// to determine the best runtime. Supported backends:
//
//   - ExecuTorch (.pte)       — Snapdragon 6xx+, XNNPACK
//   - llama.cpp   (.gguf)     — Broad ARM64 compatibility
//   - PicoLM      (custom)    — Ultra-constrained (<1GB RAM)
//   - LiteRT      (.tflite)   — GPU delegate devices
//   - MNN         (.mnn)      — MediaTek/Kirin SoCs
package runtime

import (
	"fmt"
	"log"
)

// InferenceRuntime is the interface every backend must implement.
// This abstraction lets PicoClaw swap runtimes transparently.
type InferenceRuntime interface {
	// Name returns the human-readable runtime name.
	Name() string

	// Init loads the model from the given path and prepares for inference.
	Init(modelPath string, tokenizerPath string) error

	// Infer runs a single forward pass: prompt → generated text.
	Infer(prompt string, maxTokens int, temperature float64) (string, error)

	// Close releases all resources held by the runtime.
	Close() error

	// IsAvailable checks whether this runtime can work on the current device.
	// It should return false if required libraries or hardware are missing.
	IsAvailable() bool
}

// RuntimeID identifies a supported inference backend.
type RuntimeID string

const (
	RuntimeExecuTorch RuntimeID = "executorch"
	RuntimeLlamaCpp   RuntimeID = "llamacpp"
	RuntimePicoLM     RuntimeID = "picolm"
	RuntimeLiteRT     RuntimeID = "litert"
	RuntimeMNN        RuntimeID = "mnn"
)

// registry holds all registered runtimes.
var registry = map[RuntimeID]InferenceRuntime{}

// Register adds a runtime to the global registry. Called by each backend's
// init() function so runtimes are available at startup.
func Register(id RuntimeID, rt InferenceRuntime) {
	registry[id] = rt
	log.Printf("[runtime] registered backend: %s", id)
}

// SelectBestRuntime benchmarks the device and returns the most suitable
// runtime from the registered backends. This is the core of PicoClaw's
// adaptive multi-runtime strategy.
//
// Selection priority (highest to lowest):
//  1. ExecuTorch  — if Snapdragon 6xx+ and ≥2GB RAM
//  2. llama.cpp   — if general ARM64 and ≥1.5GB RAM
//  3. MNN         — if MediaTek/Kirin SoC detected
//  4. LiteRT      — if GPU delegate available
//  5. PicoLM      — fallback for ultra-constrained devices
func SelectBestRuntime(supported []RuntimeID) (InferenceRuntime, RuntimeID, error) {
	profile := BenchmarkDevice()
	log.Printf("[runtime] device profile: RAM=%dMB SoC=%s Android=%d Arch=%s",
		profile.RAMMb, profile.SoCVendor, profile.AndroidAPI, profile.Arch)

	// Score each supported runtime against the device profile
	type scored struct {
		id    RuntimeID
		rt    InferenceRuntime
		score int
	}
	var candidates []scored

	for _, id := range supported {
		rt, ok := registry[id]
		if !ok {
			log.Printf("[runtime] backend %s not registered, skipping", id)
			continue
		}
		if !rt.IsAvailable() {
			log.Printf("[runtime] backend %s not available on device, skipping", id)
			continue
		}
		score := scoreRuntime(id, profile)
		candidates = append(candidates, scored{id, rt, score})
		log.Printf("[runtime] backend %s scored %d", id, score)
	}

	if len(candidates) == 0 {
		return nil, "", fmt.Errorf("no compatible runtime found for device (RAM=%dMB, SoC=%s)",
			profile.RAMMb, profile.SoCVendor)
	}

	// Pick the highest-scoring runtime
	best := candidates[0]
	for _, c := range candidates[1:] {
		if c.score > best.score {
			best = c
		}
	}

	log.Printf("[runtime] ✅ selected runtime: %s (score=%d)", best.id, best.score)
	return best.rt, best.id, nil
}

// scoreRuntime assigns a suitability score to a runtime for the given device.
func scoreRuntime(id RuntimeID, p DeviceProfile) int {
	score := 0

	switch id {
	case RuntimeExecuTorch:
		// Best for newer Snapdragon with good RAM
		if p.SoCVendor == "qualcomm" && p.RAMMb >= 2048 {
			score = 100
		} else if p.RAMMb >= 2048 {
			score = 70
		} else {
			score = 30
		}

	case RuntimeLlamaCpp:
		// Broad compatibility, solid on most ARM64
		if p.RAMMb >= 1536 {
			score = 80
		} else if p.RAMMb >= 1024 {
			score = 50
		} else {
			score = 20
		}

	case RuntimePicoLM:
		// Designed for ultra-constrained devices
		if p.RAMMb < 1024 {
			score = 90 // Best option for low RAM
		} else {
			score = 40
		}

	case RuntimeLiteRT:
		// GPU delegate gives a boost
		if p.HasGPUDelegate {
			score = 85
		} else {
			score = 45
		}

	case RuntimeMNN:
		// Optimized for MediaTek/Kirin
		if p.SoCVendor == "mediatek" || p.SoCVendor == "hisilicon" {
			score = 95
		} else {
			score = 35
		}
	}

	return score
}

// Get returns a runtime by ID from the registry, or nil if not found.
func Get(id RuntimeID) InferenceRuntime {
	return registry[id]
}

// Available returns the IDs of all registered and device-compatible runtimes.
func Available() []RuntimeID {
	var ids []RuntimeID
	for id, rt := range registry {
		if rt.IsAvailable() {
			ids = append(ids, id)
		}
	}
	return ids
}
