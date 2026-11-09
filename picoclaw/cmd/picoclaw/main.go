// PicoClaw — Lightweight AI agent runtime for old Android phones.
//
// Natively compiled via Android NDK as an ARM binary. No Go/Termux
// dependency at runtime — just the binary + model + skills.
//
// Usage:
//
//	picoclaw start --config ./picoclaw.json --skills ./skills/
//	picoclaw benchmark          # probe device and show recommended runtime
//	picoclaw version
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"

	"github.com/team-reclaw/reclaw/picoclaw/runtime"
)

// Version is set at build time via -ldflags.
var Version = "dev"

// Config mirrors config/picoclaw.json.
type Config struct {
	Agent struct {
		Model             string            `json:"model"`
		Engine            string            `json:"engine"` // "auto" or specific runtime
		BenchmarkOnFirst  bool              `json:"benchmark_on_first_run"`
		SupportedRuntimes []string          `json:"supported_runtimes"`
		ModelPaths        map[string]string `json:"model_paths"`
		TokenizerPath     string            `json:"tokenizer_path"`
		ModelType         string            `json:"model_type"`
		MaxTokens         int               `json:"max_tokens"`
		Temperature       float64           `json:"temperature"`
	} `json:"agent"`

	Channels struct {
		Telegram struct {
			BotToken  string   `json:"botToken"`
			AllowFrom []string `json:"allowFrom"`
			DMPolicy  string   `json:"dmPolicy"`
		} `json:"telegram"`
	} `json:"channels"`

	MasterSlave struct {
		Enabled             bool   `json:"enabled"`
		Role                string `json:"role"` // "master" or "slave"
		MasterChatID        string `json:"master_chat_id"`
		SyncIntervalSeconds int    `json:"sync_interval_s"`
		AllowRemoteOverride bool   `json:"allow_remote_override"`
	} `json:"master_slave"`

	Skills struct {
		Directory string   `json:"directory"`
		Enabled   []string `json:"enabled"`
	} `json:"skills"`

	Memory struct {
		Enabled  bool   `json:"enabled"`
		Store    string `json:"store"`
		AutoSave bool   `json:"auto_save"`
	} `json:"memory"`

	Proot struct {
		Enabled bool   `json:"enabled"`
		Distro  string `json:"distro"`
		Note    string `json:"note"`
	} `json:"proot"`

	Cron struct {
		Enabled bool `json:"enabled"`
		Jobs    []struct {
			Name     string            `json:"name"`
			Schedule string            `json:"schedule"`
			Skill    string            `json:"skill"`
			Action   string            `json:"action"`
			Args     map[string]string `json:"args,omitempty"`
		} `json:"jobs"`
	} `json:"cron"`
}

