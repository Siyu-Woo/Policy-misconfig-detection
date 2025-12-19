/* /root/Web/static/js/main.js - AutoScroll & Custom Parse Version */

// 1. 图标定义 (保持不变)
const ICONS = {
    add: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>',
    restart: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M23 4v6h-6"></path><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path></svg>',
    loading: '<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2v4"/><path d="M12 18v4"/><path d="M4.93 4.93l2.83 2.83"/><path d="M16.24 16.24l2.83 2.83"/><path d="M2 12h4"/><path d="M18 12h4"/><path d="M4.93 19.07l2.83-2.83"/><path d="M16.24 7.76l2.83-2.83"/></svg>',
    code: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 18 22 12 16 6"></polyline><polyline points="8 6 2 12 8 18"></polyline></svg>',
    excel: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><line x1="3" y1="9" x2="21" y2="9"></line><line x1="9" y1="21" x2="9" y2="9"></line></svg>',
    graph: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="6" cy="6" r="3"></circle><circle cx="6" cy="18" r="3"></circle><circle cx="18" cy="12" r="3"></circle><line x1="6" y1="9" x2="6" y2="15"></line><line x1="8.5" y1="7.5" x2="15.5" y2="10.5"></line><line x1="8.5" y1="16.5" x2="15.5" y2="13.5"></line></svg>',
    check: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>',
    loadingSmall: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="animate-spin"><path d="M21 12a9 9 0 1 1-6.219-8.56"></path></svg>',
    chevronUp: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="18 15 12 9 6 15"></polyline></svg>'
};

