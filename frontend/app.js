// API Base URL
const API_BASE = 'http://localhost:8000/api';

// Navigation
document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', () => {
        const viewName = item.dataset.view;
        switchView(viewName);

        // Update active state
        document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
        item.classList.add('active');
    });
});

function switchView(viewName) {
    document.querySelectorAll('.view').forEach(view => view.classList.remove('active'));
    document.getElementById(`${viewName}-view`).classList.add('active');

    // Load data for the view
    if (viewName === 'dashboard') loadDashboard();
    if (viewName === 'duplicates') loadDuplicates();
    if (viewName === 'largest') loadLargestFiles();
    if (viewName === 'oldest') loadOldestFiles();
    if (viewName === 'tree') loadTreeView();
}

// Dashboard
async function loadDashboard() {
    try {
        const response = await fetch(`${API_BASE}/stats`);
        const data = await response.json();

        // Update stats
        document.getElementById('total-files').textContent = data.total_files.toLocaleString();
        document.getElementById('total-size').textContent = formatBytes(data.total_size);

        // Extension chart
        const extLabels = data.extensions.map(e => e.extension || 'No Extension');
        const extData = data.extensions.map(e => e.total_size);

        const extCtx = document.getElementById('extensionChart').getContext('2d');
        new Chart(extCtx, {
            type: 'doughnut',
            data: {
                labels: extLabels,
                datasets: [{
                    data: extData,
                    backgroundColor: [
                        '#6366f1', '#8b5cf6', '#ec4899', '#f59e0b',
                        '#10b981', '#06b6d4', '#f97316', '#84cc16',
                        '#6366f1', '#a855f7'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: { color: '#e4e7f1' }
                    }
                }
            }
        });

        // Largest files chart
        const fileLabels = data.largest_files.map(f => f.filename);
        const fileSizes = data.largest_files.map(f => f.size_bytes);

        const filesCtx = document.getElementById('largestFilesChart').getContext('2d');
        new Chart(filesCtx, {
            type: 'bar',
            data: {
                labels: fileLabels,
                datasets: [{
                    label: 'Size (bytes)',
                    data: fileSizes,
                    backgroundColor: '#6366f1'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                indexAxis: 'y',
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: {
                        ticks: { color: '#9ca3af' },
                        grid: { color: '#2d3548' }
                    },
                    y: {
                        ticks: { color: '#9ca3af' },
                        grid: { color: '#2d3548' }
                    }
                }
            }
        });

    } catch (error) {
        console.error('Error loading dashboard:', error);
    }
}

// Search
document.getElementById('search-btn').addEventListener('click', performSearch);
document.getElementById('search-query').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') performSearch();
});

async function performSearch() {
    const query = document.getElementById('search-query').value;
    const extension = document.getElementById('filter-extension').value;
    const minSize = document.getElementById('filter-min-size').value;
    const maxSize = document.getElementById('filter-max-size').value;

    const params = new URLSearchParams();
    if (query) params.append('query', query);
    if (extension) params.append('extension', extension);
    if (minSize) params.append('min_size', minSize);
    if (maxSize) params.append('max_size', maxSize);

    try {
        const response = await fetch(`${API_BASE}/search?${params}`);
        const results = await response.json();

        const container = document.getElementById('search-results');

        if (results.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">🔍</div>
                    <p>Nenhum arquivo encontrado com esses critérios</p>
                </div>
            `;
            return;
        }

        container.innerHTML = results.map(file => `
            <div class="result-item">
                <div class="result-path">${escapeHtml(file.path)}</div>
                <div class="result-meta">
                    ${formatBytes(file.size_bytes)} • 
                    ${file.extension || 'Sem extensão'} • 
                    Modificado: ${new Date(file.modified_at * 1000).toLocaleDateString('pt-BR')}
                </div>
            </div>
        `).join('');

    } catch (error) {
        console.error('Error searching:', error);
    }
}

// Duplicates
async function loadDuplicates() {
    try {
        const response = await fetch(`${API_BASE}/duplicates`);
        const duplicates = await response.json();

        const container = document.getElementById('duplicates-results');

        if (duplicates.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">✨</div>
                    <p>Nenhum arquivo duplicado encontrado!</p>
                </div>
            `;
            return;
        }

        container.innerHTML = duplicates.map((dup, index) => `
            <div class="duplicate-group" id="dup-group-${index}">
                <div class="duplicate-header">
                    <div>
                        <div class="duplicate-hash">MD5: ${dup.md5_hash}</div>
                        <div>${dup.count} cópias</div>
                    </div>
                    <div style="display: flex; align-items: center; gap: 1rem;">
                        <div class="wasted-space">
                            Desperdiçado: ${formatBytes(dup.wasted_space)}
                        </div>
                        <button class="btn-verify" onclick="verifySHA256('${dup.md5_hash}', ${index})" 
                                id="verify-btn-${index}">
                            🔐 Verificar SHA256
                        </button>
                    </div>
                </div>
                <ul class="duplicate-files">
                    ${dup.paths.map(path => `<li>${escapeHtml(path)}</li>`).join('')}
                </ul>
                <div id="verify-result-${index}" class="verify-result"></div>
            </div>
        `).join('');

    } catch (error) {
        console.error('Error loading duplicates:', error);
    }
}

