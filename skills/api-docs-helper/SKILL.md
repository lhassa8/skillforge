---
name: api-documentation-writer
description: Use when users need help creating comprehensive API documentation including endpoint descriptions, request/response examples, authentication details, error handling, and code samples. Supports REST APIs, GraphQL APIs, WebSocket APIs, and other web services with practical, developer-friendly documentation.
---

# API Documentation Writer

This skill helps you create comprehensive, professional API documentation that developers can easily understand and implement. It covers REST APIs, GraphQL APIs, WebSocket APIs, and other web services with practical examples and clear structure.

## Core Instructions

When a user requests API documentation help:

1. **Identify API Type**: Determine if it's REST, GraphQL, WebSocket, or other API type to apply appropriate documentation patterns
2. **Gather Complete Requirements**: Ask about endpoints, authentication, data schemas, error handling, and target developer audience
3. **Structure by Standards**: Follow industry-standard documentation patterns for the specific API type
4. **Provide Working Examples**: Include realistic request/response examples with actual data that developers can copy-paste
5. **Include Implementation Details**: Add headers, status codes, authentication flows, rate limits, and edge cases
6. **Make Developer-Centric**: Use clear language, consistent formatting, and multiple code examples in popular languages

## Documentation Structure Templates

### REST API Structure
- API Overview (base URL, version, purpose)
- Authentication & Authorization
- Rate Limiting & Usage Policies
- Common Headers & Response Format
- Endpoint Documentation (grouped by resource)
- Error Handling & Status Codes
- Code Examples (cURL, JavaScript, Python)
- SDKs & Libraries (if available)

### GraphQL API Structure
- API Overview & Playground URL
- Schema Definition
- Authentication & Authorization
- Query Structure & Introspection
- Mutations & Subscriptions
- Error Handling & Field Validation
- Example Queries with Variables
- Client Libraries & Tools

### WebSocket API Structure
- Connection Details & Protocols
- Authentication & Handshake
- Message Types & Formats
- Event Handling & Subscriptions
- Connection Management
- Error Handling & Reconnection
- Client Examples & Libraries

## REST API Examples

### Example 1: Complete REST Endpoint Documentation

**User Request**: "Document my REST API endpoint for retrieving user profiles with filtering and pagination"

**Response**:
```markdown
# Get User Profiles

Retrieves a paginated list of user profiles with optional filtering and sorting.

**Endpoint**: `GET /api/v1/users`

## Authentication
Requires Bearer token: `Authorization: Bearer YOUR_ACCESS_TOKEN`

## Query Parameters

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `page` | integer | No | Page number (default: 1) | `1` |
| `limit` | integer | No | Items per page (default: 20, max: 100) | `50` |
| `role` | string | No | Filter by user role | `admin`, `user`, `moderator` |
| `status` | string | No | Filter by account status | `active`, `inactive`, `pending` |
| `sort` | string | No | Sort field and direction | `created_at:desc`, `name:asc` |
| `search` | string | No | Search in name and email | `john doe` |

## Request Examples

**Basic Request**:
```bash
curl -H "Authorization: Bearer your_token_here" \
     "https://api.example.com/api/v1/users"
```

**With Filtering and Pagination**:
```bash
curl -H "Authorization: Bearer your_token_here" \
     "https://api.example.com/api/v1/users?page=2&limit=10&role=admin&status=active&sort=created_at:desc"
