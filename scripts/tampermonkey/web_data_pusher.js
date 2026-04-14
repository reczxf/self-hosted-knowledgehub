// ==UserScript==
// @name         Web Data Pusher (Fixed 422)
// @namespace    http://tampermonkey.net/
// @version      2.1
// @match        *://*/*
// @grant        GM_xmlhttpRequest
// @run-at       document-start
// ==/UserScript==

(function() {
    'use strict';

    window.addEventListener('keydown', function(e) {
        // 监听 Ctrl + Shift + S
        if (e.ctrlKey && e.shiftKey && e.code === 'KeyS') {
            e.preventDefault();
            console.log("🚀 正在构造数据并推送...");

            const payload = {
                "capture_method": "browser_extension",
                "url": window.location.href,
                "canonical_url": document.querySelector('link[rel="canonical"]')?.href || window.location.href,
                "title": document.title,
                "occurred_at": new Date().toISOString(), // 格式如: 2026-04-14T09:00:00Z
                "assets": [
                    {
                        "asset_role": "page_html",
                        "file_name": "page.html",
                        "mime_type": "text/html",
                        "text_content": document.documentElement.outerHTML
                    }
                ],
                "metadata": {
                    "tags": ["demo", "browser"]
                }
            };

            GM_xmlhttpRequest({
                method: "POST",
                url: "http://127.0.0.1:8000/ingest/webpage",
                data: JSON.stringify(payload),
                headers: { "Content-Type": "application/json" },
                onload: function(response) {
                    if (response.status === 200 || response.status === 201) {
                        console.log("✅ 推送成功:", response.responseText);
                        showNotice("推送成功！", "#4CAF50");
                    } else {
                        // 打印 422 的具体错误原因
                        console.error("❌ 服务端校验失败 (422):", response.responseText);
                        showNotice("格式错误 (422)，请看控制台", "#f44336");
                    }
                },
                onerror: function(err) {
                    console.error("❌ 网络错误:", err);
                    showNotice("无法连接服务器", "#555");
                }
            });
        }
    }, true);

    function showNotice(msg, color) {
        const div = document.createElement('div');
        div.textContent = msg;
        div.style.cssText = `position:fixed;top:10px;left:50%;transform:translateX(-50%);z-index:99999;padding:10px 20px;background:${color};color:white;border-radius:4px;font-weight:bold;`;
        document.body.appendChild(div);
        setTimeout(() => div.remove(), 3000);
    }
})();