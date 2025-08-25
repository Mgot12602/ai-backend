# AI Backend

A scalable AI backend API built with FastAPI, MongoDB, WebSockets, and queue processing following hexagonal architecture.

## Features

- **Hexagonal Architecture**: Clean separation of concerns with domain, application, and infrastructure layers
- **FastAPI**: Modern, fast web framework with automatic API documentation
- **MongoDB**: Document database for flexible data storage
- **Redis + Celery**: Distributed task queue for processing AI jobs
- **WebSockets**: Real-time job status updates
- **Clerk Authentication**: Secure user authentication with JWT tokens
- **S3 Storage**: Artifact storage (supports AWS S3 or MinIO)
- **Docker**: Containerized services for easy deployment

## Architecture

```
src/
├── domain/           # Business logic and entities
│   ├── entities/     # Domain models (User, Job)
│   ├── repositories/ # Repository interfaces
│   └── services/     # Domain services
├── application/      # Use cases and DTOs
│   ├── dto/          # Data Transfer Objects
│   └── use_cases/    # Application logic
├── infrastructure/   # External concerns
│   ├── database/     # MongoDB connection
│   ├── repositories/ # Repository implementations
│   ├── external/     # External services (AI, Storage)
│   ├── queue/        # Celery tasks and queue
│   └── storage/      # S3 storage implementation
├── presentation/     # API and WebSocket endpoints
│   ├── api/          # REST API routes
│   └── websocket/    # WebSocket handlers
└── config/           # Configuration and auth
```

## Quick Start

### 1. Clone and Setup

```bash
git clone https://github.com/Mgot12602/ai-backend.git
cd ai-backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-api.txt -r requirements-worker.txt
```

### 2. Start Services

```bash
# Start MongoDB, Redis, and MinIO
docker-compose up -d

# Copy environment variables
cp .env.example .env
# Edit .env with your configuration
```

### 3. Run the Application

```bash
# Start the API server
python main.py

# In another terminal, start the Celery worker
celery -A src.infrastructure.queue.celery_queue_service worker --loglevel=info
```

## API Endpoints

### Authentication
All endpoints require a Clerk JWT token in the Authorization header:
```
Authorization: Bearer <clerk_token>
```

### Users
- `POST /api/v1/users/` - Create user
- `GET /api/v1/users/me` - Get current user
- `GET /api/v1/users/{user_id}` - Get user by ID
- `PUT /api/v1/users/{user_id}` - Update user

### Jobs
- `POST /api/v1/jobs/` - Create AI job
- `GET /api/v1/jobs/` - Get user's jobs
- `GET /api/v1/jobs/{job_id}` - Get specific job
 

### WebSocket
- `WS /ws/{user_id}?token=<clerk_token>` - Real-time job updates

## Job Types

### Audio Generation
```json
{
  "job_type": "audio_generation",
  "input_data": {
    "text": "Hello world",
    "voice": "default"
  }
}
```

### Text Generation
```json
{
  "job_type": "text_generation",
  "input_data": {
    "prompt": "Generate a story about AI",
    "max_tokens": 100
  }
}
```

### Image Generation
```json
{
  "job_type": "image_generation",
  "input_data": {
    "prompt": "A futuristic city",
    "size": "512x512"
  }
}
```

## Development

### Running Tests
```bash
pytest tests/
```

### Code Structure
The project follows hexagonal architecture principles:

- **Domain Layer**: Contains business entities and rules
- **Application Layer**: Orchestrates domain objects and external services
- **Infrastructure Layer**: Implements external concerns (database, queue, storage)
- **Presentation Layer**: Handles HTTP/WebSocket communication

### Adding New AI Services
1. Implement the `AIService` interface in `src/domain/services/ai_service.py`
2. Create your service in `src/infrastructure/external/`
3. Register it in the dependency injection container

## Configuration

Key environment variables:

- `MONGODB_URL`: MongoDB connection string
- `REDIS_URL`: Redis connection string
- `CLERK_SECRET_KEY`: Clerk authentication key
- `S3_BUCKET_NAME`: S3 bucket for artifacts
- `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`: AWS credentials

## Production Deployment

1. Set up production databases (MongoDB, Redis)
2. Configure proper authentication keys
3. Set up S3 bucket or MinIO instance
4. Use a process manager like supervisord or systemd
5. Set up reverse proxy (nginx)
6. Configure SSL certificates

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes following the hexagonal architecture
4. Add tests for new functionality
5. Submit a pull request

## License

MIT License


## Dev mode
- Docker api is running on DOCKER_API_PORT while local api is running on API_PORT.
- To authorize the swagger api requests set DEV_BEARER_TOKEN to the HTTPBearer value in swagger.