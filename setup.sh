#!/bin/bash

echo "Setting up AI Backend..."

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env file from template. Please update with your configuration."
fi

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements-api.txt -r requirements-worker.txt

echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Start MongoDB and Redis (using Docker or locally installed)"
echo "2. Update .env file with your configuration"
echo "3. Run: python main.py"
echo "4. In another terminal, run: celery -A src.infrastructure.queue.celery_queue_service worker --loglevel=info"
