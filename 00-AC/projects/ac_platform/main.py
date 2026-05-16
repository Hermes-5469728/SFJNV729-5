"""AC Platform v1.0 · 航母甲板 · 启动核心 + 挂载N模块"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import settings
from src.core.defense_label import MandatoryLabelMiddleware
from src.modules.medical.api import router as medical_router
from src.modules.content.api import router as content_router

app = FastAPI(
    title="AC Platform",
    version="1.0.0",
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url=None,
)

# ─── CORS ───
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── L5 强制标注 · 所有 JSON 输出注入幻觉警告 ───
app.add_middleware(MandatoryLabelMiddleware)

# ─── 挂载 N 模块 ───
app.include_router(medical_router, prefix="/api/v1/medical")
app.include_router(content_router, prefix="/api/v1/content")

# ─── 健康检查 ───
@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