func main() {
	// Subcommands
	if len(os.Args) > 1 {
		switch os.Args[1] {
		case "version":
			fmt.Printf("picoclaw %s\n", Version)
			return
		case "benchmark":
			cmdBenchmark()
			return
		case "start":
			// continue below
		default:
			fmt.Fprintf(os.Stderr, "Unknown command: %s\nUsage: picoclaw [start|benchmark|version]\n", os.Args[1])
			os.Exit(1)
		}
	}

	// Parse flags for 'start'
	startCmd := flag.NewFlagSet("start", flag.ExitOnError)
	configPath := startCmd.String("config", "./picoclaw.json", "Path to picoclaw.json config")
	skillsDir := startCmd.String("skills", "./skills/", "Path to skills directory")
	startCmd.Parse(os.Args[2:])

	log.Println("🦞 PicoClaw starting...")
	log.Printf("   Version:  %s", Version)
	log.Printf("   Config:   %s", *configPath)
	log.Printf("   Skills:   %s", *skillsDir)

	// ── Load config ──
	cfg, err := loadConfig(*configPath)
	if err != nil {
		log.Fatalf("❌ Failed to load config: %v", err)
	}
	log.Printf("   Model:    %s", cfg.Agent.Model)
	log.Printf("   Engine:   %s", cfg.Agent.Engine)

	// ── Device benchmark & runtime selection ──
	var selectedRT runtime.InferenceRuntime
	var selectedID runtime.RuntimeID

	if cfg.Agent.Engine == "auto" {
		log.Println("🔍 Engine set to 'auto' — benchmarking device...")
		supported := make([]runtime.RuntimeID, len(cfg.Agent.SupportedRuntimes))
		for i, s := range cfg.Agent.SupportedRuntimes {
			supported[i] = runtime.RuntimeID(s)
		}
		selectedRT, selectedID, err = runtime.SelectBestRuntime(supported)
		if err != nil {
			log.Fatalf("❌ No compatible runtime: %v", err)
		}
	} else {
		selectedID = runtime.RuntimeID(cfg.Agent.Engine)
		selectedRT = runtime.Get(selectedID)
		if selectedRT == nil {
			log.Fatalf("❌ Runtime '%s' not found in registry", cfg.Agent.Engine)
		}
	}
	log.Printf("✅ Runtime selected: %s (%s)", selectedID, selectedRT.Name())

	// ── Initialize model ──
	modelPath := cfg.Agent.ModelPaths[string(selectedID)]
	if modelPath == "" {
		log.Fatalf("❌ No model_path configured for runtime '%s'", selectedID)
	}
	if err := selectedRT.Init(modelPath, cfg.Agent.TokenizerPath); err != nil {
		log.Fatalf("❌ Failed to initialize model: %v", err)
	}
	defer selectedRT.Close()
	log.Printf("🧠 Model loaded: %s → %s", cfg.Agent.Model, modelPath)

	// ── Load skills ──
	skills := loadSkills(*skillsDir, cfg.Skills.Enabled)
	log.Printf("📦 Loaded %d skills: %v", len(skills), cfg.Skills.Enabled)

	// ── Load memory store ──
	if cfg.Memory.Enabled {
		log.Printf("💾 Memory store: %s (auto_save=%v)", cfg.Memory.Store, cfg.Memory.AutoSave)
	}

	// ── Master-Slave setup ──
	if cfg.MasterSlave.Enabled {
		log.Printf("🔗 Master-Slave: role=%s, master=%s, sync=%ds",
			cfg.MasterSlave.Role, cfg.MasterSlave.MasterChatID,
			cfg.MasterSlave.SyncIntervalSeconds)
	}

	// ── Start cron scheduler ──
	if cfg.Cron.Enabled {
		log.Printf("⏰ Cron scheduler: %d jobs registered", len(cfg.Cron.Jobs))
		for _, job := range cfg.Cron.Jobs {
			log.Printf("   • %s → %s.%s @ %s", job.Name, job.Skill, job.Action, job.Schedule)
		}
		go startCronScheduler(cfg, skills, selectedRT)
	}

	// ── Start Telegram listener ──
	if cfg.Channels.Telegram.BotToken != "" && cfg.Channels.Telegram.BotToken != "<YOUR_TELEGRAM_BOT_TOKEN>" {
		log.Println("📲 Starting Telegram listener...")
		go startTelegramListener(cfg, skills, selectedRT)
	} else {
		log.Println("⚠️  Telegram bot token not set — skipping channel")
	}

	// ── Keep alive ──
	log.Println("🦞 PicoClaw is running. Press Ctrl+C to stop.")
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
	<-sigCh
	log.Println("🛑 Shutting down PicoClaw...")
}

// cmdBenchmark runs device benchmarking and prints results.
func cmdBenchmark() {
	log.Println("🔍 Benchmarking device...")
	profile := runtime.BenchmarkDevice()

	fmt.Println("═══════════════════════════════════════")
	fmt.Println("  PicoClaw Device Benchmark Report")
	fmt.Println("═══════════════════════════════════════")
	fmt.Printf("  Architecture:    %s\n", profile.Arch)
	fmt.Printf("  CPU Cores:       %d\n", profile.CPUCores)
	fmt.Printf("  Total RAM:       %d MB\n", profile.RAMMb)
	fmt.Printf("  SoC Vendor:      %s\n", profile.SoCVendor)
	fmt.Printf("  SoC Model:       %s\n", profile.SoCModel)
	fmt.Printf("  Android API:     %d\n", profile.AndroidAPI)
	fmt.Printf("  Android Version: %s\n", profile.AndroidVersion)
	fmt.Printf("  GPU Delegate:    %v\n", profile.HasGPUDelegate)
	fmt.Printf("  Storage (free):  %d MB\n", profile.AvailStorageMB)
	fmt.Println("───────────────────────────────────────")

	// Show recommended runtime
	allRuntimes := []runtime.RuntimeID{
		runtime.RuntimeExecuTorch,
		runtime.RuntimeLlamaCpp,
		runtime.RuntimePicoLM,
		runtime.RuntimeLiteRT,
		runtime.RuntimeMNN,
	}
	fmt.Println("  Runtime Compatibility:")
	for _, id := range allRuntimes {
		rt := runtime.Get(id)
		status := "❌ not registered"
		if rt != nil {
			if rt.IsAvailable() {
				status = "✅ available"
			} else {
				status = "⚠️  registered but not available"
			}
		}
		fmt.Printf("    %-14s %s\n", id, status)
	}
	fmt.Println("═══════════════════════════════════════")
}

