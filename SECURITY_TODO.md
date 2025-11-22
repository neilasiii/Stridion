# Security TODO List

**Status**: ⚠️ **NOT PRODUCTION READY**

This document outlines critical security improvements required before production deployment.

---

## 🔴 CRITICAL - Must Fix Before Production

### 1. Authentication & Authorization

**Current State**: ❌ No authentication implemented
**Risk Level**: CRITICAL
**Impact**: Anyone can access and modify all athlete data

**Required Actions**:

```python
# Implement JWT-based authentication

from flask_httpauth import HTTPTokenAuth
from functools import wraps

auth = HTTPTokenAuth(scheme='Bearer')

@auth.verify_token
def verify_token(token):
    """Verify JWT token and return user object."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        user_id = payload['user_id']
        return get_user_by_id(user_id)
    except jwt.InvalidTokenError:
        return None

@auth.get_user_roles
def get_user_roles(user):
    """Return user roles for authorization."""
    return user.roles

# Protect endpoints
@api_v1.route('/settings/<category>', methods=['PUT'])
@auth.login_required
def update_settings_category(category):
    current_user = auth.current_user()
    # Verify user owns this athlete_id
    if not user_can_modify_athlete(current_user, athlete_id):
        return jsonify({'error': 'Forbidden'}), 403
    ...
```

**Resources**:
- Flask-HTTPAuth: https://flask-httpauth.readthedocs.io/
- JWT: https://pyjwt.readthedocs.io/

**Estimated Effort**: 2-3 days

---

### 2. CSRF Protection

**Current State**: ❌ No CSRF tokens on state-changing operations
**Risk Level**: CRITICAL
**Impact**: Cross-site request forgery attacks possible

**Required Actions**:

```python
# Add Flask-WTF for CSRF protection

from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect(app)

# Exempt API endpoints from CSRF if using token auth
@api_v1.before_request
def check_csrf():
    if request.method in ['POST', 'PUT', 'DELETE']:
        # If using Bearer token, skip CSRF
        if request.headers.get('Authorization'):
            return
        # Otherwise, require CSRF token
        csrf.protect()
```

**Frontend Update**:
```javascript
// Include CSRF token in all requests
fetch('/api/v1/settings/training', {
    method: 'PUT',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCSRFToken()  // Get from meta tag or cookie
    },
    body: JSON.stringify(data)
});
```

**Estimated Effort**: 1 day

---

### 3. Rate Limiting

**Current State**: ❌ No rate limiting on any endpoints
**Risk Level**: HIGH
**Impact**: DoS attacks, brute force, API abuse

**Required Actions**:

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# Apply stricter limits to expensive operations
@api_v1.route('/settings/calculate-vdot', methods=['POST'])
@limiter.limit("10 per minute")
def calculate_vdot():
    ...

@api_v1.route('/settings/<category>', methods=['PUT'])
@limiter.limit("30 per minute")
def update_settings_category(category):
    ...
```

**Estimated Effort**: 1 day

---

## ⚠️ HIGH PRIORITY - Should Fix Soon

### 4. Environment Variable Security

**Current State**: ⚠️ Partial - .env.example exists but need verification
**Risk Level**: HIGH
**Impact**: Credential exposure if .env is committed

**Required Actions**:
1. Verify .env is in .gitignore
2. Add .env.local, .env.*.local patterns
3. Use secrets management in production (AWS Secrets Manager, HashiCorp Vault)
4. Never log sensitive environment variables

**Verification**:
```bash
# Check .gitignore includes .env
grep "^\.env$" .gitignore

# Ensure no .env files in git history
git log --all --full-history -- .env
```

**Estimated Effort**: 2 hours

---

### 5. Input Sanitization for JSON Fields

**Current State**: ⚠️ Validated structure, but not sanitized
**Risk Level**: MEDIUM-HIGH
**Impact**: XSS, JSON injection attacks

**Required Actions**:

```python
import bleach