// 2. 颜色映射配置
const ERROR_PALETTE = [
    { bg: 'bg-orange-50',  text: 'text-orange-600', border: 'border-orange-500', hex: '#f97316' },
    { bg: 'bg-amber-50',   text: 'text-amber-600',  border: 'border-amber-500',  hex: '#d97706' },
    { bg: 'bg-yellow-50',  text: 'text-yellow-600', border: 'border-yellow-500', hex: '#ca8a04' },
    { bg: 'bg-red-50',     text: 'text-red-600',    border: 'border-red-500',    hex: '#dc2626' },
    { bg: 'bg-rose-50',    text: 'text-rose-600',   border: 'border-rose-500',   hex: '#e11d48' },
    { bg: 'bg-cyan-50',    text: 'text-cyan-600',   border: 'border-cyan-500',   hex: '#0891b2' },
    { bg: 'bg-blue-50',    text: 'text-blue-600',   border: 'border-blue-500',   hex: '#2563eb' },
    { bg: 'bg-violet-50',  text: 'text-violet-600', border: 'border-violet-500', hex: '#7c3aed' }
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

        getTheme(typeStr) {
            let idx = 0;
            const match = typeStr.match(/\d+/);
            if (match) idx = parseInt(match[0]) - 1;
            else idx = typeStr.length % 8;
            if (idx < 0 || idx >= 8) idx = 0;
            return ERROR_PALETTE[idx];
        },
        getRowClass(lineNum) {
            if (!this.checkResult || !this.checkResult.errors) return '';
            if (this.focusedErrorIdx !== null) {
                const err = this.checkResult.errors[this.focusedErrorIdx];
                if (err && err.lines.includes(lineNum)) {
                    return 'error-row-highlight ' + this.getTheme(err.type).bg;
                }
                return 'opacity-30 grayscale'; 
            }
            const matchedError = this.checkResult.errors.find(err => err.lines.includes(lineNum));
            if (matchedError) return 'error-row-highlight ' + this.getTheme(matchedError.type).bg;
            return '';
        },
        getRowStyle(lineNum) {
            let err = null;
            if (this.focusedErrorIdx !== null) {
                const focused = this.checkResult.errors[this.focusedErrorIdx];
                if (focused && focused.lines.includes(lineNum)) err = focused;
            } else {
                err = this.checkResult?.errors?.find(e => e.lines.includes(lineNum));
            }
            return err ? 'color: ' + this.getTheme(err.type).hex : '';
        },
        
        // >>> 核心修改：点击错误卡片，自动切换表格并滚动定位 <<<
        toggleFocus(idx) {
            // 如果点击的是当前已展开的，则折叠（idx设为null），否则设为新idx
            this.focusedErrorIdx = (this.focusedErrorIdx === idx) ? null : idx;
            
            // 如果选中了某个错误
            if (this.focusedErrorIdx !== null) {
                // 1. 自动切到表格视图
                this.tab = 'excel'; 
                
                // 2. 自动滚动定位逻辑
                const err = this.checkResult.errors[this.focusedErrorIdx];
                if (err && err.lines && err.lines.length > 0) {
                    const targetLine = err.lines[0]; // 找到该错误的第一个行号
                    
                    // 等待 Tab 切换和 DOM 渲染完毕
                    this.$nextTick(() => {
                        // 在表格中寻找包含该行号的行
                        // 这里使用原生 JS 查找所有 tr，判断第一列内容
                        const rows = document.querySelectorAll('tbody tr');
                        for (let row of rows) {
                            const firstCell = row.querySelector('td');
                            if (firstCell && parseInt(firstCell.textContent.trim()) === targetLine) {
                                // 找到目标行，平滑滚动到视图中心 
                                row.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                break;
                            }
                        }
                    });
                }
            }
        },

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
                
                // 设置代码视图原始内容
                const codeEl = document.getElementById('code-block');
                if(codeEl) codeEl.textContent = data.raw_content;
                
                // >>> 核心修改：前端重写 Excel 解析逻辑 <<<
                // 需求：按 "" 拆分，忽略 # 注释
                if (data.raw_content) {
                    const lines = data.raw_content.split('\n');
                    const parsedData = [];
                    
                    lines.forEach((line, index) => {
                        const cleanLine = line.trim();
                        // 1. 忽略空行和以 # 开头的行
                        if (!cleanLine || cleanLine.startsWith('#')) return;
                        
                        // 2. 使用正则提取双引号内的内容
                        // 匹配 "content" 模式，非贪婪匹配
                        const matches = cleanLine.match(/"(.*?)"/g);
                        
                        if (matches && matches.length >= 2) {
                            // 去掉前后的引号
                            const name = matches[0].slice(1, -1);
                            const rule = matches[1].slice(1, -1);
                            
                            parsedData.push({
                                line: index + 1, // 行号 (从1开始)
                                name: name,
                                rule: rule
                            });
                        }
                    });
                    this.excelData = parsedData;
                } else {
                    // 如果没有 raw_content，降级使用后端传回的 data
                    this.excelData = data.excel_data;
                }

            } catch (err) { console.error(err); }
        },

        renderCode() {
            const codeEl = document.getElementById('code-block');
            if (codeEl && window.Prism) Prism.highlightElement(codeEl);
        },
        
        async renderGraph() {
            const container = document.getElementById('viz');
            if (!container) return;
            
            container.innerHTML = '<div class=\"flex items-center justify-center h-full text-gray-500\">Loading Graph...</div>';

            try {
                const res = await fetch('/get_graph_data');
                const data = await res.json();

                if (data.error) throw new Error(data.error);
                
                const nodes = new vis.DataSet(data.nodes);
                const edges = new vis.DataSet(data.edges);
                
                const options = {
                    nodes: {
                        shape: 'dot',
                        size: 20,
                        font: { size: 14 }
                    },
                    edges: {
                        arrows: 'to',
                        color: { color: '#ccc' }
                    },
                    physics: {
                        stabilization: false,
                        barnesHut: {
                            gravitationalConstant: -3000,
                            springLength: 95
                        }
                    }
                };

                container.innerHTML = '';
                window.networkInstance = new vis.Network(container, { nodes, edges }, options);
                
            } catch (e) {
                console.error('Graph Error:', e);
                container.innerHTML = `<div class='text-red-500 p-4 text-center'>Graph Load Error: ${e.message}</div>`;
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
                alert('Check failed');
            } finally {
                this.checking = false;
            }
        }
    }));
});