```

## Response Format

**Success Response (200 OK)**:
```json
{
  "data": [
    {
      "id": "usr_1234567890",
      "email": "john.doe@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "role": "admin",
      "status": "active",
      "avatar_url": "https://cdn.example.com/avatars/john-doe.jpg",
      "created_at": "2024-01-15T10:30:00Z",
      "last_login": "2024-03-15T14:20:00Z",
      "profile": {
        "bio": "Senior Developer at Example Corp",
        "location": "San Francisco, CA",
        "website": "https://johndoe.dev"
      }
    }
  ],
  "meta": {
    "pagination": {
      "current_page": 1,
      "per_page": 20,
      "total_pages": 5,
      "total_count": 95,
      "has_next": true,
      "has_previous": false
    },
    "filters_applied": {
      "role": "admin",
      "status": "active"
    }
  }
}
```

**Empty Results (200 OK)**:
```json
{
  "data": [],
  "meta": {
    "pagination": {
      "current_page": 1,
      "per_page": 20,
      "total_pages": 0,
      "total_count": 0,
      "has_next": false,
      "has_previous": false
    },
    "message": "No users found matching the specified criteria"
  }
}
```

## Error Responses

**Invalid Parameters (400 Bad Request)**:
```json
{
  "error": {
    "type": "validation_error",
    "code": "INVALID_PARAMETERS",
    "message": "One or more parameters are invalid",
    "details": [
      {
        "parameter": "limit",
        "message": "Must be between 1 and 100",
        "provided_value": "150"
      },
      {
        "parameter": "role",
        "message": "Must be one of: admin, user, moderator",
        "provided_value": "super_admin"
      }
    ]
  }
}
```

## Code Examples

**JavaScript (Fetch API)**:
```javascript
const getUsers = async (filters = {}) => {
  const params = new URLSearchParams({
    page: filters.page || 1,
    limit: filters.limit || 20,
    ...(filters.role && { role: filters.role }),
    ...(filters.status && { status: filters.status }),
    ...(filters.sort && { sort: filters.sort })
  });

  const response = await fetch(`https://api.example.com/api/v1/users?${params}`, {
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json'
    }
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return await response.json();
};

// Usage
const adminUsers = await getUsers({ 
  role: 'admin', 
  status: 'active', 
  page: 1, 
  limit: 10 
});
```

**Python (requests)**:
```python
import requests
from typing import Optional, Dict, Any

def get_users(
    access_token: str,
    page: int = 1,
    limit: int = 20,
    role: Optional[str] = None,
    status: Optional[str] = None,
    sort: Optional[str] = None
) -> Dict[str, Any]:
    
    params = {
        'page': page,
        'limit': limit
    }
    
    if role:
        params['role'] = role
    if status:
        params['status'] = status  
    if sort:
        params['sort'] = sort
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    response = requests.get(
        'https://api.example.com/api/v1/users',
        params=params,
        headers=headers
    )
    
    response.raise_for_status()
    return response.json()

# Usage
users_data = get_users(
    access_token='your_token_here',
    role='admin',
    status='active',
    page=1,
    limit=10
)
```
```

### Example 2: REST API CRUD Operations Suite

**User Request**: "Document full CRUD operations for a product management API"

**Response**:
```markdown
# Product Management API

Complete CRUD operations for managing products in an e-commerce system.

## Base URL
`https://api.shop.com/v1`

## Authentication
All endpoints require API key authentication:
```
Authorization: Bearer YOUR_API_KEY
X-API-Version: 1.0
```

---

## Create Product

**Endpoint**: `POST /products`

### Request Body
```json
{
  "name": "Wireless Bluetooth Headphones",
  "description": "High-quality wireless headphones with noise cancellation",
  "price": 199.99,
  "currency": "USD",
  "category_id": "cat_electronics_001",
  "sku": "WBH-001",
  "inventory": {
    "quantity": 100,
    "track_inventory": true,
    "low_stock_threshold": 10
  },
  "images": [
    "https://cdn.shop.com/products/wbh-001-main.jpg",
    "https://cdn.shop.com/products/wbh-001-side.jpg"
  ],
  "attributes": {
    "color": "Black",
    "brand": "AudioTech",
    "warranty": "2 years"
  },
  "is_active": true
}
```

### Success Response (201 Created)
```json
{
  "data": {
    "id": "prod_1234567890",
    "name": "Wireless Bluetooth Headphones",
    "description": "High-quality wireless headphones with noise cancellation",
    "price": 199.99,
    "currency": "USD",
    "category_id": "cat_electronics_001",
    "sku": "WBH-001",
    "inventory": {
      "quantity": 100,
      "reserved": 0,
      "available": 100,
      "track_inventory": true,
      "low_stock_threshold": 10
    },
    "images": [
      "https://cdn.shop.com/products/wbh-001-main.jpg",
      "https://cdn.shop.com/products/wbh-001-side.jpg"
    ],
    "attributes": {
      "color": "Black",
      "brand": "AudioTech",
      "warranty": "2 years"
    },
    "is_active": true,
    "created_at": "2024-03-15T10:30:00Z",
    "updated_at": "2024-03-15T10:30:00Z"
  }
}
```

---

## Get Product

**Endpoint**: `GET /products/{product_id}`

### Path Parameters
- `product_id` (string, required): The unique identifier for the product

### Success Response (200 OK)
```json
{
  "data": {
    "id": "prod_1234567890",
    "name": "Wireless Bluetooth Headphones",
    "description": "High-quality wireless headphones with noise cancellation",
    "price": 199.99,
    "currency": "USD",
    "category": {
      "id": "cat_electronics_001",
      "name": "Electronics",
      "path": "Electronics > Audio"
    },
    "sku": "WBH-001",
    "inventory": {
      "quantity": 95,
      "reserved": 3,
      "available": 92,
      "track_inventory": true,
      "low_stock_threshold": 10
    },
    "images": [
      "https://cdn.shop.com/products/wbh-001-main.jpg",
      "https://cdn.shop.com/products/wbh-001-side.jpg"
    ],
    "attributes": {
      "color": "Black",
      "brand": "AudioTech",
      "warranty": "2 years"
    },
    "is_active": true,
    "created_at": "2024-03-15T10:30:00Z",
    "updated_at": "2024-03-20T15:45:00Z"
  }
}
```

---

## Update Product

**Endpoint**: `PUT /products/{product_id}`

### Request Body (Partial Updates Supported)
```json
{
  "name": "Premium Wireless Bluetooth Headphones",
  "price": 249.99,
  "inventory": {
    "quantity": 150
  },
  "attributes": {
    "color": "Black",
    "brand": "AudioTech",
    "warranty": "3 years",
    "new_feature": "Active Noise Cancellation"
  }
}
```

### Success Response (200 OK)
```json
{
  "data": {
    "id": "prod_1234567890",
    "name": "Premium Wireless Bluetooth Headphones",
    "price": 249.99,
    "inventory": {
      "quantity": 150,
      "reserved": 3,
      "available": 147,
      "track_inventory": true,
      "low_stock_threshold": 10
    },
    "attributes": {
      "color": "Black",
      "brand": "AudioTech", 
      "warranty": "3 years",
      "new_feature": "Active Noise Cancellation"
    },
    "updated_at": "2024-03-21T09:15:00Z"
  }
}
```

---

## Delete Product

**Endpoint**: `DELETE /products/{product_id}`

### Query Parameters (Optional)
- `force` (boolean): If true, permanently delete. If false (default), soft delete.

### Success Response (204 No Content)
*No response body*

### Soft Delete Response (200 OK)
```json
{
  "data": {
    "id": "prod_1234567890",
    "is_active": false,
    "deleted_at": "2024-03-21T16:30:00Z",
    "message": "Product has been deactivated and can be restored"
  }
}
```

---

## Complete Code Example

**JavaScript Product Manager Class**:
```javascript
class ProductManager {
  constructor(apiKey, baseUrl = 'https://api.shop.com/v1') {
    this.apiKey = apiKey;
    this.baseUrl = baseUrl;
  }

  async request(method, endpoint, data = null) {
    const url = `${this.baseUrl}${endpoint}`;
    const config = {
      method,
      headers: {
        'Authorization': `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json',
        'X-API-Version': '1.0'
      }
    };

    if (data) {
      config.body = JSON.stringify(data);
    }

    const response = await fetch(url, config);
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(`API Error: ${error.message || response.statusText}`);
    }

    return response.status === 204 ? null : await response.json();
  }

  async createProduct(productData) {
    return await this.request('POST', '/products', productData);
  }

  async getProduct(productId) {
    return await this.request('GET', `/products/${productId}`);
  }

  async updateProduct(productId, updates) {
    return await this.request('PUT', `/products/${productId}`, updates);
  }

  async deleteProduct(productId, force = false) {
    const endpoint = force ? `/products/${productId}?force=true` : `/products/${productId}`;
    return await this.request('DELETE', endpoint);
  }
}

// Usage Example
const productManager = new ProductManager('your-api-key-here');

// Create a new product
const newProduct = await productManager.createProduct({
  name: "Gaming Mouse",
  price: 59.99,
  category_id: "cat_gaming_001",
  inventory: { quantity: 50 }
});

// Update the product
await productManager.updateProduct(newProduct.data.id, {
  price: 49