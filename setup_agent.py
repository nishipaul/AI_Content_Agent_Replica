#!/usr/bin/env python3
"""
AI Agent Setup Script - Universal Installer & Configuration Tool

This script configures the boilerplate as YOUR agent.

Usage:
    # Clone the boilerplate
    git clone https://github.com/Simpplr/ai-content-agent.git my-agent
    cd my-agent

    # Run setup
    python3 setup_agent.py

    # Script will:
    # - Ask you about your agent
    # - Generate configuration files
    # - Replace boilerplate names (ai-content-agent, etc.) with your agent_id
    #   everywhere: API routes, constants, helm-values, .github workflows, scripts, docs
    # - Install dependencies
    # - Reset git (remove boilerplate history)
    # - Set up YOUR git remote

Single command:
    git clone https://github.com/Simpplr/ai-content-agent.git my-agent && cd my-agent && python3 setup_agent.py

Requirements:
    - Python 3.12+
    - Git
    - Internet connection
"""

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Minimum Python version required
MIN_PYTHON_VERSION = (3, 12)


# Color codes for cross-platform output
def _supports_color():
    """Check if terminal supports colors"""
    if platform.system() == "Windows":
        try:
            import ctypes

            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
            return True
        except Exception:
            return False
    return True


class Colors:
    """ANSI color codes that work on Windows 10+, macOS, and Linux"""

    ENABLED = _supports_color()

    RED = "\033[0;31m" if ENABLED else ""
    GREEN = "\033[0;32m" if ENABLED else ""
    YELLOW = "\033[1;33m" if ENABLED else ""
    BLUE = "\033[0;34m" if ENABLED else ""
    CYAN = "\033[0;36m" if ENABLED else ""
    MAGENTA = "\033[0;35m" if ENABLED else ""
    NC = "\033[0m" if ENABLED else ""  # No Color
    BOLD = "\033[1m" if ENABLED else ""


