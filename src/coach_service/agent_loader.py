"""
Agent configuration loader.

Loads agent configurations from the .claude/agents directory.
"""

import os
import re
from pathlib import Path
from typing import Dict, List

from ..ai_providers.base import AgentConfig


class AgentLoader:
    """Loads and manages coaching agent configurations."""

    def __init__(self, agents_dir: str = None):
        """
        Initialize the agent loader.

        Args:
            agents_dir: Path to agents directory (default: .claude/agents)
        """
        if agents_dir is None:
            # Default to .claude/agents relative to project root
            project_root = Path(__file__).parent.parent.parent
            agents_dir = project_root / '.claude' / 'agents'

        self.agents_dir = Path(agents_dir)
        self.agents: Dict[str, AgentConfig] = {}
        self._load_agents()

    def _load_agents(self):
        """Load all agent configurations from markdown files."""
        if not self.agents_dir.exists():
            raise ValueError(f"Agents directory not found: {self.agents_dir}")

        for agent_file in self.agents_dir.glob('*.md'):
            try:
                agent_config = self._parse_agent_file(agent_file)
                self.agents[agent_config.name] = agent_config
            except Exception as e:
                print(f"Warning: Failed to load agent from {agent_file}: {e}")

    def _parse_agent_file(self, file_path: Path) -> AgentConfig:
        """
        Parse an agent configuration file.

        Agent files are markdown with YAML frontmatter:
        ---
        name: agent-name
        description: Agent description
        model: sonnet/haiku/opus
        ---

        <agent system prompt content>
        """
        with open(file_path, 'r') as f:
            content = f.read()

        # Extract YAML frontmatter
        frontmatter_pattern = r'^---\s*\n(.*?)\n---\s*\n(.*)$'
        match = re.match(frontmatter_pattern, content, re.DOTALL)

        if not match:
            raise ValueError(f"No YAML frontmatter found in {file_path}")

        frontmatter, system_prompt = match.groups()

        # Parse frontmatter
        metadata = {}
        for line in frontmatter.strip().split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                metadata[key.strip()] = value.strip()

        name = metadata.get('name')
        description = metadata.get('description', '')
        model = metadata.get('model', 'default')

        if not name:
            raise ValueError(f"No name specified in {file_path}")

        # Map model names to preferences
        model_preference = 'default'
        if model.lower() in ['haiku', 'fast']:
            model_preference = 'fast'
        elif model.lower() in ['opus', 'powerful']:
            model_preference = 'powerful'

        return AgentConfig(
            name=name,
            description=description,
            system_prompt=system_prompt.strip(),
            model_preference=model_preference
        )

    def get_agent(self, name: str) -> AgentConfig:
        """Get an agent configuration by name."""
        if name not in self.agents:
            raise ValueError(
                f"Unknown agent: {name}. "
                f"Available agents: {', '.join(self.agents.keys())}"
            )
        return self.agents[name]

    def list_agents(self) -> List[str]:
        """Get list of available agent names."""
        return list(self.agents.keys())

    def get_agent_info(self) -> Dict[str, str]:
        """Get dictionary of agent names and descriptions."""
        return {
            name: agent.description
            for name, agent in self.agents.items()
        }
