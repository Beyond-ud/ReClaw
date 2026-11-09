package runtime

/*
#cgo LDFLAGS: -lexecutorch -lxnnpack
#include <stdlib.h>

// ExecuTorch C API bindings (simplified)
// In production, these link against the ExecuTorch shared library
// built for Android ARM64 via the ExecuTorch CMake build system.

typedef void* ETModel;
extern ETModel et_load_model(const char* path);
extern const char* et_infer(ETModel model, const char* prompt, int max_tokens, float temperature);
extern void et_free_model(ETModel model);
*/
import "C"

import (
	"fmt"
	"log"
	"os"
	"unsafe"
)

// ExecuTorchRuntime wraps Meta's ExecuTorch inference engine.
// Best suited for newer Snapdragon 6xx+ devices with ≥2GB RAM.
// Uses the XNNPACK backend for optimized CPU inference.
//
// Model format: .pte (exported via torch.export + ExecuTorch)
type ExecuTorchRuntime struct {
	model   C.ETModel
	loaded  bool
}

func init() {
	Register(RuntimeExecuTorch, &ExecuTorchRuntime{})
}

func (e *ExecuTorchRuntime) Name() string {
	return "ExecuTorch (XNNPACK)"
}

func (e *ExecuTorchRuntime) Init(modelPath string, tokenizerPath string) error {
	log.Printf("[executorch] loading model: %s", modelPath)

	cPath := C.CString(modelPath)
	defer C.free(unsafe.Pointer(cPath))

	e.model = C.et_load_model(cPath)
	if e.model == nil {
		return fmt.Errorf("failed to load ExecuTorch model from %s", modelPath)
	}
	e.loaded = true
	log.Println("[executorch] model loaded successfully")
	return nil
}

func (e *ExecuTorchRuntime) Infer(prompt string, maxTokens int, temperature float64) (string, error) {
	if !e.loaded {
		return "", fmt.Errorf("model not loaded")
	}

	cPrompt := C.CString(prompt)
	defer C.free(unsafe.Pointer(cPrompt))

	result := C.et_infer(e.model, cPrompt, C.int(maxTokens), C.float(temperature))
	if result == nil {
		return "", fmt.Errorf("inference failed")
	}
	return C.GoString(result), nil
}

func (e *ExecuTorchRuntime) Close() error {
	if e.loaded {
		C.et_free_model(e.model)
		e.loaded = false
		log.Println("[executorch] model unloaded")
	}
	return nil
}

func (e *ExecuTorchRuntime) IsAvailable() bool {
	// Check if ExecuTorch shared library exists on the device
	libs := []string{
		"/data/local/tmp/lib/libexecutorch.so",
		"/system/lib64/libexecutorch.so",
	}
	for _, lib := range libs {
		if _, err := os.Stat(lib); err == nil {
			return true
		}
	}
	return false
}
