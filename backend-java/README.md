# KneeSense Backend

The Spring Boot application provides the KneeSense APIs, authentication, authorization, MySQL persistence, and communication with the Python ML service. It also serves the web frontend.

## Technology Stack

- Java 21
- Spring Boot 3.5.x
- Spring Security
- Spring Data JPA and Hibernate
- MySQL 8.4
- JWT authentication
- Maven

## Responsibilities

- Patient registration, login, logout, and current-user lookup.
- Account deletion and associated data cleanup.
- Administrator user and doctor–patient assignment management.
- Patient assessment upload, history, and result retrieval.
- Doctor access to assigned patients and clinical reports.
- X-ray format and upload-size validation.
- Server-side communication with the Python ML service.
- CSRF protection and login/report rate limiting.
- Serving the frontend from `src/main/resources/static/`.

## Source Structure

```text
src/main/java/com/kneesense/
├── api/
│   ├── admin/
│   ├── assessment/
│   ├── auth/
│   └── doctor/
├── bootstrap/
├── config/
├── domain/
├── ml/
├── repository/
└── security/
```

Automated backend tests are maintained under `src/test/java/com/kneesense/`.

## Configuration

The application reads configuration from environment variables.

| Variable | Purpose |
|---|---|
| `MYSQL_DATABASE` | MySQL database name |
| `MYSQL_USER` | Database application user |
| `MYSQL_PASSWORD` | Database application password |
| `JWT_SECRET` | JWT signing secret, at least 32 UTF-8 bytes |
| `JWT_EXPIRATION_MS` | JWT lifetime in milliseconds |
| `AUTH_COOKIE_NAME` | Authentication cookie name |
| `COOKIE_SECURE` | Set to `true` when serving through HTTPS |
| `ADMIN_EMAIL` | Optional initial administrator email |
| `ADMIN_PASSWORD` | Optional initial administrator password |
| `ML_CLIENT_MODE` | `mock` or `http` |
| `ML_SERVICE_URL` | Python ML-service base URL |
| `ML_SERVICE_SECRET` | Internal service authentication secret |
| `ML_TIMEOUT_MS` | ML-service request timeout |
| `ASSESSMENT_LIVE_REPORT_LIMIT` | Per-user live-report allowance |
| `ASSESSMENT_LIVE_REPORT_PERIOD` | Per-user allowance refill period |
| `LOGIN_ATTEMPT_LIMIT` | Login attempts allowed per IP |
| `LOGIN_ATTEMPT_PERIOD` | Login allowance refill period |

Never commit actual environment files, passwords, tokens, or API keys.

## Run with Docker Compose

The recommended full-stack setup is described in the [root README](../README.md).

From the repository root:

```powershell
docker compose --env-file .env.kneesense up -d --build backend-java
```

The backend is available at:

- Frontend: http://localhost:8080/
- Health endpoint: http://localhost:8080/api/health

## Run Locally with Maven

Start MySQL first. Load the required variables from the root `.env.kneesense` file into the current PowerShell process.

From this directory:

```powershell
mvn clean test
mvn spring-boot:run
```

The default local ML client mode is `mock`. Set `ML_CLIENT_MODE=http` with the correct ML-service URL and shared secret when testing real inference integration.

Hibernate uses `ddl-auto=validate`. Database tables are managed through `db/schema.sql`; Hibernate does not automatically create or modify the schema.

## Security and Data Handling

- Passwords are stored using BCrypt.
- JWTs are stored in HttpOnly, SameSite=Lax cookies.
- State-changing requests require CSRF protection.
- User roles are loaded from the database during authentication.
- Patients can access only their own assessment records.
- Doctors can access clinical reports only for assigned patients.
- Administrators manage users and assignments but do not receive clinician reports through the doctor API.
- Uploaded X-ray bytes are not retained as image files or stored in the database.
- Account deletion removes associated records through database foreign-key cascades.

## Rate Limits

The current in-memory settings are:

| Operation | Limit |
|---|---:|
| Login attempts | 5 per minute per IP |
| Per-user live reports | 10 per 24 hours |
| Python global live reports | 200 per rolling 24 hours |

These limits are process-local and reset when the relevant service restarts. They are not distributed across multiple instances.

See [known limitations](../docs/known-limitations.md) for the pending Java–Python cached-report handoff.