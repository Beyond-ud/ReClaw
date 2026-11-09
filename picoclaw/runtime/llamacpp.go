package runtime

/*
#cgo LDFLAGS: -lllama -lggml
#include <stdlib.h>

// llama.cpp C API bindings (simplified)
// Links against the llama.cpp shared library built for Android ARM64.
// Uses GGUF model format with Q4_K_M quantization.

typedef void* LlamaModel;
typedef void* LlamaContext;
extern LlamaModel llama_load_model(const char* path);
extern LlamaContext llama_new_context(LlamaModel model);
extern const char* llama_generate(LlamaContext ctx, const char* prompt, int max_tokens, float temperature);
extern void llama_free_context(LlamaContext ctx);
extern void llama_free_model(LlamaModel model);
*/
import "C"

import (
	"fmt"
	"log"
	"os"
	"unsafe"
)

// LlamaCppRuntime wraps the llama.cpp inference engine.
// Broad ARM64 compatibility — works on most Android 7+ devices with ≥1.5GB RAM.
// Mature ecosystem with wide model support and easy quantization.
//
// Model format: .gguf (Q4_K_M quantization recommended)
type LlamaCppRuntime struct {
	model   C.LlamaModel
	ctx     C.LlamaContext
	loaded  bool
}

func init() {
	Register(RuntimeLlamaCpp, &LlamaCppRuntime{})
}

func (l *LlamaCppRuntime) Name() string {
	return "llama.cpp (GGUF)"
}

func (l *LlamaCppRuntime) Init(modelPath string, tokenizerPath string) error {
	log.Printf("[llamacpp] loading GGUF model: %s", modelPath)

	cPath := C.CString(modelPath)
	defer C.free(unsafe.Pointer(cPath))

	l.model = C.llama_load_model(cPath)
	if l.model == nil {
		return fmt.Errorf("failed to load GGUF model from %s", modelPath)
	}

	l.ctx = C.llama_new_context(l.model)
	if l.ctx == nil {
		C.llama_free_model(l.model)
		return fmt.Errorf("failed to create llama.cpp context")
	}

	l.loaded = true
	log.Println("[llamacpp] model loaded successfully (GGUF Q4_K_M)")
	return nil
}

func (l *LlamaCppRuntime) Infer(prompt string, maxTokens int, temperature float64) (string, error) {
	if !l.loaded {
		return "", fmt.Errorf("model not loaded")
	}

	cPrompt := C.CString(prompt)
	defer C.free(unsafe.Pointer(cPrompt))

	result := C.llama_generate(l.ctx, cPrompt, C.int(maxTokens), C.float(temperature))
	if result == nil {
		return "", fmt.Errorf("inference failed")
	}
	return C.GoString(result), nil
}

func (l *LlamaCppRuntime) Close() error {
	if l.loaded {
		C.llama_free_context(l.ctx)
		C.llama_free_model(l.model)
		l.loaded = false
		log.Println("[llamacpp] model unloaded")
	}
	return nil
}

func (l *LlamaCppRuntime) IsAvailable() bool {
	// llama.cpp is statically linked — always available if compiled in.
	// Check for the GGUF model file as a proxy.
	paths := []string{
		"/data/local/tmp/llama/model.gguf",
		"./model.gguf",
	}
	for _, p := range paths {
		if _, err := os.Stat(p); err == nil {
			return true
		}
	}
	return false
}
