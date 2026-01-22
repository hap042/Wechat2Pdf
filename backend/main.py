"""微信公众号文章转 PDF 核心处理模块 (Core Processing Module).

本模块负责处理微信公众号文章的抓取、图片下载、智能清洗以及 PDF 生成。
采用异步 I/O (asyncio/httpx) 提高并发下载性能，并结合 OpenCV 和 Deep Learning
(EAST 模型) 进行智能试卷识别与去噪。

Attributes:
    MIN_IMAGE_DIMENSION (int): 图片最小宽/高限制，小于此尺寸将被忽略。
    REQUEST_TIMEOUT (float): 网络请求超时时间（秒）。
    MAX_CONCURRENT_DOWNLOADS (int): 最大并发下载数量。
    USER_AGENT (str): 模拟浏览器的 User-Agent 字符串。
"""

import argparse
import asyncio
import logging
import os
import re
import sys
from io import BytesIO
from typing import List, Tuple, Optional

import cv2
import httpx
import numpy as np
from bs4 import BeautifulSoup
from PIL import Image

# -----------------------------------------------------------------------------
# Configuration & Constants (配置与常量)
# -----------------------------------------------------------------------------

# 配置日志输出到标准错误流 (Configure logging to stderr)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

# Constants (常量定义)
MIN_IMAGE_DIMENSION = 300  # Minimum width/height for images (图片最小尺寸)
REQUEST_TIMEOUT = 20.0     # Seconds (请求超时)
MAX_CONCURRENT_DOWNLOADS = 10  # Max concurrent downloads (最大并发数)
MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024  # 10MB limit per image (单张图片最大限制)
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
)

# 防止 PIL Decompression Bomb 攻击
# (Prevent PIL Decompression Bomb attacks)
Image.MAX_IMAGE_PIXELS = 100 * 1024 * 1024  # 100MP limit

# 强制清除系统代理设置，防止 requests/httpx 报错或连接失败
# (Force clear system proxy settings to avoid connection issues)
for key in ["HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"]:
    if key in os.environ:
        del os.environ[key]


# -----------------------------------------------------------------------------
# Core Classes (核心类定义)
# -----------------------------------------------------------------------------