def sanitize_json_field(data):
    """Sanitize JSON fields to prevent XSS."""
    if isinstance(data, str):
        return bleach.clean(data, strip=True)
    elif isinstance(data, dict):
        return {k: sanitize_json_field(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_json_field(item) for item in data]
    return data

# Apply before database storage
sanitized_data = sanitize_json_field(validated_data)
```

**Estimated Effort**: 1 day

---

### 6. HTTPS Enforcement

**Current State**: ❌ Not enforced
**Risk Level**: HIGH (in production)
**Impact**: Man-in-the-middle attacks, credential theft

**Required Actions**:

```python
from flask_talisman import Talisman

# Force HTTPS in production
if not app.config['TESTING']:
    Talisman(app, content_security_policy=None)
```

**Estimated Effort**: 1 hour

---

## 🟡 MEDIUM PRIORITY - Recommended

### 7. SQL Injection (Status: ✅ Mitigated via ORM)

**Current State**: ✅ Using SQLAlchemy ORM with parameterized queries
**Risk Level**: LOW (if ORM usage is consistent)
**Impact**: Database compromise if raw SQL is used

**Best Practices**:
- ✅ Always use ORM methods (filter_by, query)
- ❌ NEVER use string concatenation for SQL
- ⚠️ Review any use of `execute()` or raw SQL

**Code Review Checklist**:
```bash
# Search for potentially dangerous patterns
grep -r "execute(" src/
grep -r "raw_sql" src/
grep -r "text(" src/
```

---

### 8. Session Security

**Current State**: ❌ Not implemented (no sessions yet)
**Risk Level**: MEDIUM (when auth is added)

**Required Actions** (when implementing auth):

```python
app.config.update(
    SESSION_COOKIE_SECURE=True,      # HTTPS only
    SESSION_COOKIE_HTTPONLY=True,    # No JavaScript access
    SESSION_COOKIE_SAMESITE='Lax',   # CSRF protection
    PERMANENT_SESSION_LIFETIME=timedelta(hours=24)
)
```

**Estimated Effort**: 1 hour (when adding auth)

---

### 9. CORS Configuration

**Current State**: ⚠️ Needs review
**Risk Level**: MEDIUM
**Impact**: Unauthorized cross-origin requests

**Required Actions**:

```python
from flask_cors import CORS

# Restrict origins in production
if app.config['ENV'] == 'production':
    CORS(app, origins=['https://yourdomain.com'])
else:
    CORS(app)  # Permissive for development
```

**Estimated Effort**: 1 hour

---

### 10. Error Information Disclosure

**Current State**: ⚠️ Returning detailed error messages
**Risk Level**: MEDIUM
**Impact**: Information leakage to attackers

**Required Actions**:

```python
# Don't expose internal errors in production
@app.errorhandler(Exception)
def handle_error(e):
    if app.config['ENV'] == 'production':
        logger.error(f"Internal error: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500
    else:
        # In development, show detailed errors
        return jsonify({'error': str(e)}), 500
```

**Estimated Effort**: 2 hours

---

## 💡 NICE TO HAVE - Security Enhancements

### 11. Security Headers

Add security headers using Talisman or custom middleware:

```python
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response
```

---

### 12. Audit Logging

Log all sensitive operations:

```python
def audit_log(user_id, action, resource, details=None):
    """Log security-relevant actions."""
    logger.info(
        f"AUDIT: user={user_id} action={action} resource={resource} details={details}",
        extra={
            'user_id': user_id,
            'action': action,
            'resource': resource,
            'ip': request.remote_addr,
            'timestamp': datetime.utcnow()
        }
    )

# Example usage
@api_v1.route('/settings/<category>', methods=['PUT'])
@auth.login_required
def update_settings_category(category):
    ...
    audit_log(current_user.id, 'UPDATE', f'settings.{category}', data)
    ...
```

---

### 13. Dependency Vulnerability Scanning

Set up automated vulnerability scanning:

```bash
# Add to CI/CD pipeline
pip install safety
safety check

# Or use GitHub Dependabot
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
```

---

### 14. Database Connection Security

```python
# Use connection pooling with limits
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Test connections before use
    pool_recycle=3600    # Recycle connections every hour
)

# Use SSL for database connections in production
if app.config['ENV'] == 'production':
    engine = create_engine(
        DATABASE_URL,
        connect_args={'sslmode': 'require'}
    )
```

---

## 📋 Pre-Production Security Checklist

Before deploying to production, verify:

- [ ] Authentication implemented (JWT or session-based)
- [ ] Authorization checks on all endpoints
- [ ] CSRF protection enabled
- [ ] Rate limiting configured
- [ ] HTTPS enforced
- [ ] Security headers added
- [ ] Error messages sanitized (no stack traces)
- [ ] CORS properly configured
- [ ] Environment variables secured
- [ ] Database connections use SSL
- [ ] All secrets in secrets manager (not .env)
- [ ] Audit logging implemented
- [ ] Dependency vulnerabilities scanned
- [ ] Penetration testing completed
- [ ] Security review by external party

---

## 🔍 Security Testing

### Automated Testing

```bash
# Install security testing tools
pip install bandit safety

# Run security linter
bandit -r src/

# Check dependencies for known vulnerabilities
safety check

# SQL injection testing
sqlmap -u "http://localhost:5000/api/v1/settings/training"
```

### Manual Testing

1. **Authentication Bypass**: Try accessing endpoints without token
2. **CSRF**: Try cross-site form submissions
3. **SQL Injection**: Test with malicious input (`'; DROP TABLE--`)
4. **XSS**: Test with `<script>alert('XSS')</script>`
5. **Rate Limiting**: Flood endpoints with requests
6. **Authorization**: Try accessing other users' data

---

## 📚 Resources

- OWASP Top 10: https://owasp.org/www-project-top-ten/
- Flask Security Best Practices: https://flask.palletsprojects.com/en/2.3.x/security/
- NIST Cybersecurity Framework: https://www.nist.gov/cyberframework

---

**Last Updated**: 2025-11-22
**Next Review**: Before production deployment
**Owner**: Development Team

**IMPORTANT**: This application is NOT production-ready until all CRITICAL and HIGH priority items are addressed.