async function verifySHA256(md5Hash, groupIndex) {
    const button = document.getElementById(`verify-btn-${groupIndex}`);
    const resultDiv = document.getElementById(`verify-result-${groupIndex}`);

    // Show loading state
    button.disabled = true;
    button.innerHTML = '⏳ Verificando...';
    resultDiv.innerHTML = '<div style="padding: 1rem; color: var(--text-secondary);">Computando SHA256...</div>';

    try {
        // Get candidate data from backend
        const candidatesResp = await fetch(`${API_BASE}/duplicates/candidates`);
        const candidates = await candidatesResp.json();

        // Find the specific MD5 group
        const group = candidates.find(c => c.md5_hash === md5Hash);
        if (!group) {
            throw new Error('Grupo não encontrado');
        }

        // Prepare request payload
        const payload = {
            md5_hash: md5Hash,
            file_ids: group.ids,
            file_paths: group.paths
        };

        // Call verification endpoint
        const response = await fetch(`${API_BASE}/duplicates/verify`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            throw new Error('Erro na verificação');
        }

        const result = await response.json();

        // Display results
        let html = `
            <div style="padding: 1rem; background: var(--bg-secondary); border-radius: 8px; margin-top: 1rem;">
                <div style="font-weight: 600; margin-bottom: 1rem; color: var(--accent);">
                    ✅ Verificação SHA256 Concluída
                </div>
        `;

        result.verified_groups.forEach((vgroup, idx) => {
            const isDupe = vgroup.is_duplicate;
            html += `
                <div style="padding: 0.75rem; background: var(--bg-primary); border-radius: 6px; margin-bottom: 0.5rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <div style="font-size: 0.875rem; color: var(--text-secondary); margin-bottom: 0.25rem;">
                                Grupo ${idx + 1} - SHA256: ${vgroup.sha256_hash.substring(0, 16)}...
                            </div>
                            <div style="font-weight: 600;">
                                ${vgroup.count} arquivo${vgroup.count > 1 ? 's' : ''}
                            </div>
                        </div>
                        <div style="padding: 0.5rem 1rem; border-radius: 4px; font-weight: 600;
                                    background: ${isDupe ? '#dc2626' : '#10b981'}; color: white;">
                            ${isDupe ? '⚠️ DUPLICADO' : '✓ ÚNICO'}
                        </div>
                    </div>
                    <ul style="margin-top: 0.5rem; padding-left: 1.5rem; font-size: 0.875rem;">
                        ${vgroup.files.map(f => `<li>${escapeHtml(f.path)}</li>`).join('')}
                    </ul>
                </div>
            `;
        });

        html += `
                <div style="margin-top: 1rem; font-size: 0.875rem; color: var(--text-secondary);">
                    Total: ${result.total_files} arquivos • 
                    Sucesso: ${result.successful} • 
                    Falhas: ${result.failed}
                </div>
            </div>
        `;

        resultDiv.innerHTML = html;
        button.innerHTML = '✅ Verificado';

    } catch (error) {
        console.error('Error verifying SHA256:', error);
        resultDiv.innerHTML = `
            <div style="padding: 1rem; background: #dc2626; color: white; border-radius: 8px; margin-top: 1rem;">
                ❌ Erro na verificação: ${error.message}
            </div>
        `;
        button.disabled = false;
        button.innerHTML = '🔐 Verificar SHA256';
    }
}

// Largest Files
document.getElementById('largest-refresh-btn').addEventListener('click', loadLargestFiles);
document.getElementById('largest-limit').addEventListener('change', loadLargestFiles);

