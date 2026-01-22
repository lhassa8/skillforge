# Documentation Style Guide

This reference document defines the style conventions for API documentation.

## Writing Style

- Use **active voice**: "Returns the user" not "The user is returned"
- Use **present tense**: "Creates a resource" not "Will create"
- Be **concise**: Avoid unnecessary words
- Use **consistent terminology**: Pick one term and stick with it

## Code Examples

- Always include working curl examples
- Show both request and response
- Use realistic but safe example data
- Include error examples for common cases

## Parameter Descriptions

- Start with a verb or noun
- Include valid values for enums
- Note default values
- Mention constraints (min/max, format)

## Response Documentation

- Document all possible status codes
- Show full response structure
- Include pagination details if applicable
- Document rate limit headers
