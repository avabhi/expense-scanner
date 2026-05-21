# 🧾 Expense Scanner Backend

An AI-powered asynchronous receipt info extraction and processing system. The backend allows users to upload receipt images securely, process them using LangGraph & OpenAI Vision, store the extracted line items and merchant information in PostgreSQL, and stream extraction status in real-time via Server-Sent Events (SSE).

---

## 🛠️ Architecture

The system consists of the following components:

- **FastAPI Application**: Serves the REST API endpoints and streams real-time updates via Server-Sent Events (SSE).
- **Celery Worker**: Processes receipt images asynchronously in the background.
- **LangGraph Agent**: A structured extraction graph that invokes OpenAI Vision (`gpt-4o`) to extract merchant metadata and individual line items (price, description) from receipt images.
- **MinIO**: A local S3-compatible object storage mock used for storing receipt images during development.
- **PostgreSQL**: Stores receipt records, processing status, and final extracted structured data.
- **Redis**: Serves as the Celery message broker and backing store for Server-Sent Events (SSE) Pub/Sub channels.

---

## 🚀 Getting Started

### Prerequisites

- [Docker](https://www.docker.com/) and [Docker Compose](https://docs.docker.com/compose/)
- An **OpenAI API Key** (for Vision LLM processing)

### Environment Configuration

Create a `.env` file in the root directory by copying the example:

```bash
cp .env.example .env
```

Edit the `.env` file and insert your `OPENAI_API_KEY`:

```env
OPENAI_API_KEY="your-actual-openai-api-key"
```

*Note: The remaining default values are pre-configured to run out of the box with the local Docker Compose environment.*

---

## 📦 Running the Application (Docker Compose)

Start the entire stack using Docker Compose:

```bash
docker compose up -d
```

This will spin up:
1. **PostgreSQL** (`port 5432`)
2. **Redis** (`port 6379`)
3. **MinIO** (`ports 9000 & 9001` for console)
4. **FastAPI Web Server** (`port 8000`)
5. **Celery Background Worker**

*Note: Database migrations (`alembic upgrade head`) and S3 bucket initialization are run automatically during startup.*

To stop the containers:

```bash
docker compose down
```

---

## 🔌 API Endpoints & Usage Guide

### 1. Get Presigned Upload URL
Before uploading a receipt, request a secure presigned upload URL from the server.

* **Endpoint**: `GET /api/v1/receipts/upload-url`
* **Query Parameter**: `filename` (e.g. `receipt.jpg`)
* **Example Request**:
  ```bash
  curl -s "http://localhost:8000/api/v1/receipts/upload-url?filename=my_receipt.jpg"
  ```
* **Example Response**:
  ```json
  {
    "url": "http://localhost:9000/expense-scanner-receipts",
    "fields": {
      "acl": "private",
      "key": "receipts/a48357e5-9b81-40e9-a2b2-cbf40a66bce5-my_receipt.jpg",
      "AWSAccessKeyId": "mock_key",
      "policy": "...",
      "signature": "..."
    },
    "object_key": "receipts/a48357e5-9b81-40e9-a2b2-cbf40a66bce5-my_receipt.jpg"
  }
  ```

### 2. Upload Image to MinIO / S3
Use the returned `url` and `fields` from the previous endpoint to upload the image directly to object storage via a `POST` form upload.

* **Example Upload Command**:
  ```bash
  curl -X POST \
    -F "acl=private" \
    -F "key=receipts/a48357e5-9b81-40e9-a2b2-cbf40a66bce5-my_receipt.jpg" \
    -F "AWSAccessKeyId=mock_key" \
    -F "policy=..." \
    -F "signature=..." \
    -F "file=@/path/to/my_receipt.jpg" \
    http://localhost:9000/expense-scanner-receipts
  ```

### 3. Submit for Processing (Idempotent Ingestion)
Once the image is uploaded, trigger the asynchronous AI ingestion.

* **Endpoint**: `POST /api/v1/receipts/`
* **Payload**:
  ```json
  {
    "object_key": "receipts/a48357e5-9b81-40e9-a2b2-cbf40a66bce5-my_receipt.jpg",
    "file_hash": "a-sha256-hash-of-file-contents"
  }
  ```
* **Example Request**:
  ```bash
  curl -X POST "http://localhost:8000/api/v1/receipts/" \
    -H "Content-Type: application/json" \
    -d '{"object_key": "receipts/a48357e5-9b81-40e9-a2b2-cbf40a66bce5-my_receipt.jpg", "file_hash": "sha256hash123456"}'
  ```
* **Example Response**:
  ```json
  {
    "id": 1,
    "object_key": "receipts/a48357e5-9b81-40e9-a2b2-cbf40a66bce5-my_receipt.jpg",
    "status": "pending",
    "task_id": "84be2cf7-f831-4e78-9e5b-21d3f9ab01cd"
  }
  ```

### 4. Listen to Real-time Extraction Status (SSE)
You can subscribe to real-time progress updates for a background job using Server-Sent Events.

* **Endpoint**: `GET /api/v1/receipts/status/{task_id}`
* **Example Command**:
  ```bash
  curl -N http://localhost:8000/api/v1/receipts/status/84be2cf7-f831-4e78-9e5b-21d3f9ab01cd
  ```
* **Status Steps**:
  1. `start` - Generating secure link to access receipt image.
  2. `agent_start` - Vision AI starting extraction.
  3. `saving` - AI extraction successful. Saving data.
  4. `done` - Receipt processed successfully!

---

## ⚙️ Development Features

- **Anonymous Volume Virtualenv**: The `docker-compose.yml` mounts the project directory for hot-reloading (`web` service) while ensuring your host machine's virtual environment (`.venv`) does not override the containerized Linux virtual environment.
- **Base64 OpenAI Vision Fallback**: In development mode, the worker downloads receipt files locally from MinIO and converts them to base64 data URLs before sending them to the OpenAI API, bypassing S3 public access requirements.
- **Database Migrations**: Alembic is integrated with FastAPI. Any modifications to SQLAlchemy models can be migrated easily:
  ```bash
  docker compose run web alembic revision --autogenerate -m "description"
  docker compose run web alembic upgrade head
  ```