// loadConfig reads and parses picoclaw.json.
func loadConfig(path string) (*Config, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read config: %w", err)
	}
	var cfg Config
	if err := json.Unmarshal(data, &cfg); err != nil {
		return nil, fmt.Errorf("parse config: %w", err)
	}
	return &cfg, nil
}

// Skill represents a loaded SKILL.md file parsed into structured data.
type Skill struct {
	Name  string
	Rules []string
	Tools []string
	Raw   string // original markdown
}

// loadSkills reads SKILL.md files from the skills directory.
func loadSkills(dir string, enabled []string) map[string]*Skill {
	skills := make(map[string]*Skill)
	for _, name := range enabled {
		path := fmt.Sprintf("%s/%s/SKILL.md", strings.TrimSuffix(dir, "/"), name)
		data, err := os.ReadFile(path)
		if err != nil {
			log.Printf("⚠️  Could not load skill '%s': %v", name, err)
			continue
		}
		skill := parseSkillMD(name, string(data))
		skills[name] = skill
	}
	return skills
}

// parseSkillMD extracts tools and rules from a SKILL.md file.
func parseSkillMD(name, content string) *Skill {
	skill := &Skill{Name: name, Raw: content}
	inTools := false
	inRules := false

	for _, line := range strings.Split(content, "\n") {
		trimmed := strings.TrimSpace(line)

		if strings.HasPrefix(trimmed, "## Tools") {
			inTools = true
			inRules = false
			continue
		}
		if strings.HasPrefix(trimmed, "## Behavior Rules") || strings.HasPrefix(trimmed, "## Rules") {
			inRules = true
			inTools = false
			continue
		}
		if strings.HasPrefix(trimmed, "## ") || strings.HasPrefix(trimmed, "# ") {
			inTools = false
			inRules = false
			continue
		}

		if inTools && strings.HasPrefix(trimmed, "- `") {
			// Extract tool name from "- `tool.name` — description"
			parts := strings.SplitN(trimmed, "`", 3)
			if len(parts) >= 2 {
				skill.Tools = append(skill.Tools, parts[1])
			}
		}
		if inRules && len(trimmed) > 2 {
			skill.Rules = append(skill.Rules, trimmed)
		}
	}

	return skill
}

// startCronScheduler runs scheduled jobs defined in config.
func startCronScheduler(cfg *Config, skills map[string]*Skill, rt runtime.InferenceRuntime) {
	for _, job := range cfg.Cron.Jobs {
		log.Printf("[cron] scheduling: %s (%s) → %s.%s", job.Name, job.Schedule, job.Skill, job.Action)
	}
	// In production: use robfig/cron to schedule real jobs.
	// Each job triggers the skill's action via the inference runtime.
	// Simplified loop for prototype:
	ticker := time.NewTicker(60 * time.Second)
	defer ticker.Stop()
	for range ticker.C {
		// Check if any scheduled jobs should fire
		now := time.Now()
		for _, job := range cfg.Cron.Jobs {
			_ = now
			_ = job
			// Match cron expression against current time and dispatch
		}
	}
}

// startTelegramListener connects to Telegram and processes incoming messages.
func startTelegramListener(cfg *Config, skills map[string]*Skill, rt runtime.InferenceRuntime) {
	log.Printf("[telegram] connecting with bot token: %s...%s",
		cfg.Channels.Telegram.BotToken[:4], cfg.Channels.Telegram.BotToken[len(cfg.Channels.Telegram.BotToken)-4:])

	// In production: use go-telegram-bot-api to listen for updates.
	// Route each message through the SLM for intent recognition,
	// then dispatch to the appropriate skill.
	//
	// For master-slave mode:
	//   - Slave receives commands from master and executes locally
	//   - Slave sends status updates back to master
	//   - Master can push profile changes to slave in real-time
	//
	// Simplified polling loop for prototype:
	for {
		time.Sleep(2 * time.Second)
		// bot.GetUpdates() → process each message → SLM infer → skill dispatch
	}
}