class SmartFilter:
    """提供基于深度学习 (EAST) 和 CV 算法的智能图片过滤功能。
    
    该类封装了检测文本区域（试卷识别）和过滤无关元素（如二维码、装饰性图片）的逻辑。
    (Provides intelligent image filtering using Deep Learning (EAST) and CV algorithms.)

    Attributes:
        _net (cv2.dnn_Net): 加载的 OpenCV DNN 网络实例 (EAST 模型)。
    """
    
    _net = None

    @classmethod
    def load_model(cls) -> None:
        """从磁盘加载 EAST 文本检测模型。
        
        该方法是幂等的；它会检查模型是否已经加载。
        (Loads the EAST text detection model from disk. Idempotent.)
        """
        if cls._net is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            model_path = os.path.join(base_dir, "models", "frozen_east_text_detection.pb")
            
            if not os.path.exists(model_path):
                logger.warning(f"OCR model not found at {model_path}. Smart filtering will be skipped.")
                return
                
            try:
                cls._net = cv2.dnn.readNet(model_path)
                logger.debug(f"Loaded EAST model from {model_path}")
            except Exception as e:
                logger.error(f"Failed to load EAST model: {e}")

    @staticmethod
    def is_valid_exam_paper(pil_image: Image.Image) -> Tuple[bool, str]:
        """根据文本密度和内容判断图片是否为有效的试卷。

        Args:
            pil_image (Image.Image): 待评估的 PIL Image 对象。

        Returns:
            Tuple[bool, str]: 
                - bool: 是否保留该图片 (True 为保留，False 为丢弃)。
                - str: 判定理由的描述字符串。
        """
        w, h = pil_image.size
        
        # 1. 基础尺寸检查 (Basic dimension check)
        if w < MIN_IMAGE_DIMENSION or h < MIN_IMAGE_DIMENSION:
            return False, f"尺寸太小 ({w}x{h})"

        # 转换为 OpenCV 格式 (BGR)
        cv_img = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

        # --- 二维码检测策略 (QR Code Detection Strategy) ---
        try:
            gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
            detector = cv2.QRCodeDetector()
            
            # 多重解码策略以增强鲁棒性 (Multi-pass decoding strategy)
            # Pass 1: 原始灰度图
            decoded_text, points, _ = detector.detectAndDecode(gray)
            
            # Pass 2: 反色处理 (部分二维码是黑底白码)
            if not decoded_text:
                decoded_text, points, _ = detector.detectAndDecode(255 - gray)
                
            # Pass 3: 二值化处理
            if not decoded_text:
                 _, binary = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY)
                 decoded_text, points, _ = detector.detectAndDecode(binary)

            # 严格检查: 必须解码出文本才确认为二维码
            has_prominent_qr = False
            qr_reason = ""
            
            if points is not None and len(decoded_text) > 0:
                pts = points
                if len(pts.shape) == 3:
                    pts = pts[0]
                area = cv2.contourArea(pts)
                ratio = area / (w * h)
                
                # 如果二维码巨大 (>40%)，直接判定为无效
                if ratio > 0.40:
                    return False, f"检测到巨大二维码 (占比 {ratio:.1%})"
                
                # 如果面积占比 > 5%，标记为显著二维码，但暂不直接丢弃，需结合文本检测判断
                # (针对听力试卷包含二维码的情况)
                if ratio > 0.05:
                     has_prominent_qr = True
                     qr_reason = f"检测到可扫描二维码 (占比 {ratio:.1%})"
            
            # 降级策略: 仅检测图案但不解码 (针对复杂或模糊的二维码)
            elif len(decoded_text) == 0:
                 ok, points = detector.detect(gray)
                 if ok and points is not None:
                      pts = points
                      if len(pts.shape) == 3:
                           pts = pts[0]
                      area = cv2.contourArea(pts)
                      ratio = area / (w * h)
                      
                      if ratio > 0.20:
                           # 即使检测到疑似二维码，也不直接丢弃，而是标记为"显著二维码"
                           # 交给后续的文本检测逻辑来综合判断。如果文本足够多，仍然认为是有效试卷。
                           has_prominent_qr = True
                           qr_reason = f"检测到疑似二维码 (未解码, 占比 {ratio:.1%})"

        except Exception as e:
            logger.warning(f"QR detection error: {e}")
            has_prominent_qr = False
            qr_reason = ""
        # ----------------------------------
            
        # 加载 EAST 模型 (Load EAST model)
        SmartFilter.load_model()
        if SmartFilter._net is None:
            return True, "模型未加载，默认保留"

        # 2. 使用 EAST 进行文本检测 (Text Detection with EAST)
        inp_w, inp_h = 320, 320 # 必须是 32 的倍数
        blob = cv2.dnn.blobFromImage(cv_img, 1.0, (inp_w, inp_h), 
                                   (123.68, 116.78, 103.94), True, False)
        
        SmartFilter._net.setInput(blob)
        # 获取特征图和几何信息
        scores, geometry = SmartFilter._net.forward(["feature_fusion/Conv_7/Sigmoid", "feature_fusion/concat_3"])
        
        # 3. 解码结果 (Decode results)
        conf_threshold = 0.5
        nms_threshold = 0.4
        
        boxes, confidences = SmartFilter.decode(scores, geometry, conf_threshold)
        # 非极大值抑制 (NMS) 去除重叠框
        indices = cv2.dnn.NMSBoxes(boxes, confidences, conf_threshold, nms_threshold)
        num_text_boxes = len(indices)
        
        # 4. 决策逻辑 (Decision Logic)
        aspect_ratio = max(w, h) / min(w, h) if min(w, h) > 0 else 1.0

        # 规则 1: 高文本密度 -> 确认为试卷
        if num_text_boxes >= 8:
             return True, f"检测到大量文本区域 ({num_text_boxes}处)"
             
        # 如果文本较少且包含显著二维码，则认为是广告或干扰图
        if has_prominent_qr:
            return False, f"{qr_reason}, 且文本较少 ({num_text_boxes}处)"

             
        # 规则 2: 中等文本密度，检查长宽比
        # 试卷通常接近 A4 (比例 ~1.41)，二维码/卡片通常是正方形 (~1.0)
        if 4 <= num_text_boxes < 8:
            if aspect_ratio < 1.3:
                 return False, f"疑似二维码/卡片 (文本{num_text_boxes}处, 比例{aspect_ratio:.2f})"
            return True, f"包含适量文本 ({num_text_boxes}处)"
            
        # 规则 3: 低文本密度 (<4)
        # 检查边缘复杂度 (地图、几何题图片)
        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.count_nonzero(edges) / (w * h)
        
        if num_text_boxes > 0:
            if edge_density > 0.01:
                return True, f"少量文本但包含线条细节 (文本{num_text_boxes}, 密度{edge_density:.3f})"
        else:
            if edge_density > 0.05:
                return True, f"无文本但线条丰富 (密度{edge_density:.3f})"
                
        if aspect_ratio > 4: # 极长条图片通常是分割线或装饰
            return False, "无文本且长宽比异常"
            
        return False, f"文本极少且线条简单 (文本{num_text_boxes}, 密度{edge_density:.3f})"

    @staticmethod
    def decode(scores: np.ndarray, geometry: np.ndarray, scoreThresh: float) -> Tuple[List[List[int]], List[float]]:
        """将 EAST 模型的原始输出解码为边界框。

        Args:
            scores (np.ndarray): 置信度分数图。
            geometry (np.ndarray): 几何信息图 (RBOX)。
            scoreThresh (float): 置信度阈值。

        Returns:
            Tuple[List[List[int]], List[float]]: 
                - List[List[int]]: 边界框列表 [x, y, w, h]。
                - List[float]: 对应的置信度列表。
        """
        detections = []
        confidences = []
        
        height = scores.shape[2]
        width = scores.shape[3]
        
        for y in range(height):
            scoresData = scores[0, 0, y]
            x0_data = geometry[0, 0, y]
            x1_data = geometry[0, 1, y]
            x2_data = geometry[0, 2, y]
            x3_data = geometry[0, 3, y]
            anglesData = geometry[0, 4, y]
            
            for x in range(width):
                score = scoresData[x]
                if score < scoreThresh:
                    continue
                    
                offsetX = x * 4.0
                offsetY = y * 4.0
                angle = anglesData[x]
                cosA = np.cos(angle)
                sinA = np.sin(angle)
                
                h = x0_data[x] + x2_data[x]
                w = x1_data[x] + x3_data[x]
                
                offset = ([offsetX + cosA * x1_data[x] + sinA * x2_data[x], offsetY - sinA * x1_data[x] + cosA * x2_data[x]])
                
                p1 = (-sinA * h + offset[0], -cosA * h + offset[1])
                p3 = (-cosA * w + offset[0], sinA * w + offset[1])
                
                center = (0.5 * (p1[0] + p3[0]), 0.5 * (p1[1] + p3[1]))
                
                detections.append([int(center[0] - w/2), int(center[1] - h/2), int(w), int(h)])
                confidences.append(float(score))
                
        return detections, confidences


