/* /root/Web/static/js/main.js */

// 1. 内置图标库 (解决图标不显示的问题)
const ICONS = {
    add: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>`,
    restart: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M23 4v6h-6"></path><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path></svg>`,
    loading: `<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="animate-spin"><path d="M12 2v4"/><path d="M12 18v4"/><path d="M4.93 4.93l2.83 2.83"/><path d="M16.24 16.24l2.83 2.83"/><path d="M2 12h4"/><path d="M18 12h4"/><path d="M4.93 19.07l2.83-2.83"/><path d="M16.24 7.76l2.83-2.83"/></svg>`,
    code: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 18 22 12 16 6"></polyline><polyline points="8 6 2 12 8 18"></polyline></svg>`,
    excel: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><line x1="3" y1="9" x2="21" y2="9"></line><line x1="9" y1="21" x2="9" y2="9"></line></svg>`,
    graph: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="6" cy="6" r="3"></circle><circle cx="6" cy="18" r="3"></circle><circle cx="18" cy="12" r="3"></circle><line x1="6" y1="9" x2="6" y2="15"></line><line x1="8.5" y1="7.5" x2="15.5" y2="10.5"></line><line x1="8.5" y1="16.5" x2="15.5" y2="13.5"></line></svg>`,
    check: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>`,
    loadingSmall: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="animate-spin"><path d="M21 12a9 9 0 1 1-6.219-8.56"></path></svg>`,
    chevronUp: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="18 15 12 9 6 15"></polyline></svg>`
};

// 2. 颜色映射配置 (8种错误码)
const ERROR_PALETTE = [
    { bg: 'bg-orange-50',  text: 'text-orange-600', border: 'border-orange-500', hex: '#f97316' }, // Type 1
    { bg: 'bg-amber-50',   text: 'text-amber-600',  border: 'border-amber-500',  hex: '#d97706' }, // Type 2
    { bg: 'bg-yellow-50',  text: 'text-yellow-600', border: 'border-yellow-500', hex: '#ca8a04' }, // Type 3
    { bg: 'bg-red-50',     text: 'text-red-600',    border: 'border-red-500',    hex: '#dc2626' }, // Type 4
    { bg: 'bg-rose-50',    text: 'text-rose-600',   border: 'border-rose-500',   hex: '#e11d48' }, // Type 5
    { bg: 'bg-cyan-50',    text: 'text-cyan-600',   border: 'border-cyan-500',   hex: '#0891b2' }, // Type 6
    { bg: 'bg-blue-50',    text: 'text-blue-600',   border: 'border-blue-500',   hex: '#2563eb' }, // Type 7
    { bg: 'bg-violet-50',  text: 'text-violet-600', border: 'border-violet-500', hex: '#7c3aed' }  // Type 8
];

document.addEventListener('alpine:init', () => {
    Alpine.data('appData', () => ({
        state: 'initial',
        tab: 'code',
        icons: ICONS,
        excelData: [],
        checking: false,
        checkResult: null,
        showCards: false,
        focusedErrorIdx: null,
        neoViz: null,

        // --- 核心：颜色获取逻辑 ---
        getTheme(typeStr) {
            // 尝试从字符串中提取数字 (例如 "1" 或 "Type 1")
            let idx = 0;
            const match = typeStr.match(/\d+/);
            if (match) {
                idx = parseInt(match[0]) - 1; // 转换为 0-7 索引
            } else {
                // 如果没有数字，根据字符串长度取余，确保固定映射
                idx = typeStr.length % 8;
            }
            // 防止越界
            if (idx < 0 || idx >= 8) idx = 0;
            return ERROR_PALETTE[idx];
        },

        // --- 核心：Excel 行样式逻辑 ---
        getRowClass(lineNum) {
            if (!this.checkResult || !this.checkResult.errors) return '';
            
            // 聚焦模式
            if (this.focusedErrorIdx !== null) {
                const err = this.checkResult.errors[this.focusedErrorIdx];
                if (err && err.lines.includes(lineNum)) {
                    const theme = this.getTheme(err.type);
                    return `error-row-highlight ${theme.bg}`; // 只给背景，文字保持黑色更清晰
                }
                return 'opacity-30 grayscale'; 
            }
            
            // 全览模式
            const matchedError = this.checkResult.errors.find(err => err.lines.includes(lineNum));
            if (matchedError) {
                const theme = this.getTheme(matchedError.type);
                return `error-row-highlight ${theme.bg}`;
            }
            return '';
        },
        
        getRowStyle(lineNum) {
            // 为伪元素提供颜色变量
            let err = null;
            if (this.focusedErrorIdx !== null) {
                const focused = this.checkResult.errors[this.focusedErrorIdx];
                if (focused && focused.lines.includes(lineNum)) err = focused;
            } else {
                err = this.checkResult?.errors?.find(e => e.lines.includes(lineNum));
            }
            return err ? `color: ${this.getTheme(err.type).hex}` : '';
        },

        toggleFocus(idx) {
            this.focusedErrorIdx = (this.focusedErrorIdx === idx) ? null : idx;
            if (this.focusedErrorIdx !== null) this.tab = 'excel';
        },

        // --- 上传与解析 ---
        async handleUpload(e) {
            const file = e.target.files[0];
            if (!file) return;
            this.state = 'processing';
            const formData = new FormData();
            formData.append('file', file);
            try {
                const res = await fetch('/upload', { method: 'POST', body: formData });
                const data = await res.json();
                if (data.success) {
                    await this.loadFileData();
                    setTimeout(() => {
                        this.state = 'result';
                        this.$nextTick(() => { this.renderCode(); });
                    }, 1000);
                } else {
                    alert('Parse Error: ' + data.error);
                    this.state = 'initial';
                }
            } catch (err) {
                console.error(err);
                alert('Upload failed');
                this.state = 'initial';
            }
        },

        async loadFileData() {
            try {
                const res = await fetch('/get_file_content');
                const data = await res.json();
                const codeEl = document.getElementById('code-block');
                if(codeEl) codeEl.textContent = data.raw_content;
                this.excelData = data.excel_data;
            } catch (err) { console.error(err); }
        },

        renderCode() {
            const codeEl = document.getElementById('code-block');
            if (codeEl && window.Prism) Prism.highlightElement(codeEl);
        },

        renderGraph() {
            const container = document.getElementById("viz");
            if (!container) return;
            if (this.neoViz) { try { this.neoViz.render(); return; } catch(e) { this.neoViz = null; } }
            try {
                const neo4jUrl = "bolt://localhost:7687";
                const config = {
                    container_id: "viz",
                    server_url: neo4jUrl,
                    server_user: "neo4j",
                    server_password: "Password",
                    encrypted: "ENCRYPTION_OFF", 
                    labels: {
                        "PolicyNode": { "caption": "name", "size": "pagerank", "community": "partition" },
                        "RuleNode": { "caption": "expression" },
                        "ConditionNode": { "caption": "name" }
                    },
                    relationships: {
                        "HAS_RULE": { "thickness": 0.15, "caption": false },
                        "REQUIRES_ROLE": { "thickness": 0.2, "caption": false }
                    },
                    initial_cypher: "MATCH (n)-[r]->(m) RETURN n,r,m LIMIT 300"
                };
                const NeovisConstructor = (typeof Neovis !== 'undefined' && Neovis.default) ? Neovis.default : Neovis;
                if (!NeovisConstructor) throw new Error("Neovis library not loaded");
                this.neoViz = new NeovisConstructor(config);
                this.neoViz.render();
            } catch (e) {
                container.innerHTML = `<div class='text-red-500 p-4 text-center'>Connection Error: ${e.message}</div>`;
            }
        },

        switchTab(newTab) {
            this.tab = newTab;
            if (newTab === 'graph') setTimeout(() => this.renderGraph(), 200);
        },

        async runCheck() {
            this.checking = true;
            this.showCards = false;
            this.focusedErrorIdx = null;
            try {
                const res = await fetch('/run_check');
                const data = await res.json();
                this.checkResult = data;
                if (data.summary && data.summary.total > 0) this.showCards = true;
            } catch (err) {
                console.error(err);
                alert("Check failed");
            } finally {
                this.checking = false;
            }
        }
    }));
});