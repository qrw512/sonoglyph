"""Sonoglyph FastAPI application.

Endpoints:
  GET  /                      — simple landing page
  GET  /api/health            — health check
  GET  /api/features          — list of available analyzers
  POST /api/analyze           — upload a file and analyze it
  POST /api/analyze-by-path   — analyze a file by server-side path
  POST /api/batch             — batch analysis over a list of paths
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from sonoglyph import __version__, analyze, analyze_batch
from sonoglyph.analyzers import REGISTRY
from sonoglyph.schemas import AnalysisResult

logger = logging.getLogger(__name__)


class AnalyzeByPathRequest(BaseModel):
    """Request body for analyzing a file by server-side path."""

    path: str = Field(..., description="Path to the file on the server")
    features: list[str] | None = Field(None, description="List of analyzers")
    sr: int = Field(22050, description="Sample rate")
    use_cache: bool = Field(True, description="Use cache")


class BatchRequest(BaseModel):
    """Batch analysis request."""

    paths: list[str] = Field(..., description="List of file paths")
    features: list[str] | None = None
    sr: int = 22050
    use_cache: bool = True


class BatchResponse(BaseModel):
    """Batch analysis response."""

    results: list[AnalysisResult]
    total: int
    errors: list[str] = Field(default_factory=list)


_INDEX_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Sonoglyph API</title>
<style>
body { font-family: ui-sans-serif, system-ui, sans-serif;
       max-width: 720px; margin: 40px auto; padding: 0 20px;
       background: #0f1115; color: #e6e9ef; line-height: 1.6; }
h1 { color: #6ab0ff; }
code { background: #1c2029; padding: 2px 6px; border-radius: 4px;
       font-size: 13px; }
.endpoint { padding: 12px 16px; background: #171a21; border-radius: 6px;
            margin: 8px 0; border-left: 3px solid #6ab0ff; }
.method { display: inline-block; padding: 1px 8px; border-radius: 4px;
          font-weight: 600; font-size: 12px; margin-right: 8px; }
.get { background: #1e40af; }
.post { background: #166534; }
a { color: #6ab0ff; }
</style>
</head>
<body>
<h1>🎵 Sonoglyph API</h1>
<p>Local REST API for analyzing music tracks. Version __VERSION__.</p>

<h2>Endpoints</h2>
<div class="endpoint"><span class="method get">GET</span>
  <code>/api/health</code> — health check</div>
<div class="endpoint"><span class="method get">GET</span>
  <code>/api/features</code> — available analyzers</div>
<div class="endpoint"><span class="method post">POST</span>
  <code>/api/analyze</code> — upload a file (multipart/form-data)</div>
<div class="endpoint"><span class="method post">POST</span>
  <code>/api/analyze-by-path</code> — analyze by server-side path</div>
<div class="endpoint"><span class="method post">POST</span>
  <code>/api/batch</code> — batch analysis</div>

<h2>Documentation</h2>
<p>Interactive OpenAPI docs:
  <a href="/docs">/docs</a> (Swagger UI),
  <a href="/redoc">/redoc</a> (ReDoc).
</p>

<h2>Example</h2>
<pre><code>curl -X POST http://localhost:8000/api/analyze \\
  -F "file=@track.mp3"</code></pre>
</body>
</html>
"""


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Sonoglyph API",
        version=__version__,
        description="Extract musical features from audio files.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def index() -> str:
        return _INDEX_HTML.replace("__VERSION__", __version__)

    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok", "version": __version__}

    @app.get("/api/features")
    def features() -> dict:
        return {"features": sorted(REGISTRY.keys())}

    @app.post("/api/analyze", response_model=AnalysisResult)
    async def analyze_upload(
        file: UploadFile = File(..., description="Audio file"),
        features: str | None = None,
        sr: int = 22050,
    ) -> AnalysisResult:
        """Analyze an uploaded file.

        `features` is an optional CSV string, e.g. 'tempo,mood'.
        """
        suffix = Path(file.filename or "upload").suffix or ".wav"

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = Path(tmp.name)

        try:
            feature_list = (
                [f.strip() for f in features.split(",") if f.strip()]
                if features
                else None
            )
            return analyze(tmp_path, features=feature_list, sr=sr, use_cache=False)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Analyze failed")
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        finally:
            tmp_path.unlink(missing_ok=True)

    @app.post("/api/analyze-by-path", response_model=AnalysisResult)
    def analyze_by_path(req: AnalyzeByPathRequest) -> AnalysisResult:
        p = Path(req.path)
        if not p.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {req.path}")
        try:
            return analyze(
                p, features=req.features, sr=req.sr, use_cache=req.use_cache
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Analyze by path failed")
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/batch", response_model=BatchResponse)
    def batch(req: BatchRequest) -> BatchResponse:
        if not req.paths:
            raise HTTPException(status_code=400, detail="paths must not be empty")

        valid, errors = [], []
        for raw in req.paths:
            p = Path(raw)
            if not p.exists():
                errors.append(f"Not found: {raw}")
            else:
                valid.append(p)

        results = analyze_batch(
            valid,
            features=req.features,
            sr=req.sr,
            use_cache=req.use_cache,
        )
        return BatchResponse(results=results, total=len(results), errors=errors)

    return app


# uvicorn sonoglyph.server.app:app --reload
app = create_app()