class ArticleProcessor:
    """处理微信文章的端到端流程 (Handles the end-to-end processing)."""

    @staticmethod
    def normalize_image_url(url: str) -> str:
        """标准化微信图片 URL 以确保获取高质量版本。

        Args:
            url (str): 原始图片 URL。

        Returns:
            str: 标准化后的 URL。
        """
        match = re.search(r"(https://mmbiz\.qpic\.cn/[^?]+)", url)
        if match:
            base = match.group(1)
            parts = base.rsplit("/", 1)
            if len(parts) == 2:
                prefix, last = parts
                if last.isdigit():
                    return f"{prefix}/0" # /0 通常代表原图/高清图
        return url

    @staticmethod
    async def fetch_html(url: str) -> str:
        """异步获取文章 HTML 内容。

        Args:
            url (str): 文章 URL。

        Returns:
            str: HTML 文本内容。

        Raises:
            httpx.HTTPStatusError: 如果请求返回非 200 状态码。
        """
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, follow_redirects=True) as client:
            headers = {
                "User-Agent": USER_AGENT,
                "Accept-Language": "zh-CN,zh;q=0.9",
            }
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            return resp.text

    @staticmethod
    def extract_image_urls(html: str) -> List[str]:
        """解析 HTML 并提取所有相关的图片 URL。

        Args:
            html (str): HTML 内容。

        Returns:
            List[str]: 图片 URL 列表。
        """
        soup = BeautifulSoup(html, "html.parser")
        container = soup.find(id="js_content") or soup
        
        urls = []
        seen = set()
        
        for img in container.find_all("img"):
            # 微信文章通常将真实 URL 放在 data-src 中
            src = img.get("data-src") or img.get("data-original") or img.get("src")
            if not src:
                continue
            src = src.strip()
            if not src:
                continue
                
            src = ArticleProcessor.normalize_image_url(src)
            if src in seen:
                continue
            seen.add(src)
            urls.append(src)
            
        return urls

    @staticmethod
    async def download_single_image(client: httpx.AsyncClient, url: str, semaphore: asyncio.Semaphore) -> Optional[Tuple[Image.Image, int, str]]:
        """下载单张图片并进行错误处理 (Download single image with safety checks).

        Args:
            client (httpx.AsyncClient): HTTP 客户端实例。
            url (str): 图片 URL。
            semaphore (asyncio.Semaphore): 并发控制信号量。

        Returns:
            Optional[Tuple[Image.Image, int, str]]: 
                成功时返回 (PIL Image对象, 图片大小字节数, URL)；
                失败或被过滤时返回 None。
        """
        async with semaphore:
            try:
                headers = {
                    'User-Agent': USER_AGENT,
                    'Referer': 'https://mp.weixin.qq.com/',
                    'Accept': 'image/webp,image/jpeg,image/png,image/*,*/*;q=0.8'
                }
                
                # 使用 stream 模式以检查 Content-Length 并防止大文件攻击
                async with client.stream('GET', url, headers=headers) as resp:
                    resp.raise_for_status()
                    
                    content_type = resp.headers.get('Content-Type', '').lower()
                    if 'text/html' in content_type or 'image/svg' in content_type:
                        return None
                        
                    # 1. Check Content-Length header if available
                    content_length = resp.headers.get('Content-Length')
                    if content_length and int(content_length) > MAX_IMAGE_SIZE_BYTES:
                        logger.warning(f"Skipping {url}: Size {content_length} exceeds limit.")
                        return None

                    # 2. Stream download with size limit
                    img_data = bytearray()
                    async for chunk in resp.aiter_bytes():
                        img_data.extend(chunk)
                        if len(img_data) > MAX_IMAGE_SIZE_BYTES:
                             logger.warning(f"Skipping {url}: Downloaded size exceeds {MAX_IMAGE_SIZE_BYTES} bytes.")
                             return None
                    
                img_size = len(img_data)
                
                # 使用 BytesIO 避免磁盘 I/O
                # Use BytesIO to avoid disk I/O
                try:
                    img = Image.open(BytesIO(img_data))
                    img.load() # 强制加载数据 (Force load data)
                except Image.DecompressionBombError:
                    logger.warning(f"Skipping {url}: Decompression Bomb detected!")
                    return None
                except Exception as e:
                    logger.warning(f"Invalid image data from {url}: {e}")
                    return None
                
                # 统一转换为 RGB 模式
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                    
                w, h = img.size
                if w < MIN_IMAGE_DIMENSION or h < MIN_IMAGE_DIMENSION:
                    return None
                    
                return (img, img_size, url)
                
            except Exception as e:
                logger.warning(f"Failed to download {url}: {e}")
                return None

    @staticmethod
    async def download_images(urls: List[str], no_filter: bool = False, save_discarded: bool = False) -> List[Image.Image]:
        """并发下载多张图片并进行过滤。

        Args:
            urls (List[str]): 图片 URL 列表。
            no_filter (bool): 是否禁用智能过滤。
            save_discarded (bool): 是否保存被丢弃的图片（用于调试）。

        Returns:
            List[Image.Image]: 最终保留的图片列表。
        """
        logger.info(f"Starting download for {len(urls)} images...")
        
        candidates = []
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)
        
        # 使用 http2=True 提高并发性能
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, http2=True) as client:
            tasks = []
            for url in urls:
                tasks.append(ArticleProcessor.download_single_image(client, url, semaphore))
            
            # 并发执行所有下载任务
            results = await asyncio.gather(*tasks)
            
            for res in results:
                if res:
                    candidates.append(res)
                    
        if not candidates:
            return []

        # --- 过滤阶段 (Filtering Stage) ---
        if no_filter:
            logger.info("Smart filtering disabled.")
            return [c[0] for c in candidates]

        logger.info("Applying smart filtering...")
        final_images = []
        discarded_images = []

        for img, size, url in candidates:
            is_valid, reason = SmartFilter.is_valid_exam_paper(img)
            
            if not is_valid:
                logger.info(f"[Discarded] {reason} | {size//1024}KB")
                if save_discarded:
                    discarded_images.append(img)
                continue
                
            logger.info(f"[Kept] {reason} | {size//1024}KB")
            final_images.append(img)

        if save_discarded and discarded_images:
            discard_dir = os.path.join("output", "discarded")
            os.makedirs(discard_dir, exist_ok=True)
            for i, img in enumerate(discarded_images):
                img.save(os.path.join(discard_dir, f"discarded_{i}.jpg"))

        return final_images

    @staticmethod
    def save_images_as_pdf(images: List[Image.Image], output_path: str) -> None:
        """将图片列表保存为单个 PDF 文件。

        Args:
            images (List[Image.Image]): 图片列表。
            output_path (str): 输出 PDF 文件的路径。

        Raises:
            ValueError: 如果图片列表为空。
        """
        if not images:
            raise ValueError("No images to save.")
            
        first, *rest = images
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        first.save(output_path, format="PDF", save_all=True, append_images=rest, resolution=100.0)

    @staticmethod
    def generate_pdf_bytes(images: List[Image.Image]) -> BytesIO:
        """将图片列表转换为 PDF 字节流 (在内存中)。

        Args:
            images (List[Image.Image]): 图片列表。

        Returns:
            BytesIO: 包含 PDF 数据的内存缓冲区。

        Raises:
            ValueError: 如果图片列表为空。
        """
        if not images:
            raise ValueError("No images to convert")

        pdf_buffer = BytesIO()
        first, *rest = images
        first.save(pdf_buffer, format="PDF", save_all=True, append_images=rest, resolution=100.0)
        pdf_buffer.seek(0)
        return pdf_buffer


