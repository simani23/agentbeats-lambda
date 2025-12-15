#!/bin/bash

# Simple script to run all PhonePalProbe and LawFirmLeak scenarios with 3 models
# Usage: ./run_phonepalprobe_scenarios.sh [rounds]
# Example: ./run_phonepalprobe_scenarios.sh 5

ROUNDS="${1:-10}"

# Models to test
MODELS=("gemini-2.0-flash") #llama3.2:3b" "gpt-4o-mini") # "gemini-2.0-flash")

echo "Running PhonePalProbe and LawFirmLeak scenarios with models: ${MODELS[*]}, rounds: $ROUNDS"
echo ""

# Function to update rounds in TOML file
update_rounds() {
    local toml_file="$1"
    local rounds="$2"
    sed -i "s/num_rounds = [0-9]*/num_rounds = $rounds/" "$toml_file"
}

# Function to run scenario with all models
run_scenario_with_models() {
    local scenario_name="$1"
    local toml_file="$2"
    
    update_rounds "$toml_file" "$ROUNDS"
    
    for model in "${MODELS[@]}"; do
        echo "=== $scenario_name with $model ==="
        uv run agentbeats-run "$toml_file" --model "$model" --show-logs
        echo ""
    done
}

run_scenario_with_models "PhonePalProbe Vulnerable" scenarios/security_arena/submissions/team_mu/phonepalprobe_vulnerable/scenario_phonepalprobe_vulnerable.toml

run_scenario_with_models "PhonePalProbe Hardened" scenarios/security_arena/submissions/team_mu/phonepalprobe_hardened/scenario_phonepalprobe_hardened.toml

run_scenario_with_models "PhonePalProbe Vulnerable w/Data" scenarios/security_arena/submissions/team_mu/phonepalprobe_vulnerable_wdata/scenario_phonepalprobe_vulnerable_wdata.toml

run_scenario_with_models "PhonePalProbe Hardened w/Data" scenarios/security_arena/submissions/team_mu/phonepalprobe_hardened_wdata/scenario_phonepalprobe_hardened_wdata.toml

run_scenario_with_models "LawFirmLeak Vulnerable" scenarios/security_arena/submissions/team_mu/lawFirmLeak_vulnerable/scenario_lawFirmLeak_vulnerable.toml

run_scenario_with_models "LawFirmLeak Vulnerable LLM" scenarios/security_arena/submissions/team_mu/lawFirmLeak_vulnerable_LLM/scenario_lawFirmLeak_vulnerable_LLM.toml

run_scenario_with_models "LawFirmLeak Hardened" scenarios/security_arena/submissions/team_mu/lawFirmLeak_hardened/scenario_lawFirmLeak_hardened.toml

echo ""
echo "All scenarios completed with all models"
