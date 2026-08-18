# Security Policy - DevJourney

## Reporting Vulnerabilities

If you discover a security vulnerability, please report it responsibly:

1. **DO NOT** open a public GitHub issue
2. Email the maintainers with details of the vulnerability
3. Include steps to reproduce the issue
4. Allow reasonable time for a fix before public disclosure

## Security Measures

### Authentication
- Passwords hashed with Argon2id (memory-hard, salted)
- Legacy SHA-256 hashes auto-upgraded to Argon2 on login
- Session tokens: 256-bit random, stored in HttpOnly/Secure/SameSite=Lax cookies
- Sessions expire after 24 hours
- Expired sessions cleaned up on startup and hourly

### Authorization
- All data-modification endpoints require authentication
- All queries filtered by `user_id` to prevent IDOR
- Session tokens validated on every request

### HTTP Security Headers
- `Content-Security-Policy`: restricts script/style/connect/frame sources
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: camera=(), microphone=(), geolocation=()`
- `Cross-Origin-Opener-Policy: same-origin`
- `Cross-Origin-Resource-Policy: same-origin`
- `Strict-Transport-Security` (production only): max-age=31536000; includeSubDomains; preload

### Rate Limiting
- Login: 10 attempts per 15 minutes per IP
- Registration: 5 attempts per hour per IP
- General: 120 requests per minute per IP

### Input Validation
- Username: regex-validated (3-30 chars, alphanumeric + underscore)
- Email: regex-validated
- Password: minimum 6 characters
- File uploads: 1 MB max size, 500 lines max for imports
- Numeric inputs: bounds-checked
- Enum fields: whitelist-validated

### Database
- SQLAlchemy ORM (parameterized queries)
- Foreign keys with CASCADE/SET NULL
- Unique constraints on critical fields
- Database user should have least-privilege permissions

### Cookie Security
- `HttpOnly`: prevents JavaScript access
- `Secure`: HTTPS-only (production)
- `SameSite=Lax`: CSRF protection for most attacks
- `Max-Age`: 86400 seconds (24 hours)

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | Yes (production) | Random secret for session signing (min 32 bytes hex) |
| `DATABASE_URL` | Yes (production) | PostgreSQL connection string |
| `PORT` | No | Server port (default: 8000) |
| `RENDER` | Auto-set | Set by Render.com platform |

**NEVER commit `.env` files to version control.**

## Production Checklist

- [ ] Set strong `SECRET_KEY` (generate with `python -c "import secrets; print(secrets.token_hex(32))"`)
- [ ] Set `DATABASE_URL` to PostgreSQL
- [ ] Enable HTTPS (via reverse proxy or platform)
- [ ] Disable debug mode
- [ ] Remove `/docs` and `/redoc` endpoints (auto-disabled in production)
- [ ] Set secure CORS policies if needed
- [ ] Configure backup for database
- [ ] Monitor logs for suspicious activity

## Development

- SQLite used for local development (data ephemeral)
- Debug endpoints available at `/docs` and `/redoc`
- Rate limits apply in development too

## Dependencies

Audit dependencies regularly:
```bash
pip-audit
# or
safety check
```

## Known Limitations

- No account lockout after failed passwords (rate limiting mitigates)
- No email verification on registration
- No password reset functionality
- No 2FA/MFA
- No audit log of user actions
- CSRF protection relies on SameSite cookies (not CSRF tokens)
