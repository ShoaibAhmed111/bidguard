# BidGuard Boilerplate

Generate the complete project boilerplate and directory setup scripts for "BidGuard AI" (SIH26100: AI-Powered Integrated Bid Compliance Verification Platform for GeM Procurement).

### System Overview:

- Backend: Python 3.11+ FastAPI application handling PDF parsing, gateway abstractions, and deterministic compliance auditing.

- Frontend: Next.js 14+ (App Router), React, Tailwind CSS, Lucide icons, and modern dashboard UI.

- Architecture: Monorepo with separated `backend/` and `frontend/` directories.

### Deliverables to Generate:

1. `backend/requirements.txt`:

   - Include: fastapi, uvicorn[standard], pydantic>=2.0, pydantic-settings, httpx, pymupdf (fitz), rapidfuzz, python-multipart, celery, redis, pytest.

2. `frontend/package.json`:

   - Modern Next.js 14 App Router project setup with TailwindCSS, Lucide-react, Radix UI primitives / shadcn-ready dependencies, and react-pdf / pdfjs-dist.

3. `docker-compose.yml`:

   - Multi-container configuration running:

     - `backend` (FastAPI on port 8000)

     - `frontend` (Next.js on port 3000)

     - `redis` (Cache / async task broker on port 6379)

4. `.gitignore`:

   - Comprehensive rules for Python (`__pycache__`, `.venv`, `.env`), Node.js (`node_modules`, `.next`), and OS files.

5. `.env.example`:

   - Standard configuration keys: `APP_ENV=SANDBOX`, `SANDBOX_BASE_URL=http://localhost:8000/api/v1/mock`, `API_SETU_BASE_URL=https://apisetu.gov.in/api/v1`, `REDIS_URL=redis://localhost:6379/0`.

6. Shell initialization script (`init_project.sh`):

   - Bash script to automatically create all directories, touch required empty `__init__.py` files, and print confirmation.

Provide clean, production-grade configuration files ready to be pasted directly into our workspace.

This project was built with [Lovable](https://lovable.dev).

## Build with Lovable

Continue developing this project in the [Lovable editor](https://lovable.dev/projects/093bac1b-cab1-4d39-af0c-1e4bb17a2279).

- **Ship faster**: describe what you want to build and Lovable handles the code.
- **Stay in sync**: every change made in Lovable is committed straight to this repository.
- **Full ownership**: this code is yours. Push to `main` on GitHub and your changes sync back into Lovable, ready for your next prompt.

## Development

Prefer working locally? You need Node.js and npm — [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating).

```sh
git clone <this-repository-url>
cd <repository-name>
npm i
npm run dev
```
