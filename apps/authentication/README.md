# Authentication System Documentation

## Overview

This authentication system provides JWT-based authentication for admin users in the Escape Rooms booking system. It includes access tokens, refresh tokens, and middleware for protecting admin endpoints.

## Features

- **JWT Access Tokens**: Short-lived tokens (15 minutes) for API access
- **JWT Refresh Tokens**: Long-lived tokens (7 days) for obtaining new access tokens
- **Staff-Only Access**: Only users with `is_staff=True` can authenticate
- **Automatic Token Management**: Refresh tokens are stored in database and can be revoked
- **Secure Middleware**: Easy-to-use authentication middleware for protecting endpoints

## API Endpoints

### POST /api/auth/login
Authenticate admin user and return JWT tokens.

**Request:**
```json
{
  "username": "admin",
  "password": "password123"
}
```

**Response (200):**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "Bearer",
  "expires_in": 900
}
```

**Error Response (401):**
```json
{
  "error": "invalid_credentials",
  "message": "Invalid username or password"
}
```

### POST /api/auth/refresh
Refresh access token using refresh token.

**Request:**
```json
{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Response (200):**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "Bearer",
  "expires_in": 900
}
```

### POST /api/auth/logout
Logout user by deactivating all refresh tokens.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200):**
```json
{
  "message": "Successfully logged out"
}
```

### GET /api/auth/me
Get current user information.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200):**
```json
{
  "id": 1,
  "username": "admin",
  "email": "admin@example.com",
  "is_staff": true,
  "is_superuser": true
}
```

## Usage in API Endpoints

### Protecting Endpoints

To protect an endpoint with JWT authentication, import and use the `jwt_auth` middleware:

```python
from apps.authentication.middleware import jwt_auth
from ninja import Router

router = Router()

@router.get("/admin/reservations/", auth=jwt_auth)
def list_reservations_admin(request):
    """Admin-only endpoint"""
    user = request.auth  # Authenticated user object
    return {"message": f"Hello {user.username}"}
```

### Access User Information

In protected endpoints, the authenticated user is available as `request.auth`:

```python
@router.get("/admin/profile/", auth=jwt_auth)
def get_admin_profile(request):
    user = request.auth
    return {
        "username": user.username,
        "email": user.email,
        "is_superuser": user.is_superuser
    }
```

## Token Structure

### Access Token Claims
```json
{
  "user_id": 1,
  "username": "admin",
  "is_staff": true,
  "is_superuser": true,
  "exp": 1755749191,
  "iat": 1755748291,
  "type": "access"
}
```

### Refresh Token Claims
```json
{
  "token_id": "25c285c4-d4f6-40f3-9d23-ade447c3b979",
  "exp": 1756353091,
  "iat": 1755748291,
  "type": "refresh"
}
```

## Security Features

### Token Expiration
- **Access Tokens**: 15 minutes (short-lived for security)
- **Refresh Tokens**: 7 days (long-lived for convenience)

### Staff-Only Access
Only users with `is_staff=True` can authenticate. Regular users will receive a 401 error.

### Token Revocation
- Refresh tokens are stored in the database and can be deactivated
- Logout deactivates all refresh tokens for the user
- Expired tokens are automatically rejected

### Secure Headers
All protected endpoints require the `Authorization` header:
```
Authorization: Bearer <access_token>
```

## Models

### RefreshToken
Stores refresh tokens in the database for management and revocation.

**Fields:**
- `user`: Foreign key to User model
- `token`: Unique token identifier (UUID string)
- `created_at`: Token creation timestamp
- `expires_at`: Token expiration timestamp
- `is_active`: Boolean flag for token status

**Methods:**
- `is_expired()`: Check if token is expired
- `deactivate()`: Deactivate the token

## Admin Interface

The authentication system includes Django admin integration for managing refresh tokens:

- View all refresh tokens
- Filter by active status and dates
- Deactivate tokens in bulk
- Search by username or token

## Testing

The system includes comprehensive tests:

### Unit Tests (`tests.py`)
- JWT utility functions
- RefreshToken model methods
- API endpoint functionality
- Authentication middleware

### Integration Tests (`integration_tests.py`)
- Complete authentication flow
- Token refresh workflow
- Error handling scenarios
- Security validations

### Admin Endpoint Tests (`admin_endpoint_test.py`)
- Protected endpoint access
- Authentication requirements
- Staff-only restrictions

Run tests with:
```bash
python manage.py test apps.authentication
```

## Error Handling

### Common Error Responses

**Invalid Credentials (401):**
```json
{
  "error": "invalid_credentials",
  "message": "Invalid username or password"
}
```

**Insufficient Permissions (401):**
```json
{
  "error": "insufficient_permissions",
  "message": "User must be staff to access admin panel"
}
```

**Invalid Token (401):**
```json
{
  "error": "invalid_token",
  "message": "Invalid refresh token"
}
```

**Token Expired (401):**
```json
{
  "error": "token_expired",
  "message": "Refresh token has expired"
}
```

## Configuration

### Settings
The system uses Django's `SECRET_KEY` for JWT signing. Ensure this is properly configured in your settings.

### Dependencies
- `PyJWT==2.8.0`: JWT token handling
- `cryptography==41.0.7`: Cryptographic operations

## Best Practices

### Frontend Integration
1. Store access token in memory (not localStorage for security)
2. Store refresh token in httpOnly cookie or secure storage
3. Implement automatic token refresh before expiration
4. Handle 401 responses by redirecting to login

### Security Considerations
1. Always use HTTPS in production
2. Implement proper CORS settings
3. Use secure, random SECRET_KEY
4. Monitor and log authentication attempts
5. Implement rate limiting on auth endpoints

### Token Management
1. Refresh tokens before they expire
2. Handle token refresh failures gracefully
3. Implement proper logout to clear all tokens
4. Monitor refresh token usage for suspicious activity

## Example Frontend Usage

### Login Flow
```javascript
// Login
const response = await fetch('/api/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username, password })
});

const { access_token, refresh_token } = await response.json();

// Store tokens securely
sessionStorage.setItem('access_token', access_token);
// Store refresh_token in httpOnly cookie or secure storage
```

### API Requests
```javascript
// Make authenticated request
const response = await fetch('/api/admin/reservations/', {
  headers: {
    'Authorization': `Bearer ${access_token}`,
    'Content-Type': 'application/json'
  }
});

if (response.status === 401) {
  // Token expired, try to refresh
  await refreshToken();
  // Retry request
}
```

### Token Refresh
```javascript
// Refresh token
const refreshResponse = await fetch('/api/auth/refresh', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ refresh_token })
});

if (refreshResponse.ok) {
  const { access_token } = await refreshResponse.json();
  sessionStorage.setItem('access_token', access_token);
} else {
  // Refresh failed, redirect to login
  window.location.href = '/login';
}
```