async function loadLargestFiles() {
    const limit = document.getElementById('largest-limit').value;

    try {
        const response = await fetch(`${API_BASE}/largest?limit=${limit}`);
        const files = await response.json();

        const container = document.getElementById('largest-results');

        if (files.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">📊</div>
                    <p>Nenhum arquivo encontrado</p>
                </div>
            `;
            return;
        }

        let totalSize = files.reduce((sum, f) => sum + f.size_bytes, 0);

        container.innerHTML = `
            <div style="padding: 1rem; border-bottom: 1px solid var(--border); margin-bottom: 1rem;">
                <strong>${files.length} arquivos</strong> • Total: <strong>${formatBytes(totalSize)}</strong>
            </div>
            ${files.map((file, index) => `
                <div class="result-item">
                    <div style="display: flex; justify-content: space-between; align-items: start;">
                        <div style="flex: 1;">
                            <div style="color: var(--text-secondary); font-size: 0.875rem; margin-bottom: 0.25rem;">
                                #${index + 1}
                            </div>
                            <div class="result-path">${escapeHtml(file.path)}</div>
                            <div class="result-meta">
                                ${file.extension || 'Sem extensão'} • 
                                Modificado: ${new Date(file.modified_at * 1000).toLocaleDateString('pt-BR')}
                            </div>
                        </div>
                        <div style="text-align: right; margin-left: 1rem;">
                            <div style="font-size: 1.25rem; font-weight: 700; color: var(--accent);">
                                ${formatBytes(file.size_bytes)}
                            </div>
                        </div>
                    </div>
                </div>
            `).join('')}
        `;

    } catch (error) {
        console.error('Error loading largest files:', error);
    }
}

// Oldest Files
document.getElementById('oldest-refresh-btn').addEventListener('click', loadOldestFiles);
document.getElementById('oldest-limit').addEventListener('change', loadOldestFiles);

async function loadOldestFiles() {
    const limit = document.getElementById('oldest-limit').value;

    try {
        const response = await fetch(`${API_BASE}/oldest?limit=${limit}`);
        const files = await response.json();

        const container = document.getElementById('oldest-results');

        if (files.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">📊</div>
                    <p>Nenhum arquivo encontrado</p>
                </div>
            `;
            return;
        }

        let totalSize = files.reduce((sum, f) => sum + f.size_bytes, 0);

        // Calculate age in days
        const now = Date.now() / 1000; // Current time in seconds

        container.innerHTML = `
            <div style="padding: 1rem; border-bottom: 1px solid var(--border); margin-bottom: 1rem;">
                <strong>${files.length} arquivos</strong> • Total: <strong>${formatBytes(totalSize)}</strong>
            </div>
            ${files.map((file, index) => {
            const ageInDays = Math.floor((now - file.modified_at) / 86400);
            const modifiedDate = new Date(file.modified_at * 1000);

            return `
                    <div class="result-item">
                        <div style="display: flex; justify-content: space-between; align-items: start;">
                            <div style="flex: 1;">
                                <div style="color: var(--text-secondary); font-size: 0.875rem; margin-bottom: 0.25rem;">
                                    #${index + 1}
                                </div>
                                <div class="result-path">${escapeHtml(file.path)}</div>
                                <div class="result-meta">
                                    ${formatBytes(file.size_bytes)} • 
                                    ${file.extension || 'Sem extensão'}
                                </div>
                            </div>
                            <div style="text-align: right; margin-left: 1rem;">
                                <div style="font-size: 1.25rem; font-weight: 700; color: var(--accent);">
                                    ${ageInDays} dias
                                </div>
                                <div style="font-size: 0.75rem; color: var(--text-secondary); margin-top: 0.25rem;">
                                    ${modifiedDate.toLocaleDateString('pt-BR')}
                                </div>
                            </div>
                        </div>
                    </div>
                `;
        }).join('')}
        `;

    } catch (error) {
        console.error('Error loading oldest files:', error);
    }
}

// Utilities
function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Tree View
let treeCache = {}; // Cache loaded tree nodes