class SetupAgent:
    """Main setup class for AI Agent installation and configuration"""

    def __init__(self):
        self.script_dir = Path(__file__).parent.resolve()
        self.repo_root = self.script_dir
        self.master_config_path = self.repo_root / "master_config.yaml"
        self.env_file_path = self.repo_root / ".env"
        self.env_example_path = self.repo_root / ".env.example"

        # Configuration storage
        self.config: Dict = {}
        self.system_info = self._get_system_info()

    def _get_system_info(self) -> Dict:
        """Get system information for OS-specific operations"""
        return {
            "os": platform.system(),  # Windows, Darwin, Linux
            "os_version": platform.version(),
            "machine": platform.machine(),
            "python_version": sys.version,
            "is_windows": platform.system() == "Windows",
            "is_macos": platform.system() == "Darwin",
            "is_linux": platform.system() == "Linux",
        }

    # ========================================================================
    # Output Helpers
    # ========================================================================

    def print_header(self):
        """Print welcome header"""
        print()
        print(f"{Colors.CYAN}{'='*70}{Colors.NC}")
        print(
            f"{Colors.CYAN}║{Colors.NC}  {Colors.BLUE}{Colors.BOLD}AI Agent Setup - Interactive Configuration{Colors.NC}"
        )
        print(
            f"{Colors.CYAN}║{Colors.NC}  {Colors.BLUE}Universal Installer for Windows, macOS & Linux{Colors.NC}"
        )
        print(f"{Colors.CYAN}{'='*70}{Colors.NC}")
        print()
        print(
            f"{Colors.CYAN}System:{Colors.NC} {self.system_info['os']} | {Colors.CYAN}Python:{Colors.NC} {sys.version.split()[0]}"
        )
        print()

    def print_step(self, message: str):
        """Print a step message"""
        print(f"{Colors.GREEN}==>{Colors.NC} {Colors.BLUE}{message}{Colors.NC}")

    def print_info(self, message: str):
        """Print an info message"""
        print(f"{Colors.CYAN}ℹ{Colors.NC}  {message}")

    def print_warning(self, message: str):
        """Print a warning message"""
        print(f"{Colors.YELLOW}⚠{Colors.NC}  {message}")

    def print_error(self, message: str):
        """Print an error message"""
        print(f"{Colors.RED}✗{Colors.NC} {message}")

    def print_success(self, message: str):
        """Print a success message"""
        print(f"{Colors.GREEN}✓{Colors.NC} {message}")

    # ========================================================================
    # Input Helpers
    # ========================================================================

    def prompt_input(self, prompt: str, default: str = "") -> str:
        """Prompt for user input with optional default"""
        if default:
            user_input = input(
                f"{Colors.YELLOW}?{Colors.NC} {prompt} {Colors.CYAN}[{default}]{Colors.NC}: "
            ).strip()
            return user_input if user_input else default
        else:
            user_input = input(f"{Colors.YELLOW}?{Colors.NC} {prompt}: ").strip()
            return user_input

    def prompt_confirm(self, prompt: str) -> bool:
        """Prompt for yes/no confirmation"""
        response = (
            input(
                f"{Colors.YELLOW}?{Colors.NC} {prompt} {Colors.CYAN}[y/N]{Colors.NC}: "
            )
            .strip()
            .lower()
        )
        return response in ["y", "yes"]

    def get_config_flag(self, key: str, default: bool = True) -> bool:
        """Normalize config flag values from bool/string/number to boolean."""
        value = self.config.get(key, default)
        if isinstance(value, bool):
            return value
        if value is None:
            return default
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"y", "yes", "true", "1", "on", "enabled"}:
                return True
            if normalized in {"n", "no", "false", "0", "off", "disabled"}:
                return False
        return bool(value)

    def prompt_choice(self, prompt: str, options: List[str]) -> str:
        """Prompt for a choice from a list"""
        print(f"{Colors.YELLOW}?{Colors.NC} {prompt}")
        for i, option in enumerate(options, 1):
            print(f"  {i}) {option}")

        while True:
            try:
                choice = input(
                    f"{Colors.YELLOW}?{Colors.NC} Enter choice (1-{len(options)}): "
                ).strip()
                index = int(choice) - 1
                if 0 <= index < len(options):
                    selected_option = options[index]
                    if selected_option.strip().lower() == "other":
                        while True:
                            custom_value = self.prompt_input("Please specify")
                            if custom_value.strip():
                                return custom_value.strip()
                            self.print_error("Please provide a non-empty value.")
                    return selected_option
                else:
                    self.print_error(
                        f"Please enter a number between 1 and {len(options)}"
                    )
            except (ValueError, KeyboardInterrupt):
                self.print_error("Invalid input. Please enter a number.")

    # ========================================================================
    # System Requirements Check
    # ========================================================================

    def check_python_version(self) -> bool:
        """Check if Python version meets minimum requirements"""
        self.print_step("Checking Python version...")

        current_version = sys.version_info[:2]

        if current_version >= MIN_PYTHON_VERSION:
            self.print_success(
                f"Python {current_version[0]}.{current_version[1]} meets requirements"
            )
            return True
        else:
            self.print_error(
                f"Python {MIN_PYTHON_VERSION[0]}.{MIN_PYTHON_VERSION[1]}+ is required. "
                f"Current: {current_version[0]}.{current_version[1]}"
            )
            print()
            print("Please install Python 3.12+ first:")
            if self.system_info["is_windows"]:
                print("  Windows: winget install Python.Python.3.12")
                print("           or download from https://www.python.org/downloads/")
            elif self.system_info["is_macos"]:
                print("  macOS:   brew install python@3.12")
            else:
                print(
                    "  Linux:   sudo apt update && sudo apt install python3.12 python3.12-venv"
                )
            return False

    def check_git(self) -> bool:
        """Check if git is installed"""
        self.print_step("Checking Git installation...")

        try:
            result = subprocess.run(
                ["git", "--version"], capture_output=True, text=True, check=True
            )
            self.print_success(f"Git found: {result.stdout.strip()}")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.print_warning("Git not found (optional but recommended)")
            print()
            print("To install Git:")
            if self.system_info["is_windows"]:
                print("  Windows: winget install Git.Git")
            elif self.system_info["is_macos"]:
                print("  macOS:   brew install git")
            else:
                print("  Linux:   sudo apt install git")
            return False

    def install_uv(self) -> bool:
        """Install uv package manager if not present"""
        self.print_step("Checking uv package manager...")

        # Check if uv is already installed
        try:
            result = subprocess.run(
                ["uv", "--version"], capture_output=True, text=True, check=True
            )
            self.print_success(f"uv already installed: {result.stdout.strip()}")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

        self.print_info("Installing uv package manager...")

        try:
            if self.system_info["is_windows"]:
                # Windows: Use PowerShell to install
                install_cmd = [
                    "powershell",
                    "-ExecutionPolicy",
                    "ByPass",
                    "-c",
                    "irm https://astral.sh/uv/install.ps1 | iex",
                ]
            else:
                # Unix-like: Use shell script
                install_cmd = [
                    "sh",
                    "-c",
                    "curl -LsSf https://astral.sh/uv/install.sh | sh",
                ]

            subprocess.run(install_cmd, check=True)

            # Add to PATH for current session
            if self.system_info["is_windows"]:
                uv_path = Path.home() / ".cargo" / "bin"
            else:
                uv_path = Path.home() / ".local" / "bin"

            os.environ["PATH"] = str(uv_path) + os.pathsep + os.environ["PATH"]

            # Verify installation
            result = subprocess.run(
                ["uv", "--version"], capture_output=True, text=True, check=True
            )
            self.print_success(f"uv installed successfully: {result.stdout.strip()}")
            return True

        except subprocess.CalledProcessError as e:
            self.print_error(f"Failed to install uv: {e}")
            self.print_info(
                "Please install uv manually from: https://github.com/astral-sh/uv"
            )
            return False
        except Exception as e:
            self.print_error(f"Unexpected error installing uv: {e}")
            return False

    # ========================================================================
    # Configuration Collection
    # ========================================================================

    def collect_agent_info(self, args: argparse.Namespace):
        """Collect agent configuration from user"""
        self.print_step("Collecting Agent Information")
        print()
        self.print_info("Please provide information about your agent.")
        self.print_info("Press Enter to accept default values shown in [brackets].")
        print()

        # Agent ID
        if args.agent_id:
            agent_id = args.agent_id
        else:
            while True:
                agent_id = self.prompt_input(
                    "Agent ID (lowercase, hyphens, e.g., my-custom-agent)", ""
                )
                if (
                    agent_id
                    and agent_id.replace("-", "").replace("_", "").isalnum()
                    and agent_id.islower()
                ):
                    break
                self.print_error(
                    "Agent ID must be lowercase with hyphens/underscores only"
                )

        self.config["agent_id"] = agent_id

        # Agent Name
        default_name = agent_id.replace("-", " ").replace("_", " ").title()
        self.config["agent_name"] = args.agent_name or self.prompt_input(
            "Agent Name (human-readable)", default_name
        )

        # Description
        default_desc = f"{self.config['agent_name']} agent powered by AI Infra SDK"
        self.config["description"] = args.description or self.prompt_input(
            "Agent Description", default_desc
        )

        # Version
        self.config["version"] = self.prompt_input("Initial Version", "1.0.0")

        # Framework
        if args.framework:
            framework = args.framework
        else:
            print()
            framework = self.prompt_choice(
                "Select AI Framework:",
                ["CrewAI", "OpenAI", "LangGraph", "VertexAI", "other"],
            )
        self.config["framework"] = framework

        # Category
        if args.category:
            category = args.category
        else:
            print()
            category = self.prompt_choice(
                "Select Agent Category:",
                [
                    "platform_services",
                    "business_logic",
                    "data_processing",
                    "analytics",
                    "integration",
                    "other",
                ],
            )
        self.config["category"] = category

        # Pattern
        print()
        pattern = self.prompt_choice(
            "Select Agent Pattern:",
            [
                "Single Agent",
                "Sequential Crew",
                "Hierarchical Crew",
                "Collaborative Crew",
                "Tool-Using Agent",
                "RAG Agent",
                "ReAct Agent",
                "other",
            ],
        )
        self.config["pattern"] = pattern

        print()
        self.print_step("Collecting Owner Information")
        print()

        # Owner Team
        self.config["owner_team"] = args.owner_team or self.prompt_input(
            "Team Name", "my-team"
        )

        # Owner Email
        default_email = f"{self.config['owner_team']}@simpplr.com"
        self.config["owner_email"] = args.owner_email or self.prompt_input(
            "Team Email", default_email
        )

        # Slack Channel
        default_slack = f"#{self.config['owner_team']}-support"
        self.config["owner_slack"] = args.owner_slack or self.prompt_input(
            "Slack Channel", default_slack
        )

        # GitHub Repo
        default_repo = f"https://github.com/Simpplr/{agent_id}"
        self.config["github_repo"] = args.github_repo or self.prompt_input(
            "GitHub Repository URL", default_repo
        )

        print()
        self.print_step("Collecting Runtime Configuration")
        print()

        # Endpoints and features
        if args.skip_prompts:
            self.config["rest_enabled"] = True
            self.config["kafka_enabled"] = False
            self.config["websocket_enabled"] = False
            self.config["mongo_enabled"] = True
            self.config["redis_enabled"] = True
            self.config["sql_enabled"] = True
            self.config["memory_enabled"] = False
            self.config["prompt_mgmt_enabled"] = False
        else:
            print(f"{Colors.YELLOW}Agent Endpoints{Colors.NC}")
            self.config["rest_enabled"] = True
            self.config["kafka_enabled"] = self.prompt_confirm("Enable Kafka?")
            self.config["websocket_enabled"] = self.prompt_confirm("Enable WebSocket?")
            print()
            print(f"{Colors.YELLOW}Databases{Colors.NC}")
            self.config["mongo_enabled"] = self.prompt_confirm("Enable MongoDB?")
            self.config["redis_enabled"] = self.prompt_confirm("Enable Redis?")
            self.config["sql_enabled"] = self.prompt_confirm(
                "Enable PostgreSQL Database?"
            )
            print()
            print(f"{Colors.YELLOW}Memory{Colors.NC}")
            self.config["memory_enabled"] = self.prompt_confirm(
                "Enable Short-term Memory?"
            )
            print()
            self.config["prompt_mgmt_enabled"] = False  # Disabled; not prompted

        # Tags
        print()
        default_tags = agent_id
        tags_input = self.prompt_input(
            "Agent Tags (comma-separated, e.g., summarization,analysis)", default_tags
        )
        self.config["tags"] = [tag.strip() for tag in tags_input.split(",")]

        print()
        self.print_success("Configuration collected successfully!")
        print()

    def modify_agent_info(self):
        """Modify agent information after reviewing summary."""
        print()
        self.print_step("Modify Agent Information")
        print()

        while True:
            agent_id = self.prompt_input(
                "Agent ID (lowercase, hyphens, e.g., my-custom-agent)",
                self.config.get("agent_id", ""),
            )
            if (
                agent_id
                and agent_id.replace("-", "").replace("_", "").isalnum()
                and agent_id.islower()
            ):
                self.config["agent_id"] = agent_id
                break
            self.print_error("Agent ID must be lowercase with hyphens/underscores only")

        default_name = (
            self.config["agent_id"].replace("-", " ").replace("_", " ").title()
        )
        self.config["agent_name"] = self.prompt_input(
            "Agent Name (human-readable)", self.config.get("agent_name", default_name)
        )

        default_desc = f"{self.config['agent_name']} agent powered by AI Infra SDK"
        self.config["description"] = self.prompt_input(
            "Agent Description", self.config.get("description", default_desc)
        )

        self.config["version"] = self.prompt_input(
            "Initial Version", self.config.get("version", "1.0.0")
        )

        print()
        self.config["framework"] = self.prompt_choice(
            "Select AI Framework:",
            ["CrewAI", "OpenAI", "LangGraph", "VertexAI", "other"],
        )

        print()
        self.config["category"] = self.prompt_choice(
            "Select Agent Category:",
            [
                "platform_services",
                "business_logic",
                "data_processing",
                "analytics",
                "integration",
                "other",
            ],
        )

        print()
        self.config["pattern"] = self.prompt_choice(
            "Select Agent Pattern:",
            [
                "Single Agent",
                "Sequential Crew",
                "Hierarchical Crew",
                "Collaborative Crew",
                "Tool-Using Agent",
                "RAG Agent",
                "ReAct Agent",
                "other",
            ],
        )

        default_tags = self.config["agent_id"]
        tags_input = self.prompt_input(
            "Agent Tags (comma-separated, e.g., summarization,analysis)",
            ",".join(self.config.get("tags", [default_tags])),
        )
        self.config["tags"] = [
            tag.strip() for tag in tags_input.split(",") if tag.strip()
        ]

    def modify_owner_info(self):
        """Modify owner/team information after reviewing summary."""
        print()
        self.print_step("Modify Owner Information")
        print()

        self.config["owner_team"] = self.prompt_input(
            "Team Name", self.config.get("owner_team", "my-team")
        )

        default_email = f"{self.config['owner_team']}@simpplr.com"
        self.config["owner_email"] = self.prompt_input(
            "Team Email", self.config.get("owner_email", default_email)
        )

        default_slack = f"#{self.config['owner_team']}-support"
        self.config["owner_slack"] = self.prompt_input(
            "Slack Channel", self.config.get("owner_slack", default_slack)
        )

        default_repo = f"https://github.com/Simpplr/{self.config.get('agent_id', 'my-custom-agent')}"
        self.config["github_repo"] = self.prompt_input(
            "GitHub Repository URL", self.config.get("github_repo", default_repo)
        )

    def modify_runtime_configuration(self):
        """Modify runtime configuration after reviewing summary."""
        print()
        self.print_step("Modify Runtime Configuration")
        print()

        print(f"{Colors.YELLOW}Agent Endpoints{Colors.NC}")
        self.config["rest_enabled"] = True
        self.config["kafka_enabled"] = self.prompt_confirm("Enable Kafka?")
        self.config["websocket_enabled"] = self.prompt_confirm("Enable WebSocket?")
        print()
        print(f"{Colors.YELLOW}Databases{Colors.NC}")
        self.config["mongo_enabled"] = self.prompt_confirm("Enable MongoDB?")
        self.config["redis_enabled"] = self.prompt_confirm("Enable Redis?")
        self.config["sql_enabled"] = self.prompt_confirm("Enable SQL Database?")
        print()
        print(f"{Colors.YELLOW}Memory{Colors.NC}")
        self.config["memory_enabled"] = self.prompt_confirm("Enable Short-term Memory?")
        self.config["prompt_mgmt_enabled"] = False  # Disabled; not prompted

    def delete_repo_and_exit(self):
        """Delete repository directory and exit setup."""
        self.print_warning("Quit selected. Deleting repository folder...")
        try:
            # Move out of repo so deletion can proceed.
            os.chdir(self.repo_root.parent)
            shutil.rmtree(self.repo_root)
            self.print_success(f"Deleted repository folder: {self.repo_root}")
        except Exception as e:
            self.print_warning(f"Could not fully delete repository folder: {e}")
        sys.exit(0)

    def review_configuration_loop(self):
        """Show summary and allow user to edit sections before proceeding."""
        while True:
            self.show_configuration_summary()
            if self.prompt_confirm("Proceed with this configuration?"):
                return

            print()
            action = self.prompt_choice(
                "Configuration not approved. What would you like to do?",
                [
                    "Modify Agent Info",
                    "Modify Owner info",
                    "Modify Runtime configuration",
                    "Save Config",
                    "Quit setup",
                ],
            )

            if action == "Modify Agent Info":
                self.modify_agent_info()
            elif action == "Modify Owner info":
                self.modify_owner_info()
            elif action == "Modify Runtime configuration":
                self.modify_runtime_configuration()
            elif action == "Save Config":
                self.generate_master_config()
                self.print_success("Configuration saved. Continuing setup...")
                return
            else:
                self.delete_repo_and_exit()

    def show_configuration_summary(self):
        """Display configuration summary"""
        print()
        print(f"{Colors.CYAN}{'='*70}{Colors.NC}")
        print(
            f"{Colors.CYAN}║{Colors.NC}  {Colors.BLUE}{Colors.BOLD}Configuration Summary{Colors.NC}"
        )
        print(f"{Colors.CYAN}{'='*70}{Colors.NC}")
        print()

        print(f"{Colors.YELLOW}Agent Information:{Colors.NC}")
        print(f"  ID:          {self.config['agent_id']}")
        print(f"  Name:        {self.config['agent_name']}")
        print(f"  Description: {self.config['description']}")
        print(f"  Version:     {self.config['version']}")
        print(f"  Framework:   {self.config['framework']}")
        print(f"  Category:    {self.config['category']}")
        print(f"  Pattern:     {self.config['pattern']}")
        print()

        print(f"{Colors.YELLOW}Owner Information:{Colors.NC}")
        print(f"  Team:        {self.config['owner_team']}")
        print(f"  Email:       {self.config['owner_email']}")
        print(f"  Slack:       {self.config['owner_slack']}")
        print(f"  GitHub:      {self.config['github_repo']}")
        print()

        print(f"{Colors.YELLOW}Runtime Configuration:{Colors.NC}")
        print(f"  REST API:    {self.config['rest_enabled']}")
        print(f"  Kafka:       {self.config['kafka_enabled']}")
        print(f"  WebSocket:   {self.config['websocket_enabled']}")
        print(f"  MongoDB:     {self.config['mongo_enabled']}")
        print(f"  Redis:       {self.config['redis_enabled']}")
        print(f"  SQL:         {self.config['sql_enabled']}")
        print(f"  Memory:      {self.config['memory_enabled']}")
        print(f"  Prompts:     {self.config['prompt_mgmt_enabled']}")
        print()

    # ========================================================================
    # Configuration File Generation
    # ========================================================================

    def generate_master_config(self):
        """Generate master_config.yaml file"""
        self.print_step("Generating master_config.yaml...")

        # Generate tags YAML
        tags_yaml = "\n".join(f"    - {tag}" for tag in self.config["tags"])

        # Generate config content
        config_content = f"""## all the agent registry configurations are defined here
agent_registry_config:
  agent_id: {self.config['agent_id']}
  name: {self.config['agent_name']}
  description: {self.config['description']}
  version: {self.config['version']}
  pattern: {self.config['pattern']}
  framework: {self.config['framework']}
  tags:
{tags_yaml}
  category: {self.config['category']}
  status: development

  owner:
    team: {self.config['owner_team']}
    contact: {self.config['owner_email']}
    slack_channel: "{self.config['owner_slack']}"
    github_repo: {self.config['github_repo']}

  capabilities:
    - {self.config['agent_id']}

  endpoints:
    dev: https://api-be-2.dev.simpplr.xyz/v1/{self.config['agent_id']}

  reusable: true
  tools:
    - custom
  memory_config:
    short_term: {str(self.config['memory_enabled']).lower()}
    long_term: false
    contextual: false



## all the runtime configurations for the agent are defined here
agent_runtime_config:
  endpoints:
    rest_api_enabled: {str(self.config['rest_enabled']).lower()}
    kafka_enabled: {str(self.config['kafka_enabled']).lower()}
    websocket_enabled: {str(self.config['websocket_enabled']).lower()}

  databases:
    mongo_enabled: {str(self.config['mongo_enabled']).lower()}
    redis_enabled: {str(self.config['redis_enabled']).lower()}
    sql_enabled: {str(self.config['sql_enabled']).lower()}

  memory:
    short_term: {str(self.config['memory_enabled']).lower()}

  prompt_management:
    enabled: {str(self.config['prompt_mgmt_enabled']).lower()}




### All the prompts for the agents and tasks and their versions are defined here
agent_prompt_config:
  Agents:
    - {self.config['agent_id']}_analyst:
        name: {self.config['agent_id']}_prompts
        Labels:
          - agent_{self.config['agent_id']}_analyst
        Version:
          - v1
        Tags:
{tags_yaml}

  Tasks:
    - {self.config['agent_id']}_task:
        name: {self.config['agent_id']}_prompts
        Labels:
          - task_{self.config['agent_id']}_task
        Version:
          - v1
        Tags:
{tags_yaml}
"""

        # Write to file
        self.master_config_path.write_text(config_content, encoding="utf-8")
        self.print_success("master_config.yaml generated successfully")

    def generate_env_file(self):
        """Generate .env file from template"""
        self.print_step("Generating .env file...")

        if self.env_file_path.exists():
            self.print_warning(".env file already exists. Skipping generation.")
            self.print_info(
                "If you want to regenerate, delete .env and run this script again."
            )
            return

        # Read template or create basic one
        if self.env_example_path.exists():
            env_content = self.env_example_path.read_text(encoding="utf-8")
        else:
            env_content = f"""######## Agent Name ########
AGENT_NAME={self.config['agent_id']}
############################

######## Environment ########
ENVIRONMENT=dev
############################

LOG_LEVEL=INFO


### Kafka Database Credentials (if enabled)
KAFKA_BOOTSTRAP_ADDRESS=bootstrap_address
CONSUMER_TOPIC=topic_name
PRODUCER_TOPIC=topic_name
KAFKA_GROUP_ID=group_id
SECURITY_PROTOCOL=SSL
MAX_POLL_INTERVAL_MS=6000000
MAX_POLL_RECORDS=1


### AWS and Vault Configuration
AWS_SM_VAULT_CONFIG=vault/environment/orion
AWS_DEFAULT_REGION=us-west-2
AWS_PROFILE=aws_dev

### Vault Paths (Update these with your actual vault paths)
sql_vault_path=sql_vault_path
mongo_vault_path=mongo_vault_path
REDIS_VAULT_PATH=redis_vault_path
LANGFUSE_VAULT_PATH=langfuse_vault_path

### LLM Endpoint
LLM_ENDPOINT=llm_endpoint
"""

        # Update AGENT_NAME in content
        lines = env_content.split("\n")
        updated_lines = []
        for line in lines:
            if line.startswith("AGENT_NAME="):
                updated_lines.append(f"AGENT_NAME={self.config['agent_id']}")
            else:
                updated_lines.append(line)

        self.env_file_path.write_text("\n".join(updated_lines), encoding="utf-8")
        self.print_success(".env file generated successfully")
        self.print_warning(
            "Remember to update vault paths and credentials in .env file!"
        )

    def replace_agent_readme_from_example(self):
        """Replace README.md with README_example.md and delete README_example.md."""
        self.print_step("Replacing README.md from README_example.md...")

        source_path = self.repo_root / "README_example.md"
        target_path = self.repo_root / "README.md"

        if not source_path.exists():
            self.print_warning(
                "README_example.md not found. Skipping README replacement."
            )
            return

        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            readme_content = source_path.read_text(encoding="utf-8")
            target_path.write_text(readme_content, encoding="utf-8")
            source_path.unlink()
            self.print_success("README.md replaced and README_example.md removed")
        except Exception as e:
            self.print_warning(f"Could not replace README.md: {e}")

    def update_pyproject_dependencies(self):
        """Remove disabled feature packages from pyproject.toml based on runtime config."""
        self.print_step("Updating pyproject.toml dependencies from runtime config...")

        pyproject_path = self.repo_root / "pyproject.toml"
        if not pyproject_path.exists():
            self.print_warning("pyproject.toml not found. Skipping dependency update.")
            return

        try:
            lines = pyproject_path.read_text(encoding="utf-8").splitlines()
        except Exception as e:
            self.print_warning(f"Could not read pyproject.toml: {e}")
            return

        mongo_enabled = self.get_config_flag("mongo_enabled", True)
        sql_enabled = self.get_config_flag("sql_enabled", True)
        kafka_enabled = self.get_config_flag("kafka_enabled", True)
        websocket_enabled = self.get_config_flag("websocket_enabled", True)

        def should_remove(stripped_line: str) -> bool:
            if stripped_line.startswith("#"):
                return False
            if not kafka_enabled and stripped_line.startswith('"kafka-python'):
                return True
            if not websocket_enabled and stripped_line.startswith('"websockets'):
                return True
            if not mongo_enabled and (
                stripped_line.startswith('"ai-infra-python-sdk-mongodb"')
                or stripped_line.startswith("ai-infra-python-sdk-mongodb =")
            ):
                return True
            if not sql_enabled and (
                stripped_line.startswith('"ai-infra-python-sdk-postgresql"')
                or stripped_line.startswith("ai-infra-python-sdk-postgresql =")
            ):
                return True
            return False

        removed_count = 0
        updated_lines: List[str] = []
        for line in lines:
            stripped = line.lstrip()
            if should_remove(stripped):
                removed_count += 1
                continue
            updated_lines.append(line)

        if removed_count == 0:
            self.print_info("No dependency lines needed removal in pyproject.toml")
            return

        try:
            pyproject_path.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")
            self.print_success(
                f"Updated pyproject.toml ({removed_count} line(s) removed)"
            )
        except Exception as e:
            self.print_warning(f"Could not update pyproject.toml: {e}")

    def update_env_example_by_runtime_config(self):
        """Comment .env.example entries based on runtime config."""
        self.print_step("Updating .env.example from runtime config...")

        if not self.env_example_path.exists():
            self.print_warning(".env.example not found. Skipping env example update.")
            return

        try:
            lines = self.env_example_path.read_text(encoding="utf-8").splitlines()
        except Exception as e:
            self.print_warning(f"Could not read .env.example: {e}")
            return

        kafka_enabled = self.get_config_flag("kafka_enabled", True)
        mongo_enabled = self.get_config_flag("mongo_enabled", True)
        sql_enabled = self.get_config_flag("sql_enabled", True)

        kafka_keys = {
            "KAFKA_BOOTSTRAP_ADDRESS=",
            "CONSUMER_TOPIC=",
            "PRODUCER_TOPIC=",
            "KAFKA_GROUP_ID=",
            "SECURITY_PROTOCOL=",
            "MAX_POLL_INTERVAL_MS=",
            "MAX_POLL_RECORDS=",
        }

        updated_count = 0
        updated_lines: List[str] = []
        for line in lines:
            stripped = line.lstrip()
            if stripped.startswith("#"):
                updated_lines.append(line)
                continue

            should_comment = (
                (
                    not kafka_enabled
                    and any(stripped.startswith(key) for key in kafka_keys)
                )
                or (not sql_enabled and stripped.startswith("SQL_VAULT_PATH="))
                or (not mongo_enabled and stripped.startswith("MONGO_VAULT_PATH="))
            )
            if should_comment:
                indent = line[: len(line) - len(stripped)]
                updated_lines.append(f"{indent}# {stripped}")
                updated_count += 1
            else:
                updated_lines.append(line)

        if updated_count == 0:
            self.print_info("No env lines needed updates in .env.example")
            return

        try:
            self.env_example_path.write_text(
                "\n".join(updated_lines) + "\n", encoding="utf-8"
            )
            self.print_success(
                f"Updated .env.example ({updated_count} line(s) commented)"
            )
        except Exception as e:
            self.print_warning(f"Could not update .env.example: {e}")

    def _replacement_map(self) -> Dict[str, str]:
        """Build map of boilerplate placeholders to user-configured values (for repo-wide replace)."""
        agent_id = self.config["agent_id"]
        return {
            "ai-content-agent": agent_id,
            "ai-content-agent": agent_id,
        }

    def _apply_replacements(self, content: str) -> str:
        """Apply all placeholder replacements to string content."""
        for old, new in self._replacement_map().items():
            content = content.replace(old, new)
        return content

    def replace_placeholders_repo_wide(self):
        """Replace boilerplate agent names with user-configured agent_id across the whole repo.

        Updates: src/, tests/, scripts/, helm-values/, .github/, README, sample_curl.sh,
        Makefile, .env.example, and other text files. Excludes .git, .venv, uv.lock, etc.
        """
        self.print_step(
            "Replacing agent names across repo (API, helm, workflows, scripts, docs)..."
        )

        skip_dirs = {
            ".git",
            ".venv",
            "venv",
            "node_modules",
            "__pycache__",
            ".pytest_cache",
            "dist",
            "build",
            ".cursor",
        }
        skip_files = {"uv.lock"}  # do not modify lock file
        # Extensions to process (text files only)
        text_extensions = (".py", ".yaml", ".yml", ".md", ".sh", ".toml")
        text_filenames = ("Makefile", ".env.example", "Dockerfile")

        replacement_map = self._replacement_map()
        updated_count = 0
        updated_paths: List[str] = []

        for root, dirs, files in os.walk(self.repo_root, topdown=True):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            rel_root = (
                Path(root).relative_to(self.repo_root)
                if root != self.repo_root
                else Path(".")
            )

            for name in files:
                if name in skip_files:
                    continue
                path = Path(root) / name
                rel_path = rel_root / name
                if (
                    rel_path.parts
                    and rel_path.parts[0].startswith(".")
                    and rel_path.parts[0] not in (".env.example", ".github")
                ):
                    continue
                if name.endswith(text_extensions) or name in text_filenames:
                    try:
                        raw = path.read_text(encoding="utf-8", errors="strict")
                    except Exception:
                        continue
                    new_content = raw
                    for old, new in replacement_map.items():
                        if old in new_content:
                            new_content = new_content.replace(old, new)
                    if new_content != raw:
                        path.write_text(new_content, encoding="utf-8")
                        updated_count += 1
                        updated_paths.append(str(rel_path))

        for rel in updated_paths:
            self.print_info(f"  Updated {rel}")
        if updated_count > 0:
            self.print_success(
                f"Replaced placeholders in {updated_count} files (helm, .github, src, tests, scripts, README, etc.)"
            )
        else:
            self.print_info("No files needed placeholder updates")

    # ========================================================================
    # Dependency Installation
    # ========================================================================

    def install_dependencies(self):
        """Install Python dependencies using uv"""
        self.print_step("Installing Python dependencies with uv...")
        print()
        self.print_info("This may take a few minutes...")

        try:
            # Change to repo root
            os.chdir(self.repo_root)

            # Run uv sync and allow lockfile updates to reflect pyproject changes.
            subprocess.run(["uv", "sync"], capture_output=True, text=True, check=True)

            self.print_success("Dependencies installed successfully")
            return True

        except subprocess.CalledProcessError as e:
            self.print_error("Failed to install dependencies")
            print(f"\nError output:\n{e.stderr}")
            return False
        except Exception as e:
            self.print_error(f"Unexpected error: {e}")
            return False

    def setup_precommit(self):
        """Set up pre-commit hooks"""
        self.print_step("Setting up pre-commit hooks...")

        precommit_config = self.repo_root / ".pre-commit-config.yaml"

        if not precommit_config.exists():
            self.print_warning(
                ".pre-commit-config.yaml not found. Skipping pre-commit setup."
            )
            return

        try:
            subprocess.run(
                ["uv", "run", "pre-commit", "install"],
                capture_output=True,
                text=True,
                check=True,
                cwd=self.repo_root,
            )
            self.print_success("Pre-commit hooks installed")
        except subprocess.CalledProcessError:
            self.print_warning("Failed to install pre-commit hooks (non-critical)")
        except Exception as e:
            self.print_warning(f"Could not set up pre-commit: {e}")

    # ========================================================================
    # Git Repository Setup
    # ========================================================================

    def remove_existing_git_history(self):
        """Remove existing .git directory early in setup flow."""
        git_dir = self.repo_root / ".git"
        if not git_dir.exists():
            return

        self.print_step("Removing existing Git history...")
        try:
            shutil.rmtree(git_dir)
            self.print_success("Existing git history removed")
        except Exception as e:
            self.print_warning(f"Could not remove .git: {e}")

    def setup_git_repo(self, skip_prompts: bool = False):
        """Set up a new git repository"""
        self.print_step("Setting up Git repository...")

        # Initialize fresh git
        if skip_prompts or self.prompt_confirm("Initialize fresh Git repository?"):
            try:
                subprocess.run(["git", "init"], cwd=self.repo_root, check=True)
                self.print_success("Fresh git repository initialized")
                # Checkout to develop (create if not exists)
                try:
                    subprocess.run(
                        ["git", "checkout", "-b", "develop"],
                        cwd=self.repo_root,
                        check=True,
                    )
                    self.print_success("Branch 'develop' created and checked out")
                except subprocess.CalledProcessError:
                    # Branch may already exist (e.g. after re-run), try checkout
                    subprocess.run(
                        ["git", "checkout", "develop"], cwd=self.repo_root, check=True
                    )
                    self.print_success("Checked out branch 'develop'")

                # Ask for remote URL
                if not skip_prompts:
                    print()
                    remote_url = self.prompt_input(
                        "Git remote URL (your new repo)", self.config["github_repo"]
                    )
                else:
                    remote_url = self.config["github_repo"]

                if remote_url:
                    try:
                        subprocess.run(
                            ["git", "remote", "add", "origin", remote_url],
                            cwd=self.repo_root,
                            check=True,
                        )
                        self.print_success(f"Remote 'origin' added: {remote_url}")
                    except subprocess.CalledProcessError:
                        self.print_warning("Could not add remote (may already exist)")

                # Create initial commit on develop
                if skip_prompts or self.prompt_confirm("Create initial commit?"):
                    subprocess.run(["git", "add", "."], cwd=self.repo_root, check=True)
                    subprocess.run(
                        [
                            "git",
                            "commit",
                            "-m",
                            f"Initial commit: {self.config['agent_name']}",
                        ],
                        cwd=self.repo_root,
                        check=True,
                    )
                    self.print_success("Initial commit created on develop")

                    if not skip_prompts and self.prompt_confirm("Push to remote?"):
                        try:
                            subprocess.run(
                                ["git", "push", "-u", "origin", "develop", "--force"],
                                cwd=self.repo_root,
                                check=True,
                            )
                            self.print_success("Pushed to origin/develop")
                        except subprocess.CalledProcessError:
                            self.print_warning(
                                "Could not push (make sure remote exists)"
                            )

            except subprocess.CalledProcessError as e:
                self.print_warning(f"Git operation failed: {e}")
            except FileNotFoundError:
                self.print_warning("Git not found. Skipping git setup.")

    # ========================================================================
    # Final Instructions
    # ========================================================================

    def show_next_steps(self):
        """Display next steps for the user"""
        print()
        print(f"{Colors.CYAN}{'='*70}{Colors.NC}")
        print(
            f"{Colors.CYAN}║{Colors.NC}  {Colors.GREEN}{Colors.BOLD}✓ Setup Complete!{Colors.NC}"
        )
        print(f"{Colors.CYAN}{'='*70}{Colors.NC}")
        print()

        print(f"{Colors.YELLOW}{Colors.BOLD}Your agent is ready!{Colors.NC}")
        print(f"  Location: {Colors.CYAN}{self.repo_root}{Colors.NC}")
        print()

        print(f"{Colors.YELLOW}{Colors.BOLD}Next Steps:{Colors.NC}")
        print()

        print("1. Review configuration files:")
        print(f"   {Colors.CYAN}├─{Colors.NC} master_config.yaml  (agent settings)")
        print(
            f"   {Colors.CYAN}└─{Colors.NC} .env                (vault paths - update these!)"
        )
        print()

        print("2. Configure AWS credentials:")
        if self.system_info["is_windows"]:
            print(f"   {Colors.CYAN}>{Colors.NC} aws sso login --profile aws_dev")
        else:
            print(f"   {Colors.CYAN}${Colors.NC} aws sso login --profile aws_dev")
        print()

        print("3. Customize your agent code:")
        print(
            f"   {Colors.CYAN}├─{Colors.NC} src/agent/crew.py             (define agents and tasks)"
        )
        print(
            f"   {Colors.CYAN}├─{Colors.NC} src/agent/config/agents.yaml  (agent prompts)"
        )
        print(
            f"   {Colors.CYAN}├─{Colors.NC} src/agent/config/tasks.yaml   (task prompts)"
        )
        print(
            f"   {Colors.CYAN}└─{Colors.NC} src/agent/api/routes.py       (API endpoints)"
        )
        print()

        print("4. Start the development server:")
        if self.system_info["is_windows"]:
            print(f"   {Colors.CYAN}>{Colors.NC} .venv\\Scripts\\activate")
            print(
                f"   {Colors.CYAN}>{Colors.NC} uv run uvicorn agent.api:app --reload --host 0.0.0.0 --port 5000"
            )
        else:
            print(f"   {Colors.CYAN}${Colors.NC} source .venv/bin/activate")
            print(
                f"   {Colors.CYAN}${Colors.NC} uv run uvicorn agent.api:app --reload --host 0.0.0.0 --port 5000"
            )
        print()

        print("5. Access the API documentation:")
        print(
            f"   {Colors.CYAN}Swagger:{Colors.NC} http://localhost:5000/v1/{self.config['agent_id']}/docs"
        )
        print(
            f"   {Colors.CYAN}ReDoc:{Colors.NC}   http://localhost:5000/v1/{self.config['agent_id']}/redoc"
        )
        print()

        print("6. Test the health endpoint:")
        if self.system_info["is_windows"]:
            print(f"   {Colors.CYAN}>{Colors.NC} curl http://localhost:5000/health")
        else:
            print(f"   {Colors.CYAN}${Colors.NC} curl http://localhost:5000/health")
        print()

        print(f"{Colors.YELLOW}{Colors.BOLD}For more information:{Colors.NC}")
        print(
            f"   {Colors.CYAN}├─{Colors.NC} Read README.md for detailed documentation"
        )
        print(
            f"   {Colors.CYAN}├─{Colors.NC} Check sample_curl.sh for API usage examples"
        )
        print(f"   {Colors.CYAN}└─{Colors.NC} Contact: {self.config['owner_email']}")
        print()

        self.print_success("Happy coding! 🚀")
        print()

    # ========================================================================
    # Main Execution Flow
    # ========================================================================

    def run(self, args: argparse.Namespace):
        """Main execution flow"""
        try:
            # Print header
            self.print_header()

            # First step: remove inherited git metadata; re-init happens at the end.
            self.remove_existing_git_history()

            # System requirements check
            if not self.check_python_version():
                sys.exit(1)

            self.check_git()

            if not self.install_uv():
                sys.exit(1)

            print()

            # Collect configuration
            if not args.skip_prompts:
                self.collect_agent_info(args)
                self.review_configuration_loop()
            else:
                # Non-interactive mode - set defaults
                self.print_info("Running in non-interactive mode")
                self.config = {
                    "agent_id": args.agent_id or "my-custom-agent",
                    "agent_name": args.agent_name or "My Custom Agent",
                    "description": args.description
                    or "Custom agent powered by AI Infra SDK",
                    "version": "1.0.0",
                    "framework": args.framework or "CrewAI",
                    "category": args.category or "platform_services",
                    "pattern": "service",
                    "owner_team": args.owner_team or "my-team",
                    "owner_email": args.owner_email or "my-team@simpplr.com",
                    "owner_slack": args.owner_slack or "#my-team-support",
                    "github_repo": args.github_repo
                    or f"https://github.com/Simpplr/{args.agent_id or 'my-custom-agent'}",
                    "tags": [args.agent_id or "my-custom-agent"],
                    "rest_enabled": True,
                    "kafka_enabled": False,
                    "websocket_enabled": False,
                    "mongo_enabled": True,
                    "redis_enabled": True,
                    "sql_enabled": True,
                    "memory_enabled": False,
                    "prompt_mgmt_enabled": False,
                }

            print()

            # Generate configuration files
            self.generate_master_config()
            self.update_env_example_by_runtime_config()
            self.generate_env_file()
            self.replace_agent_readme_from_example()
            self.replace_placeholders_repo_wide()
            self.update_pyproject_dependencies()

            print()

            # Install dependencies
            if not self.install_dependencies():
                self.print_warning(
                    "Failed to install dependencies. You may need to run 'uv sync' manually."
                )

            self.setup_precommit()

            print()

            # Git setup - reset and create fresh repo
            if not args.skip_prompts:
                self.setup_git_repo()
            else:
                # Auto-setup git in non-interactive mode (develop branch)
                try:
                    subprocess.run(
                        ["git", "init"],
                        cwd=self.repo_root,
                        check=True,
                        capture_output=True,
                    )
                    subprocess.run(
                        ["git", "checkout", "-b", "develop"],
                        cwd=self.repo_root,
                        check=True,
                        capture_output=True,
                    )
                    subprocess.run(
                        ["git", "remote", "add", "origin", self.config["github_repo"]],
                        cwd=self.repo_root,
                        check=True,
                        capture_output=True,
                    )
                    subprocess.run(
                        ["git", "add", "."],
                        cwd=self.repo_root,
                        check=True,
                        capture_output=True,
                    )
                    subprocess.run(
                        [
                            "git",
                            "commit",
                            "-m",
                            f"Initial commit: {self.config['agent_name']}",
                        ],
                        cwd=self.repo_root,
                        check=True,
                        capture_output=True,
                    )
                    self.print_success("Git initialized on branch develop with remote")
                    if args.push:
                        try:
                            subprocess.run(
                                ["git", "push", "-u", "origin", "develop", "--force"],
                                cwd=self.repo_root,
                                check=True,
                            )
                            self.print_success("Pushed to origin/develop")
                        except subprocess.CalledProcessError:
                            self.print_warning(
                                "Could not push (make sure remote exists)"
                            )
                except Exception:
                    pass

            # Show next steps
            self.show_next_steps()

        except KeyboardInterrupt:
            print()
            self.print_warning("Setup interrupted by user")
            sys.exit(1)
        except Exception as e:
            print()
            self.print_error(f"Unexpected error: {e}")
            import traceback

            traceback.print_exc()
            sys.exit(1)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="AI Agent Setup - Interactive Installation & Configuration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  python setup_agent.py

  # Non-interactive mode with all arguments
  python setup_agent.py --agent-id "content-summarizer" \\
    --agent-name "Content Summarizer" \\
    --description "Summarizes long-form content" \\
    --owner-team "content-team" \\
    --owner-email "content@example.com" \\
    --skip-prompts

For more information, see README.md
        """,
    )

    parser.add_argument(
        "--agent-id", help="Agent unique identifier (e.g., my-custom-agent)"
    )
    parser.add_argument("--agent-name", help="Human-readable agent name")
    parser.add_argument("--description", help="Agent description")
    parser.add_argument("--owner-team", help="Team name owning this agent")
    parser.add_argument("--owner-email", help="Team contact email")
    parser.add_argument("--owner-slack", help="Slack channel (e.g., #team-channel)")
    parser.add_argument("--github-repo", help="GitHub repository URL")
    parser.add_argument(
        "--category",
        help="Agent category",
        choices=[
            "platform_services",
            "business_logic",
            "data_processing",
            "analytics",
            "integration",
            "other",
        ],
    )
    parser.add_argument(
        "--framework",
        help="Framework used",
        choices=["CrewAI", "OpenAI", "LangGraph", "VertexAI", "other"],
    )
    parser.add_argument(
        "--skip-prompts",
        action="store_true",
        help="Skip interactive prompts, use defaults/args only",
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="Push to origin/develop after setup (use with --skip-prompts)",
    )

    args = parser.parse_args()

    # Create and run setup
    setup = SetupAgent()
    setup.run(args)


if __name__ == "__main__":
    main()
