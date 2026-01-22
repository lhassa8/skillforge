---
schema_version: "1.0"
name: api-documenter
description: Use when asked to generate API documentation. Creates comprehensive docs with endpoints, parameters, and examples.
version: 1.0.0
min_skillforge_version: 1.0.0
tags:
  - documentation
  - api
includes:
  - ./STYLE_GUIDE.md
---

# API Documentation Generator

Generate comprehensive API documentation from code, specifications, or descriptions.

## Documentation Structure

Every API endpoint should include:

1. **Endpoint**: HTTP method and path
2. **Description**: What the endpoint does
3. **Authentication**: Required auth (if any)
4. **Parameters**: Path, query, and body parameters
5. **Response**: Success and error responses
6. **Examples**: Request/response examples

## Output Format

```markdown
## Endpoint Name

Brief description.

### Request

`METHOD /path/:param`

**Authentication**: Bearer token / API key / None

**Parameters**:
| Name | Type | In | Required | Description |
|------|------|-----|----------|-------------|
| id | string | path | Yes | Resource ID |

**Body**:
```json
{
  "field": "value"
}
```

### Response

**Success (200)**:
```json
{
  "data": {}
}
```

**Error (4xx)**:
```json
{
  "error": "message"
}
```

### Example

```bash
curl -X METHOD https://api.example.com/path \
  -H "Authorization: Bearer token" \
  -d '{"field": "value"}'
```
```

## Examples

### Example 1: REST Endpoint

**User**: Document this endpoint:
```python
@app.get("/users/{user_id}")
def get_user(user_id: int, include_posts: bool = False):
    """Get user by ID."""
    ...
```

**Response**:

## Get User

Retrieve a user by their unique identifier.

### Request

`GET /users/:user_id`

**Authentication**: Bearer token

**Parameters**:
| Name | Type | In | Required | Description |
|------|------|-----|----------|-------------|
| user_id | integer | path | Yes | Unique user identifier |
| include_posts | boolean | query | No | Include user's posts (default: false) |

### Response

**Success (200)**:
```json
{
  "id": 123,
  "name": "John Doe",
  "email": "john@example.com",
  "posts": []
}
```

**Error (404)**:
```json
{
  "error": "User not found"
}
```

### Example

```bash
curl https://api.example.com/users/123?include_posts=true \
  -H "Authorization: Bearer your-token"
```
