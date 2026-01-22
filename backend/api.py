"""FastAPI 接口服务模块 (API Service Module).

本模块定义了用于微信文章转 PDF 的 RESTful API 接口。
它充当系统的入口网关，负责接收 HTTP 请求，调用后端核心处理逻辑 (ArticleProcessor)，
并以流式响应的方式返回生成的 PDF 文件。

Routes:
    POST /api/convert: 将微信文章转换为 PDF。
    GET /api/health: 健康检查接口。
"""

import logging
import os
import sys
from io import BytesIO

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# 确保可以从本地模块导入
# (Ensure we can import from local modules)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入核心处理类
# (Import the core processing class)
from main import ArticleProcessor

# 配置日志 (Configure Logger)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 初始化 FastAPI 应用 (Initialize FastAPI App)
app = FastAPI(title="WeChat Article to PDF API")

# 允许 CORS 用于前端开发
# (Allow CORS for frontend development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConvertRequest(BaseModel):
    """转换请求的数据模型 (Data model for conversion requests).

    Attributes:
        url (str): 微信文章的 URL。
        no_filter (bool): 是否禁用智能图片过滤 (默认 False)。
    """
    url: str
    no_filter: bool = False

@app.post("/api/convert")
async def convert_to_pdf(req: ConvertRequest):
    """将微信文章 URL 转换为 PDF 文件。

    使用异步处理以实现高性能并发。

    Args:
        req (ConvertRequest): 请求体，包含 URL 和过滤选项。

    Returns:
        StreamingResponse: 生成的 PDF 文件流。

    Raises:
        HTTPException: 
            - 400: 如果无法获取内容、未找到图片或所有图片都被过滤。
            - 500: 如果发生意外的服务器内部错误。
    """
    logger.info(f"Received conversion request for: {req.url}")
    try:
        # 1. 获取内容 (Fetch content - Async)
        try:
            html = await ArticleProcessor.fetch_html(req.url)
        except Exception as e:
            logger.error(f"Failed to fetch HTML: {e}")
            raise HTTPException(status_code=400, detail=f"无法获取文章内容: {str(e)}")

        image_urls = ArticleProcessor.extract_image_urls(html)
        
        if not image_urls:
            raise HTTPException(status_code=400, detail="未找到图片链接")
        
        # 2. 下载并处理图片 (Download and process images - Async)
        # 在 API 模式下，我们不保存被丢弃的图片，以保持无状态和清洁
        # (We don't save discarded images in API mode to keep it stateless/clean)
        images = await ArticleProcessor.download_images(image_urls, no_filter=req.no_filter, save_discarded=False)
        
        if not images:
            raise HTTPException(status_code=400, detail="没有有效的图片可生成 PDF (可能全被过滤了)")
        
        # 3. 生成 PDF 到内存 (Generate PDF to memory)
        # 这部分是 CPU 密集型操作，使用 run_in_executor 避免阻塞事件循环
        # (This part is CPU bound, run in thread pool to avoid blocking event loop)
        loop = asyncio.get_running_loop()
        pdf_buffer = await loop.run_in_executor(None, ArticleProcessor.generate_pdf_bytes, images)
        
        # 4. 以流的形式返回 (Return as stream)
        filename = "article.pdf"
        logger.info("PDF generated successfully, returning stream.")
        return StreamingResponse(
            pdf_buffer, 
            media_type="application/pdf", 
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error processing request: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
def health_check():
    """健康检查接口 (Health check endpoint).

    Returns:
        dict: 服务状态信息。
    """
    return {"status": "ok"}
