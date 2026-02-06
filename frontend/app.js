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

        container.innerHTML = duplicates.map(dup => `
            <div class="duplicate-group">
                <div class="duplicate-header">
                    <div>
                        <div class="duplicate-hash">MD5: ${dup.md5_hash}</div>
                        <div>${dup.count} cópias</div>
                    </div>
                    <div class="wasted-space">
                        Desperdiçado: ${formatBytes(dup.wasted_space)}
                    </div>
                </div>
                <ul class="duplicate-files">
                    ${dup.paths.map(path => `<li>${escapeHtml(path)}</li>`).join('')}
                </ul>
            </div>
        `).join('');

    } catch (error) {
        console.error('Error loading duplicates:', error);
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

// Load dashboard on startup
loadDashboard();
