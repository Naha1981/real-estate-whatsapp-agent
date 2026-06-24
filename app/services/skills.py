"""
Skills Loader — loads and manages agent skill definitions.
Adapted from HyperAgent public skills format.

Skills are JSON files that define:
- System prompts and behavior patterns
- Conversation workflows
- Output templates
- Qualification/scoring logic

Usage:
    loader = SkillsLoader()
    buyer_prompt = loader.load_skill("sa-buyer-conversation")
    lead_prompt = loader.load_skill("sa-lead-qualifier")
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

SKILLS_DIR = Path(__file__).parent.parent.parent / "skills"


class SkillsLoader:
    """Loads and manages agent skill definitions."""

    def __init__(self, skills_dir: Path = SKILLS_DIR):
        self.skills_dir = skills_dir
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._load_all()

    def _load_all(self):
        """Pre-load all skill files from the skills directory."""
        if not self.skills_dir.exists():
            logger.warning(f"Skills directory not found: {self.skills_dir}")
            return

        for skill_file in self.skills_dir.glob("skill-*.json"):
            try:
                with open(skill_file) as f:
                    skill = json.load(f)
                name = skill["data"]["name"]
                self._cache[skill_file.stem] = skill
                logger.info(f"📚 Loaded skill: {name}")
            except Exception as e:
                logger.error(f"Failed to load {skill_file}: {e}")

    def get_skill(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """Get a skill by its ID (filename without .json)."""
        # Try exact match
        if skill_id in self._cache:
            return self._cache[skill_id]

        # Try matching by name
        for key, skill in self._cache.items():
            if skill_id.lower() in skill["data"]["name"].lower():
                return skill

        return None

    def get_system_prompt(self, skill_id: str) -> Optional[str]:
        """Extract the skillMdBody as a system prompt."""
        skill = self.get_skill(skill_id)
        if not skill:
            return None
        return skill["data"].get("skillMdBody")

    def get_all_skills(self) -> List[Dict[str, Any]]:
        """List all loaded skills with metadata."""
        return [
            {
                "id": key,
                "name": skill["data"]["name"],
                "description": skill["data"]["description"],
                "tags": skill["data"].get("tags", []),
            }
            for key, skill in self._cache.items()
        ]

    def build_agent_system_prompt(self, role: str = "buyer_agent") -> str:
        """
        Build a composite system prompt by combining relevant skills.
        
        Args:
            role: One of 'buyer_agent', 'seller_agent', 'rental_agent', 'luxury_agent', 'investor_agent'
        """
        prompts = []

        # Always include structured outputs
        structured = self.get_system_prompt("skill-sa-structured-outputs")
        if structured:
            prompts.append(structured)

        # Load role-specific behavior
        behaviors = self.get_system_prompt("skill-sa-agent-behaviors")
        if behaviors:
            # Extract only the relevant template section
            role_markers = {
                "buyer_agent": "Township Property Specialist",
                "rental_agent": "Rental Portfolio Manager",
                "luxury_agent": "Luxury Property Consultant",
                "investor_agent": "Investor Advisor",
                "seller_agent": "Suburban Family Agent",
            }
            prompts.append(behaviors)

        # Load conversation flow
        conversation = self.get_system_prompt("skill-sa-buyer-conversation")
        if conversation:
            prompts.append(conversation)

        # Load qualification logic
        qualifier = self.get_system_prompt("skill-sa-lead-qualifier")
        if qualifier:
            prompts.append(qualifier)

        return "\n\n---\n\n".join(prompts)

    def get_lead_scoring_prompt(self) -> str:
        """Get just the lead scoring prompt for standalone use."""
        skill = self.get_system_prompt("skill-sa-lead-qualifier")
        if not skill:
            return ""
        # Extract the scoring section
        for section in skill.split("## "):
            if section.startswith("Lead Scoring Prompt Template"):
                return "## " + section
        return skill


# Singleton
skills_loader = SkillsLoader()