async function loadTreeView() {
    const container = document.getElementById('tree-root');
    container.innerHTML = '<div style="padding: 1rem; color: var(--text-secondary);">Carregando raízes...</div>';

    try {
        const response = await fetch(`${API_BASE}/tree?path=`);
        const data = await response.json();

        if (!data.children || data.children.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">📂</div>
                    <p>Nenhum diretório encontrado</p>
                </div>
            `;
            return;
        }

        // Cache root
        treeCache[''] = data;

        // Render root items
        container.innerHTML = '';
        data.children.forEach(item => {
            container.appendChild(createTreeItem(item, 0));
        });

    } catch (error) {
        console.error('Error loading tree:', error);
        container.innerHTML = `
            <div style="padding: 1rem; color: var(--danger);">
                ❌ Erro ao carregar árvore
            </div>
        `;
    }
}

function createTreeItem(item, level) {
    const div = document.createElement('div');
    div.className = 'tree-item';
    div.style.paddingLeft = `${level * 1.5}rem`;

    const isDir = item.type === 'dir';
    const icon = isDir ? '📁' : '📄';
    const hasChildren = item.has_children;

    div.innerHTML = `
        <div class="tree-item-content">
            ${hasChildren ? '<span class="tree-toggle">▶</span>' : '<span class="tree-spacer"></span>'}
            <span class="tree-icon">${icon}</span>
            <span class="tree-name">${escapeHtml(item.name)}</span>
            <span class="tree-size">${formatBytes(item.size)}</span>
        </div>
        <div class="tree-children" style="display: none;"></div>
    `;

    // Add click handler for directories
    if (hasChildren) {
        const toggle = div.querySelector('.tree-toggle');
        const content = div.querySelector('.tree-item-content');
        const childrenContainer = div.querySelector('.tree-children');

        content.style.cursor = 'pointer';

        content.addEventListener('click', async () => {
            const isExpanded = childrenContainer.style.display === 'block';

            if (isExpanded) {
                // Collapse
                childrenContainer.style.display = 'none';
                toggle.textContent = '▶';
            } else {
                // Expand - load children if not cached
                if (!treeCache[item.path]) {
                    toggle.textContent = '⏳';

                    try {
                        const response = await fetch(`${API_BASE}/tree?path=${encodeURIComponent(item.path)}`);
                        const data = await response.json();
                        treeCache[item.path] = data;

                        // Render children
                        childrenContainer.innerHTML = '';
                        if (data.children && data.children.length > 0) {
                            data.children.forEach(child => {
                                childrenContainer.appendChild(createTreeItem(child, level + 1));
                            });
                        } else {
                            childrenContainer.innerHTML = '<div style="padding: 0.5rem; padding-left: 1rem; color: var(--text-secondary); font-size: 0.875rem;">Pasta vazia</div>';
                        }

                    } catch (error) {
                        console.error('Error loading children:', error);
                        childrenContainer.innerHTML = '<div style="padding: 0.5rem; padding-left: 1rem; color: var(--danger); font-size: 0.875rem;">Erro ao carregar</div>';
                    }
                }

                childrenContainer.style.display = 'block';
                toggle.textContent = '▼';
            }
        });
    }

    return div;
}

// Export functionality
// --- Export Modal Logic ---

function openExportModal() {
    const modal = document.getElementById('export-modal');
    modal.classList.remove('hidden');
    // Force reflow for transition
    void modal.offsetWidth;
    modal.classList.add('active');
}

function closeExportModal() {
    const modal = document.getElementById('export-modal');
    modal.classList.remove('active');
    setTimeout(() => {
        modal.classList.add('hidden');
    }, 300); // Wait for transition
}

async function confirmExport() {
    const format = document.querySelector('input[name="export-format"]:checked').value;
    const btn = document.querySelector('#export-modal .btn-primary');
    const btnText = btn.querySelector('.btn-text');
    const spinner = btn.querySelector('.spinner');

    // UI Loading State
    btn.disabled = true;
    btnText.textContent = 'Gerando...';
    spinner.classList.remove('hidden');

    try {
        const response = await fetch(`${API_BASE}/export/${format}`);

        if (!response.ok) throw new Error('Falha na exportação');

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;

        // Get filename from header or default
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = `relatorio_arquivos_${new Date().toISOString().slice(0, 10)}.${format}`;
        if (contentDisposition) {
            const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
            if (filenameMatch.length === 2)
                filename = filenameMatch[1];
        }

        a.download = filename;
        document.body.appendChild(a);
        a.click();

        window.URL.revokeObjectURL(url);

        // Close modal after short delay
        setTimeout(() => {
            closeExportModal();
        }, 500);

    } catch (error) {
        console.error('Export error:', error);
        alert('Erro ao gerar relatório. Tente novamente.');
    } finally {
        // Reset UI
        btn.disabled = false;
        btnText.textContent = 'Exportar';
        spinner.classList.add('hidden');
    }
}

// Close modal on Escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeExportModal();
});

// Load dashboard on startup
loadDashboard();
/**
 * Load Suggestions
 */
async function loadSuggestions() {
    const container = document.getElementById('suggestions-table-body');
    container.innerHTML = '<tr><td colspan="5" class="loading">Carregando sugestões...</td></tr>';

    try {
        const response = await fetch(`${API_BASE}/suggestions`);
        const suggestions = await response.json();

        container.innerHTML = '';

        if (suggestions.length === 0) {
            container.innerHTML = '<tr><td colspan="5" class="no-data">Nenhuma sugestão encontrada! Seu sistema está limpo.</td></tr>';
            return;
        }

        suggestions.forEach(item => {
            const tr = document.createElement('tr');

            // Icon based on type/reason
            let icon = '📄';
            if (item.type === 'folder') icon = '📁';
            if (item.reason.includes('temporário')) icon = '🗑️';
            if (item.reason.includes('log')) icon = '📝';

            // Action button class
            let actionClass = 'btn-secondary';
            if (item.action === 'delete') actionClass = 'btn-danger';

            // Translate action
            const actionMap = {
                'delete': 'Excluir',
                'archive': 'Arquivar',
                'ignore': 'Ignorar'
            };

            tr.innerHTML = `
                <td class="col-path" title="${item.path}">
                    <span class="file-icon">${icon}</span>
                    ${item.path}
                </td>
                <td><span class="badge badge-${item.type}">${item.type === 'folder' ? 'Pasta' : 'Arquivo'}</span></td>
                <td>${item.reason}</td>
                <td class="text-right monospace">${formatBytes(item.size_bytes)}</td>
                <td class="text-center">
                    <button class="btn-sm ${actionClass}" onclick="mockAction('${item.action}', '${item.path.replace(/\\/g, '\\\\')}')">
                        ${actionMap[item.action] || item.action}
                    </button>
                </td>
            `;
            container.appendChild(tr);
        });

    } catch (error) {
        console.error('Error loading suggestions:', error);
        container.innerHTML = '<tr><td colspan="5" class="error">Erro ao carregar sugestões. Verifique o console.</td></tr>';
    }
}

function mockAction(action, path) {
    alert(`Ação simulada: ${action.toUpperCase()} em\n${path}\n\n(Funcionalidade de execução será implementada na próxima fase)`);
}

// Poll Scan Progress
let isScanning = false;
async function pollScanProgress() {
    try {
        const response = await fetch(`${API_BASE}/scan_progress`);
        const data = await response.json();

        const container = document.getElementById('scan-progress-container');
        const countEl = document.getElementById('scan-count');
        const barEl = document.getElementById('scan-bar');
        const fileEl = document.getElementById('scan-current-file');

        if (data.status === 'running') {
            isScanning = true;
            container.classList.remove('hidden');
            countEl.textContent = data.scanned.toLocaleString();
            fileEl.textContent = data.current_file;
            fileEl.title = data.current_file;

            // Indeterminate progress animation if total is unknown
            if (data.total) {
                const percent = (data.scanned / data.total) * 100;
                barEl.style.width = `${percent}%`;
            } else {
                // Animated stripe or just specific logic
                barEl.style.width = '100%';
                barEl.classList.add('indeterminate');
            }
        } else if (data.status === 'completed' && isScanning) {
            // Scan just finished
            isScanning = false;
            countEl.textContent = `Concluído: ${data.scanned}`;
            fileEl.textContent = "Scan finalizado!";
            barEl.style.width = '100%';

            // Hide after 5 seconds
            setTimeout(() => {
                container.classList.add('hidden');
            }, 5000);

            // Refresh dashboard
            loadDashboard();
        } else {
            // Idle or Error
            if (!isScanning) {
                container.classList.add('hidden');
            }
        }

    } catch (error) {
        // console.error('Error polling progress:', error); // Silence errors in console
    }
}

// Start polling
setInterval(pollScanProgress, 3000);

function cancelScan() {
    alert("Funcionalidade de cancelar scan será implementada com WebSocket na próxima fase.");
}


