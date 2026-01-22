import { useState } from 'react'
import { FileText, Download, Loader2, AlertCircle, CheckCircle2, Settings, Shield, Zap } from 'lucide-react'

function App() {
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  const [noFilter, setNoFilter] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!url) return

    setLoading(true)
    setError('')
    setSuccess(false)

    try {
      // Use BASE_URL to support subpath deployment (e.g., /wechat2pdf/)
      // In dev, BASE_URL is '/', so it becomes '/api/convert'
      // In prod, BASE_URL is '/wechat2pdf/', so it becomes '/wechat2pdf/api/convert'
      const baseUrl = import.meta.env.BASE_URL.endsWith('/') 
        ? import.meta.env.BASE_URL 
        : `${import.meta.env.BASE_URL}/`
      
      const response = await fetch(`${baseUrl}api/convert`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url, no_filter: noFilter }),
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || '转换失败')
      }

      // Handle file download
      const blob = await response.blob()
      const downloadUrl = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = downloadUrl
      a.download = 'article.pdf'
      document.body.appendChild(a)
      a.click()
      a.remove()
      setSuccess(true)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 text-slate-800 font-sans">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="bg-blue-600 p-1.5 rounded-lg">
              <FileText className="w-6 h-6 text-white" />
            </div>
            <span className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-700 to-blue-500">
              PDFCraft
            </span>
          </div>
          <nav className="hidden md:flex items-center gap-6 text-sm font-medium text-gray-600">
            <a href="/" className="hover:text-blue-600 transition-colors">首页</a>
            <a href="/" className="text-blue-600">工具</a>
            <a href="/" className="hover:text-blue-600 transition-colors">工作流</a>
            <a href="/" className="hover:text-blue-600 transition-colors">关于</a>
          </nav>
          <div className="flex items-center gap-3">
            <a href="/" className="p-2 hover:bg-gray-100 rounded-full text-gray-500">
              <Settings className="w-5 h-5" />
            </a>
            <a href="/" className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center text-blue-700 font-medium text-sm hover:ring-2 hover:ring-blue-200 transition-all">
              H
            </a>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-4 py-12 sm:px-6 lg:px-8">
        <div className="text-center mb-12">
          <h1 className="text-3xl sm:text-4xl font-extrabold text-gray-900 tracking-tight mb-4">
            微信公众号试卷转 PDF
          </h1>
          <p className="text-lg text-gray-500 max-w-2xl mx-auto">
            专注于将微信公众号文章中的试卷图片智能提取并转换为干净、可打印的 PDF 文档。
            <br />
            智能去噪，自动识别并移除文末广告、二维码和无关图片。
          </p>
        </div>

        <div className="bg-white rounded-2xl shadow-xl border border-gray-100 overflow-hidden">
          <div className="p-1 bg-gradient-to-r from-blue-500 via-indigo-500 to-purple-500 opacity-80"></div>
          
          <div className="p-8 sm:p-10">
            <form onSubmit={handleSubmit} className="space-y-6">
              <div>
                <label htmlFor="url" className="block text-sm font-medium text-gray-700 mb-2">
                  文章链接
                </label>
                <div className="relative">
                  <input
                    type="url"
                    id="url"
                    required
                    placeholder="粘贴微信公众号文章链接 (https://mp.weixin.qq.com/...)"
                    className="block w-full rounded-xl border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 py-4 px-4 text-base bg-gray-50 border hover:bg-white transition-colors"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                  />
                </div>
              </div>

              <div className="flex items-center justify-between bg-gray-50 p-4 rounded-xl border border-gray-100">
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-lg ${!noFilter ? 'bg-green-100 text-green-700' : 'bg-gray-200 text-gray-500'}`}>
                    <Shield className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="font-medium text-gray-900">智能过滤</h3>
                    <p className="text-xs text-gray-500">
                      自动识别并移除二维码、卡片等非正文内容 <span className="text-red-500 font-bold">可能导致缺页</span>
                    </p>
                  </div>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input 
                    type="checkbox" 
                    className="sr-only peer" 
                    checked={!noFilter}
                    onChange={(e) => setNoFilter(!e.target.checked)}
                  />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                </label>
              </div>

              <button
                type="submit"
                disabled={loading || !url}
                className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-bold py-4 px-8 rounded-xl transition-all transform hover:scale-[1.01] active:scale-[0.99] disabled:opacity-70 disabled:cursor-not-allowed shadow-lg shadow-blue-200"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    正在处理...
                  </>
                ) : (
                  <>
                    <Zap className="w-5 h-5" />
                    立即转换
                  </>
                )}
              </button>
            </form>

            {error && (
              <div className="mt-6 p-4 bg-red-50 border border-red-100 rounded-xl flex items-start gap-3 text-red-700 animate-in fade-in slide-in-from-top-2">
                <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
                <div>
                  <h4 className="font-medium">转换失败</h4>
                  <p className="text-sm mt-1">{error}</p>
                </div>
              </div>
            )}

            {success && (
              <div className="mt-6 p-4 bg-green-50 border border-green-100 rounded-xl flex items-start gap-3 text-green-700 animate-in fade-in slide-in-from-top-2">
                <CheckCircle2 className="w-5 h-5 shrink-0 mt-0.5" />
                <div>
                  <h4 className="font-medium">转换成功！</h4>
                  <p className="text-sm mt-1">PDF 文件已自动开始下载。</p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Features Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-16">
          {[
            { title: "智能识别", desc: "基于 EAST 模型的深度学习算法，精准识别试卷与无关图片。", icon: <Zap className="w-6 h-6 text-yellow-500" /> },
            { title: "纯净输出", desc: "自动拼接图片生成 A4 规格 PDF，无水印，适合打印。", icon: <FileText className="w-6 h-6 text-blue-500" /> },
            { title: "隐私安全", desc: "所有处理在服务器内存中完成，不保留任何用户数据。", icon: <Shield className="w-6 h-6 text-green-500" /> },
          ].map((item, i) => (
            <div key={i} className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm hover:shadow-md transition-shadow">
              <div className="bg-gray-50 w-12 h-12 rounded-lg flex items-center justify-center mb-4">
                {item.icon}
              </div>
              <h3 className="font-bold text-gray-900 mb-2">{item.title}</h3>
              <p className="text-sm text-gray-500 leading-relaxed">{item.desc}</p>
            </div>
          ))}
        </div>
      </main>
      
      <footer className="mt-20 py-8 border-t border-gray-200 bg-white text-center text-sm text-gray-500">
        <p>&copy; 2026 PDFCraft. All rights reserved.</p>
      </footer>
    </div>
  )
}

export default App
