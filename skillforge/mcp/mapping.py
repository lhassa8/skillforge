"""Mapping between SkillForge Skills and MCP Tools.

This module provides bidirectional conversion between Anthropic Agent Skills
and Model Context Protocol (MCP) tool definitions.

MCP Specification: https://modelcontextprotocol.io/
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

from skillforge.skill import Skill, normalize_skill_name


class MCPMappingError(Exception):
    """Raised when MCP mapping fails."""
    pass


@dataclass
class MCPToolParameter:
    """A parameter for an MCP tool.

    Maps to JSON Schema property format used by MCP.
    """
    name: str
    description: str
    type: str = "string"
    required: bool = False
    default: Optional[Any] = None
    enum: Optional[list[str]] = None

    def to_json_schema(self) -> dict:
        """Convert to JSON Schema property format."""
        schema: dict[str, Any] = {
            "type": self.type,
            "description": self.description,
        }
        if self.default is not None:
            schema["default"] = self.default
        if self.enum:
            schema["enum"] = self.enum
        return schema


@dataclass
class MCPToolDefinition:
    """An MCP tool definition.

    Represents a tool that can be exposed via MCP server.

    Attributes:
        name: Tool name (lowercase, hyphens allowed)
        description: Human-readable description
        parameters: List of tool parameters
        skill_content: Original skill content (for execution context)
    """
    name: str
    description: str
    parameters: list[MCPToolParameter] = field(default_factory=list)
    skill_content: str = ""
    version: Optional[str] = None

    def to_mcp_schema(self) -> dict:
        """Convert to MCP tool schema format.

        Returns:
            Dictionary in MCP tool definition format
        """
        # Build JSON Schema for parameters
        properties = {}
        required = []

        for param in self.parameters:
            properties[param.name] = param.to_json_schema()
            if param.required:
                required.append(param.name)

        input_schema: dict[str, Any] = {
            "type": "object",
            "properties": properties,
        }
        if required:
            input_schema["required"] = required

        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": input_schema,
        }

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "parameters": [
                {
                    "name": p.name,
                    "description": p.description,
                    "type": p.type,
                    "required": p.required,
                    "default": p.default,
                    "enum": p.enum,
                }
                for p in self.parameters
            ],
            "skill_content": self.skill_content,
        }

    @classmethod
    def from_dict(cls, data: dict) -> MCPToolDefinition:
        """Create from dictionary."""
        parameters = [
            MCPToolParameter(
                name=p["name"],
                description=p.get("description", ""),
                type=p.get("type", "string"),
                required=p.get("required", False),
                default=p.get("default"),
                enum=p.get("enum"),
            )
            for p in data.get("parameters", [])
        ]

        return cls(
            name=data["name"],
            description=data["description"],
            parameters=parameters,
            skill_content=data.get("skill_content", ""),
            version=data.get("version"),
        )


def skill_to_mcp_tool(skill: Skill) -> MCPToolDefinition:
    """Convert a SkillForge Skill to an MCP tool definition.

    Args:
        skill: The skill to convert

    Returns:
        MCPToolDefinition that can be exposed via MCP server
    """
    # Extract parameters from skill content
    # Look for patterns like "Input: <description>" or "Parameters:" sections
    parameters = _extract_parameters_from_content(skill.content)

    # If no parameters found, add a default "request" parameter
    if not parameters:
        parameters = [
            MCPToolParameter(
                name="request",
                description="The user's request or input for this skill",
                type="string",
                required=True,
            )
        ]

    return MCPToolDefinition(
        name=skill.name,
        description=skill.description,
        parameters=parameters,
        skill_content=skill.content,
        version=skill.version,
    )


def mcp_tool_to_skill(tool: MCPToolDefinition) -> Skill:
    """Convert an MCP tool definition to a SkillForge Skill.

    Args:
        tool: The MCP tool definition

    Returns:
        Skill that can be used with SkillForge
    """
    # Build skill content from tool definition
    content = _build_skill_content_from_tool(tool)

    return Skill(
        name=normalize_skill_name(tool.name),
        description=tool.description,
        content=content,
        version=tool.version,
    )


def _extract_parameters_from_content(content: str) -> list[MCPToolParameter]:
    """Extract parameters from skill content.

    Looks for common patterns:
    - "## Parameters" or "## Input" sections
    - Bullet points with parameter descriptions
    - "- parameter_name: description" format
    """
    parameters = []

    # Look for Parameters/Input section
    param_section_match = re.search(
        r"##\s*(?:Parameters|Inputs?|Arguments?)\s*\n(.*?)(?=\n##|\Z)",
        content,
        re.IGNORECASE | re.DOTALL
    )

    if param_section_match:
        section = param_section_match.group(1)

        # Extract bullet point parameters
        # Pattern: - name: description or - name (type): description
        param_pattern = re.compile(
            r"[-*]\s*`?(\w+)`?\s*(?:\((\w+)\))?\s*[:-]\s*(.+?)(?=\n[-*]|\n\n|\Z)",
            re.DOTALL
        )

        for match in param_pattern.finditer(section):
            name = match.group(1)
            param_type = match.group(2) or "string"
            description = match.group(3).strip()

            # Check if marked as required
            required = "required" in description.lower()

            parameters.append(MCPToolParameter(
                name=name,
                description=description,
                type=param_type,
                required=required,
            ))

    return parameters


def _build_skill_content_from_tool(tool: MCPToolDefinition) -> str:
    """Build skill content from MCP tool definition."""
    lines = [
        f"# {tool.name.replace('-', ' ').title()}",
        "",
        "## Overview",
        "",
        tool.description,
        "",
    ]

    # Add parameters section if any
    if tool.parameters:
        lines.extend([
            "## Parameters",
            "",
        ])
        for param in tool.parameters:
            required_str = " (required)" if param.required else ""
            lines.append(f"- `{param.name}`{required_str}: {param.description}")
        lines.append("")

    # Add original content if available
    if tool.skill_content:
        lines.extend([
            "## Instructions",
            "",
            tool.skill_content,
        ])

    return "\n".join(lines)


def parse_mcp_tool_response(response: dict) -> MCPToolDefinition:
    """Parse an MCP tool definition from server response.

    Args:
        response: MCP ListTools response item

    Returns:
        MCPToolDefinition

    Raises:
        MCPMappingError: If response format is invalid
    """
    if "name" not in response:
        raise MCPMappingError("MCP tool response missing 'name' field")

    name = response["name"]
    description = response.get("description", "")

    # Parse input schema
    parameters = []
    input_schema = response.get("inputSchema", {})

    if input_schema.get("type") == "object":
        properties = input_schema.get("properties", {})
        required = input_schema.get("required", [])

        for prop_name, prop_schema in properties.items():
            parameters.append(MCPToolParameter(
                name=prop_name,
                description=prop_schema.get("description", ""),
                type=prop_schema.get("type", "string"),
                required=prop_name in required,
                default=prop_schema.get("default"),
                enum=prop_schema.get("enum"),
            ))

    return MCPToolDefinition(
        name=name,
        description=description,
        parameters=parameters,
    )


def validate_tool_name(name: str) -> list[str]:
    """Validate an MCP tool name.

    Args:
        name: Tool name to validate

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    if not name:
        errors.append("Tool name is required")
        return errors

    if len(name) > 64:
        errors.append("Tool name must be 64 characters or less")

    if not re.match(r"^[a-z][a-z0-9_-]*$", name):
        errors.append(
            "Tool name must start with lowercase letter and contain only "
            "lowercase letters, numbers, underscores, and hyphens"
        )

    return errors
