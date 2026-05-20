# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 4.1.x   | ✅ Active support  |
| 4.0.x   | ⚠️ Critical fixes only |
| < 4.0   | ❌ End of life     |

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it responsibly.

### How to Report

1. **DO NOT** create a public GitHub issue for security vulnerabilities.
2. Email the security team with details of the vulnerability.
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact assessment
   - Suggested remediation (if any)

### Response Timeline

- **Acknowledgement**: Within 48 hours
- **Initial assessment**: Within 5 business days
- **Fix release**: Within 15 business days for critical issues

### Scope

The following are in scope:
- Backend API (`backend/`)
- Frontend application (`frontend/`)
- Docker configuration
- Data handling and processing pipelines

### Out of Scope

- Third-party dependencies (report upstream)
- Issues in development/test environments only
- Denial of service via legitimate API usage within rate limits

## Security Measures

This system implements the following security controls:

- **CORS whitelist**: Configurable allowed origins (not wildcard)
- **Upload size limits**: Configurable maximum file size
- **Path traversal protection**: Sanitised file paths on all download endpoints
- **Input validation**: File type and content validation on upload
- **Non-root Docker user**: Backend runs as `appuser` (UID 1001)
- **Security headers**: X-Frame-Options, X-Content-Type-Options, CSP via nginx
- **Rate limiting**: Upload and processing endpoints are rate-limited
