# Installation Guide

This guide provides instructions for installing and configuring the AI Music Mastering API. For a general overview of the project, please see the [README.md](README.md).

## Prerequisites

Before you begin, ensure you have the following installed:

- Docker and Docker Compose
- Python 3.11+
- NVIDIA GPU (recommended for AI models)
- 16GB+ RAM

## Development Setup

Follow these steps to set up a local development environment:

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-org/ai-music-mastering-chain.git
    cd ai-music-mastering-chain
    ```

2.  **Install dependencies:**
    ```bash
    python -m pip install -r requirements.txt
    ```

3.  **Set up environment variables:**
    Create a `.env` file in the root directory of the project. You can copy the example file as a starting point:
    ```bash
    cp .env.example .env
    ```
    Edit the `.env` file with your specific configuration. Refer to the [Configuration](#configuration) section for details on each variable. Key variables to set for development include:
    *   `DATABASE_URL`: Defines the connection string for your PostgreSQL database. The `docker-compose.yml` sets this up as `postgresql+asyncpg://musicapp:musicapp123@db:5432/musicapp`.
    *   `REDIS_URL`: Defines the connection string for your Redis instance. The `docker-compose.yml` sets this up as `redis://redis:6379/0`.
    *   `SECRET_KEY`: A secret key for signing JWTs. Generate a strong random key.
    *   `DEBUG`: Set to `True` for development to enable debug features.
    *   API keys for any external AI services you plan to use (e.g., `OPENAI_API_KEY`, `STABILITY_API_KEY`).

4.  **Start the development environment:**
    This command will build the Docker images and start the services defined in `docker-compose.yml` (API, database, Redis).
    ```bash
    docker-compose up -d
    ```

5.  **Initialize the database:**
    Run database migrations to set up the schema.
    ```bash
    docker-compose exec api alembic upgrade head
    ```
    *Note: If you are not using the provided Docker setup for the API service (e.g., running the Python backend directly on your host), you would run `python -m alembic upgrade head` or `alembic upgrade head` (if alembic is on your PATH) in your activated Python environment.*


6.  **Access the application:**
    *   API Documentation: [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs)
    *   The `docker-compose.yml` also includes commented-out services for Grafana (monitoring) and Prometheus (metrics). If you enable them:
        *   Grafana Monitoring: `http://localhost:3000` (default admin/admin)
        *   Prometheus Metrics: `http://localhost:9090`

## Production Deployment

For production environments, it's recommended to deploy the application using Kubernetes.

### 1. Kubernetes Deployment

You can deploy the application to a Kubernetes cluster using the provided manifest files:

```bash
kubectl apply -f kubernetes/
```
This will create the necessary deployments, services, and other resources defined in the `kubernetes/` directory. Ensure your Kubernetes cluster is configured correctly and has access to pull the required Docker images. You will also need to manage secrets (like API keys and database credentials) securely within Kubernetes.

### 2. Helm Chart (Recommended)

A Helm chart is provided for a more configurable and manageable deployment:

```bash
helm install ai-music-mastering ./helm-chart --values ./helm-chart/values.yaml
```
Customize the deployment by modifying the `values.yaml` file within the `helm-chart` directory or by using the `--set` flag during installation. The Helm chart typically handles the creation of necessary Kubernetes resources, including secrets management and configurable service exposure.

## Configuration

The application is configured using environment variables. These can be set in a `.env` file in the project root for local development or managed through your deployment environment (e.g., Kubernetes secrets, Docker environment variables).

The following table lists the available environment variables, their default values (if any, as defined in `app/core/config.py`), and a description of their purpose:

| Variable                      | Default Value                               | Description                                                                                                |
| ----------------------------- | ------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| `APP_NAME`                    | "AI Music Mastering API"                    | The name of the application.                                                                               |
| `DEBUG`                       | `False`                                     | Set to `True` to enable debug mode, providing more verbose error messages. Should be `False` in production. |
| `ENVIRONMENT`                 | "development"                               | The deployment environment (e.g., "development", "staging", "production").                                   |
| `SECRET_KEY`                  | "your-secret-key-change-in-production"      | A secret key used for cryptographic signing (e.g., JWTs). **Must be changed to a strong, unique value.**   |
| `API_V1_STR`                  | "/api/v1"                                   | The prefix for version 1 of the API.                                                                       |
| `HOST`                        | "0.0.0.0"                                   | The host address the application server will bind to.                                                      |
| `PORT`                        | `8000`                                      | The port the application server will listen on.                                                            |
| `ALLOWED_HOSTS`               | `["*"]`                                     | A list of allowed host headers. Can be a comma-separated string or a JSON-style list.                      |
| `DATABASE_URL`                | "sqlite+aiosqlite:///./music_mastering.db"  | The connection string for the database. For PostgreSQL with Docker Compose: `postgresql+asyncpg://musicapp:musicapp123@db:5432/musicapp`. |
| `DB_POOL_SIZE`                | `5`                                         | The number of database connections to keep in the pool.                                                    |
| `DB_MAX_OVERFLOW`             | `10`                                        | The maximum number of connections that can be opened beyond `DB_POOL_SIZE`.                                  |
| `REDIS_URL`                   | "redis://localhost:6379/0"                  | The connection string for Redis, used for caching and sessions. For Docker Compose: `redis://redis:6379/0`. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30`                                        | The lifespan of an access token in minutes.                                                                |
| `REFRESH_TOKEN_EXPIRE_DAYS`   | `7`                                         | The lifespan of a refresh token in days.                                                                   |
| `ALGORITHM`                   | "HS256"                                     | The algorithm used for signing JWTs.                                                                       |
| `PASSWORD_MIN_LENGTH`         | `8`                                         | Minimum length required for user passwords.                                                                |
| `PASSWORD_REQUIRE_UPPERCASE`  | `True`                                      | Whether user passwords must contain at least one uppercase letter.                                         |
| `PASSWORD_REQUIRE_LOWERCASE`  | `True`                                      | Whether user passwords must contain at least one lowercase letter.                                         |
| `PASSWORD_REQUIRE_DIGITS`     | `True`                                      | Whether user passwords must contain at least one digit.                                                    |
| `PASSWORD_REQUIRE_SPECIAL`    | `False`                                     | Whether user passwords must contain at least one special character.                                        |
| `RATE_LIMIT_PER_MINUTE`       | `60`                                        | Maximum number of requests allowed per minute per user.                                                    |
| `RATE_LIMIT_PER_HOUR`         | `1000`                                      | Maximum number of requests allowed per hour per user.                                                      |
| `RATE_LIMIT_PER_DAY`          | `10000`                                     | Maximum number of requests allowed per day per user.                                                       |
| `MAX_UPLOAD_SIZE`             | `104857600` (100MB)                         | Maximum allowed size for uploaded files in bytes.                                                          |
| `ALLOWED_AUDIO_TYPES`         | `["audio/mpeg", "audio/wav", ...]`          | A list of allowed MIME types for audio uploads.                                                            |
| `UPLOAD_PATH`                 | "uploads"                                   | Directory where uploaded files are stored (if `STORAGE_PROVIDER` is "local").                              |
| `TEMP_PATH`                   | "temp"                                      | Directory for temporary file storage during processing.                                                    |
| `AI_MODEL_PATH`               | "models"                                    | Path to AI model files (if applicable, depends on model integration).                                      |
| `MAX_PROCESSING_TIME`         | `3600` (1 hour)                             | Maximum time allowed for an AI processing job in seconds.                                                  |
| `MAX_CONCURRENT_JOBS`         | `5`                                         | Maximum number of concurrent AI processing jobs.                                                           |
| `OPENAI_API_KEY`              | `None`                                      | API key for OpenAI services.                                                                               |
| `ANTHROPIC_API_KEY`           | `None`                                      | API key for Anthropic services.                                                                            |
| `HUGGINGFACE_API_KEY`         | `None`                                      | API key for Hugging Face services.                                                                         |
| `STABILITY_API_KEY`           | `None`                                      | API key for Stability AI services.                                                                         |
| `GOOGLE_AI_API_KEY`           | `None`                                      | API key for Google AI services.                                                                            |
| `REPLICATE_API_TOKEN`         | `None`                                      | API token for Replicate services.                                                                          |
| `MAGENTA_API_KEY`             | `None`                                      | API key for Magenta (if applicable).                                                                       |
| `TEPAND_API_KEY`              | `None`                                      | API key for Tepand (if applicable).                                                                        |
| `ACES_API_KEY`                | `None`                                      | API key for ACES (if applicable).                                                                          |
| `SUNI_API_KEY`                | `None`                                      | API key for Suni (if applicable).                                                                          |
| `BEETHOVEN_API_KEY`           | `None`                                      | API key for Beethoven AI (if applicable).                                                                  |
| `MUREKA_API_KEY`              | `None`                                      | API key for Mureka (if applicable).                                                                        |
| `LANDR_API_KEY`               | `None`                                      | API key for LANDR services.                                                                                |
| `SMTP_TLS`                    | `True`                                      | Whether to use TLS for SMTP connections.                                                                   |
| `SMTP_PORT`                   | `587`                                       | Port for the SMTP server.                                                                                  |
| `SMTP_HOST`                   | `None`                                      | Hostname or IP address of the SMTP server.                                                                 |
| `SMTP_USER`                   | `None`                                      | Username for SMTP authentication.                                                                          |
| `SMTP_PASSWORD`               | `None`                                      | Password for SMTP authentication.                                                                          |
| `EMAILS_FROM_EMAIL`           | `None`                                      | The "From" email address for outgoing emails.                                                              |
| `EMAILS_FROM_NAME`            | `None`                                      | The "From" name for outgoing emails.                                                                       |
| `STORAGE_PROVIDER`            | "local"                                     | Storage provider for files ("local", "s3", "gcs", "azure").                                                |
| `AWS_ACCESS_KEY_ID`           | `None`                                      | AWS Access Key ID (if `STORAGE_PROVIDER` is "s3").                                                         |
| `AWS_SECRET_ACCESS_KEY`       | `None`                                      | AWS Secret Access Key (if `STORAGE_PROVIDER` is "s3").                                                     |
| `AWS_S3_BUCKET`               | `None`                                      | Name of the AWS S3 bucket (if `STORAGE_PROVIDER` is "s3").                                                 |
| `AWS_REGION`                  | "us-east-1"                                 | AWS region for S3 bucket (if `STORAGE_PROVIDER` is "s3").                                                  |
| `CDN_URL`                     | `None`                                      | Base URL for a Content Delivery Network (if used).                                                         |
| `LOG_LEVEL`                   | "INFO"                                      | Logging level (e.g., "DEBUG", "INFO", "WARNING", "ERROR").                                                 |
| `SENTRY_DSN`                  | `None`                                      | Sentry DSN for error tracking.                                                                             |

**Note on Subscription Tier Limits:**
The `FREE_TIER_LIMITS`, `PREMIUM_TIER_LIMITS`, and `PRO_TIER_LIMITS` are dictionaries defined in the settings but are not directly set via individual environment variables. Their default structures are:
```python
# Example: FREE_TIER_LIMITS
{
    "api_calls": 100,         # Max API calls
    "file_size_mb": 10,       # Max file size in MB
    "concurrent_sessions": 1, # Max concurrent sessions
    "storage_gb": 1           # Max storage in GB
}
```
These are typically managed within the application code or a separate configuration system if they need to be dynamically changed without code deployment.
