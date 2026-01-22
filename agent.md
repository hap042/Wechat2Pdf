You are now a senior full‑stack architect. Before implementing any features, please generate architecture diagrams and perform a security audit. The code must comply with Google's coding standards and include detailed comments in Chinese.

所有用到的包都必须写入 requirements.txt 文件中。

# PDFCraft 架构设计与代码优化指南 (Architectural Design & Code Optimization Guide)

## 1. 系统架构设计 (System Architecture)

本系统采用经典的前后端分离架构 (SPA + REST API)，专注于微信公众号文章的高保真 PDF 转换与智能清洗。

### 1.1 架构图 (Mermaid)

```mermaid
graph TD
    User[用户 (Browser)] -->|HTTP Request| Frontend[前端 (React + Vite)]
    Frontend -->|REST API (POST /api/convert)| BackendGateway[后端网关 (FastAPI)]
    
    subgraph Backend [后端核心服务]
        BackendGateway --> Processor[文章处理器 (ArticleProcessor)]
        
        Processor --> Fetcher[异步下载器 (AsyncFetcher)]
        Fetcher -->|Async HTTP| WeChat[微信服务器]
        
        Processor --> Filter[智能过滤器 (SmartFilter)]
        Filter -->|Deep Learning| EAST[EAST 文字检测模型]
        Filter -->|CV Algorithms| OpenCV[OpenCV 二维码检测]
        
        Processor --> Generator[PDF 生成器 (PDFGenerator)]
        Generator -->|Image Processing| Pillow[Pillow / ReportLab]
    end
    
    BackendGateway -->|Stream Response| User
```

### 1.2 核心模块职责
1.  **AsyncFetcher**: 基于 `httpx` 实现高并发图片下载，替代传统的串行下载，大幅降低 I/O 等待时间。
2.  **SmartFilter**: 集成 EAST 深度学习模型与多重二维码检测策略，实现“试题保留、杂质去除”的业务黄金标准。
3.  **PDFGenerator**: 内存流式处理，避免大量磁盘 I/O，直接将处理后的图片流合成为 PDF 返回。

---

## 2. 安全审计 (Security Audit)

### 2.1 潜在风险与应对策略

| 风险点 | 描述 | 应对策略 | 状态 |
| :--- | :--- | :--- | :--- |
| **SSRF (服务端请求伪造)** | 用户传入恶意 URL 导致服务器攻击内网资源 | 1. 严格校验 URL 域名白名单 (仅允许 `mp.weixin.qq.com`, `mmbiz.qpic.cn`) <br> 2. 禁用系统环境变量代理 | ✅ 待强化 |
| **DOS (拒绝服务)** | 恶意构造超大图片或海量请求耗尽服务器内存/带宽 | 1. 限制最大并发下载数 <br> 2. 设置请求超时 (Timeout) <br> 3. 校验 Content-Length 和图片尺寸 | ✅ 已部分实现 |
| **RCE (远程代码执行)** | 通过恶意构造的图片文件触发图像处理库漏洞 | 1. 使用 Pillow `Image.open` 后立即 `load()` 并在沙箱/受限环境处理 <br> 2. 及时更新 Pillow/OpenCV 依赖 | ⚠️ 需持续关注 |
| **依赖安全** | 第三方库存在已知漏洞 | 锁定 `requirements.txt` 版本，定期运行 `pip audit` | ✅ 已锁定 |

### 2.2 Google 编码规范合规性检查
*   **Docstrings**: 必须使用 Google Style Docstrings (Three double-quotes, Args, Returns, Raises)。
*   **Type Hinting**: 所有函数参数和返回值必须包含类型注解。
*   **Naming**: 变量 `lower_case_with_underscores`, 类 `CapWords`, 常量 `CAPS_WITH_UNDERSCORES`。
*   **Imports**: 标准库 -> 第三方库 -> 本地库，分组排序。

---

## 3. 代码优化建议 (Code Optimization Tips)

### 3.1 性能优化
1.  **异步并发 (Async Concurrency)**: 
    *   *现状*: `requests` 串行下载，效率低下。
    *   *优化*: 引入 `httpx` 或 `aiohttp`，结合 `asyncio.gather` 并发下载图片。对于一篇包含 50 张图片的文章，耗时可从 30s 降至 5s。
2.  **内存管理**:
    *   图片处理尽量在内存中完成 (`BytesIO`)，减少磁盘读写。
    *   对于超大图片，使用缩略图进行预判，避免全量加载到 CV 模型。

### 3.2 可维护性优化
1.  **模块化 (Modularity)**: 将 `main.py` 拆分为 `fetcher.py`, `filter.py`, `pdf_maker.py`。虽然目前保持单文件便于管理，但内部应通过 Class 进行逻辑隔离。
2.  **配置分离**: 将超时时间、阈值、模型路径等硬编码提取为配置常量或环境变量。
3.  **日志规范**: 使用 `logging` 模块替代 `print`，区分 `INFO`, `DEBUG`, `WARNING` 级别。

---

## 4. 实施计划
我们将立即执行以下重构：
1.  引入 `httpx` 替换 `requests`。
2.  重构 `main.py` 为面向对象的 `ArticleProcessor` 类。
3.  添加完整的 Google Style 中文注释。
4.  增强异常处理与资源回收。
