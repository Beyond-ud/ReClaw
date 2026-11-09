package runtime

import (
	"log"
	"os"
	"runtime"
	"strconv"
	"strings"
)

// DeviceProfile holds hardware and OS info gathered during device benchmarking.
// PicoClaw probes the device on first run to build this profile, which is then
// used by SelectBestRuntime() to pick the optimal inference backend.
type DeviceProfile struct {
	// Hardware
	RAMMb         int    // Total RAM in megabytes
	Arch          string // CPU architecture (arm64, arm, x86_64)
	SoCVendor     string // qualcomm, mediatek, hisilicon, samsung, etc.
	SoCModel      string // Full SoC model string from /proc/cpuinfo
	CPUCores      int    // Number of CPU cores
	HasGPUDelegate bool  // Whether GPU compute (OpenCL/Vulkan) is available

	// Android
	AndroidAPI    int    // Android API level (e.g., 24 for Android 7)
	AndroidVersion string // Human-readable version (e.g., "12")

	// Filesystem
	AvailStorageMB int // Available storage on /data partition
}

// BenchmarkDevice probes the current device and returns a DeviceProfile.
// This runs on first launch and the result is cached in picoclaw.json
// so subsequent boots are instant.
func BenchmarkDevice() DeviceProfile {
	p := DeviceProfile{
		Arch:     runtime.GOARCH,
		CPUCores: runtime.NumCPU(),
	}

	// Probe total RAM from /proc/meminfo
	p.RAMMb = probeRAM()

	// Probe SoC from /proc/cpuinfo
	p.SoCVendor, p.SoCModel = probeSoC()

	// Probe Android version from system properties
	p.AndroidAPI, p.AndroidVersion = probeAndroid()

	// Check GPU delegate availability
	p.HasGPUDelegate = probeGPU()

	// Check available storage
	p.AvailStorageMB = probeStorage()

	log.Printf("[benchmark] device profile: %+v", p)
	return p
}

// probeRAM reads total memory from /proc/meminfo.
func probeRAM() int {
	data, err := os.ReadFile("/proc/meminfo")
	if err != nil {
		log.Printf("[benchmark] cannot read /proc/meminfo: %v", err)
		return 1024 // assume 1GB if unknown
	}
	for _, line := range strings.Split(string(data), "\n") {
		if strings.HasPrefix(line, "MemTotal:") {
			fields := strings.Fields(line)
			if len(fields) >= 2 {
				kb, _ := strconv.Atoi(fields[1])
				return kb / 1024
			}
		}
	}
	return 1024
}

// probeSoC extracts the SoC vendor and model from /proc/cpuinfo.
func probeSoC() (vendor, model string) {
	data, err := os.ReadFile("/proc/cpuinfo")
	if err != nil {
		return "unknown", "unknown"
	}
	content := strings.ToLower(string(data))

	// Extract hardware line
	for _, line := range strings.Split(content, "\n") {
		if strings.HasPrefix(line, "hardware") {
			parts := strings.SplitN(line, ":", 2)
			if len(parts) == 2 {
				model = strings.TrimSpace(parts[1])
			}
		}
	}

	// Determine vendor from known patterns
	switch {
	case strings.Contains(content, "qualcomm") || strings.Contains(content, "snapdragon"):
		vendor = "qualcomm"
	case strings.Contains(content, "mediatek") || strings.Contains(content, "mt6"):
		vendor = "mediatek"
	case strings.Contains(content, "hisilicon") || strings.Contains(content, "kirin"):
		vendor = "hisilicon"
	case strings.Contains(content, "exynos") || strings.Contains(content, "samsung"):
		vendor = "samsung"
	case strings.Contains(content, "tensor"):
		vendor = "google"
	default:
		vendor = "unknown"
	}

	if model == "" {
		model = "unknown"
	}
	return vendor, model
}

// probeAndroid reads Android API level and version from system properties.
// On a real Android device these come from `getprop`. When running in proot
// or Termux, we fall back to environment variables.
func probeAndroid() (apiLevel int, version string) {
	// Try reading from build.prop (available on Android)
	data, err := os.ReadFile("/system/build.prop")
	if err != nil {
		// Fallback: try getprop-style env vars (Termux sets some of these)
		if v := os.Getenv("ANDROID_API"); v != "" {
			apiLevel, _ = strconv.Atoi(v)
		}
		return apiLevel, ""
	}

	for _, line := range strings.Split(string(data), "\n") {
		line = strings.TrimSpace(line)
		if strings.HasPrefix(line, "ro.build.version.sdk=") {
			apiLevel, _ = strconv.Atoi(strings.TrimPrefix(line, "ro.build.version.sdk="))
		}
		if strings.HasPrefix(line, "ro.build.version.release=") {
			version = strings.TrimPrefix(line, "ro.build.version.release=")
		}
	}
	return apiLevel, version
}

// probeGPU checks for GPU compute availability (OpenCL/Vulkan libraries).
func probeGPU() bool {
	gpuLibs := []string{
		"/system/lib64/libOpenCL.so",
		"/system/vendor/lib64/libOpenCL.so",
		"/system/lib64/libvulkan.so",
	}
	for _, lib := range gpuLibs {
		if _, err := os.Stat(lib); err == nil {
			return true
		}
	}
	return false
}

// probeStorage checks available storage in the data partition.
func probeStorage() int {
	// Simplified: read /proc/mounts to find /data and estimate.
	// In production, we'd use syscall.Statfs.
	// For now, return a reasonable default.
	return 2048 // 2GB assumed
}