# -----------------------------------------------------------------------------
# CLI Entry Point (命令行入口)
# -----------------------------------------------------------------------------

async def async_main() -> None:
    """异步主函数，处理 CLI 参数并执行转换流程。"""
    parser = argparse.ArgumentParser(description="Convert WeChat Article to PDF (Async Optimized)")
    parser.add_argument("url", help="WeChat Article URL")
    parser.add_argument("-o", "--output", default=os.path.join("output", "output.pdf"), help="Output PDF path")
    parser.add_argument("--no-filter", action="store_true", help="Disable smart filtering")
    parser.add_argument("--save-discarded", action="store_true", help="Save discarded images for debugging")
    
    args = parser.parse_args()

    try:
        html = await ArticleProcessor.fetch_html(args.url)
        image_urls = ArticleProcessor.extract_image_urls(html)
        
        if not image_urls:
            logger.error("No image URLs found in the article.")
            sys.exit(1)
            
        images = await ArticleProcessor.download_images(image_urls, no_filter=args.no_filter, save_discarded=args.save_discarded)
        
        if not images:
            logger.error("No valid images remained after filtering.")
            sys.exit(1)
            
        ArticleProcessor.save_images_as_pdf(images, args.output)
        logger.info(f"PDF generated successfully: {os.path.abspath(args.output)}")
        
    except Exception as e:
        logger.exception(f"Processing failed: {e}")
        sys.exit(1)

def main():
    """入口点封装器 (Entry point wrapper).
    
    负责初始化模型并启动 asyncio 事件循环。
    """
    SmartFilter.load_model()
    asyncio.run(async_main())

if __name__ == "__main__":
    main()

# -----------------------------------------------------------------------------
# Legacy/Sync Wrapper for API Compatibility (旧版/同步 API 兼容包装器)
# -----------------------------------------------------------------------------
# 这些包装器确保 api.py 中现有的同步调用（如果尚未更新）仍然可以工作。
# (These wrappers ensure backward compatibility.)

def fetch_html(url: str) -> str:
    """fetch_html 的同步包装器 (Legacy Support)。"""
    return asyncio.run(ArticleProcessor.fetch_html(url))

def extract_image_urls(html: str) -> List[str]:
    """extract_image_urls 的包装器。"""
    return ArticleProcessor.extract_image_urls(html)

def download_images(urls: List[str], no_filter: bool = False, save_discarded: bool = False) -> List[Image.Image]:
    """download_images 的同步包装器 (Legacy Support)。"""
    return asyncio.run(ArticleProcessor.download_images(urls, no_filter, save_discarded))
