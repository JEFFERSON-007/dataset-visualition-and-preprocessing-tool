document.addEventListener('DOMContentLoaded', () => {
    const fileInput = document.getElementById('file-input');
    const uploadBtn = document.getElementById('upload-btn');
    const reportBtn = document.getElementById('report-btn');  // Add report button
    const dropZone = document.getElementById('drop-zone');
    const statusMsg = document.getElementById('status-message');
    const fileNameDisplay = document.getElementById('file-name-display');
    const resultsArea = document.getElementById('results-area');

    // Configuration
    const MAX_FILE_SIZE = 5 * 1024 * 1024 * 1024; // 5GB
    const LARGE_FILE_WARNING = 1024 * 1024 * 1024; // 1GB
    const SUPPORTED_EXTENSIONS = ['.csv', '.tsv', '.txt', '.xlsx', '.xls', '.json', '.parquet'];

    // Store file for preprocessing re-upload (simulated state)
    let currentFile = null;

    // Drag & Drop
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        if (e.dataTransfer.files.length) {
            handleFileSelect(e.dataTransfer.files[0]);
        }
    });

    // Click to select
    dropZone.addEventListener('click', () => fileInput.click());

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length) {
            handleFileSelect(fileInput.files[0]);
        }
    });

    function handleFileSelect(file) {
        // Validate file extension
        const fileName = file.name.toLowerCase();
        const ext = '.' + fileName.split('.').pop();

        if (!SUPPORTED_EXTENSIONS.includes(ext)) {
            statusMsg.style.color = 'var(--error)';
            statusMsg.textContent = `Unsupported file type: ${ext}. Please upload: ${SUPPORTED_EXTENSIONS.join(', ')}`;
            uploadBtn.disabled = true;
            fileNameDisplay.textContent = 'No file selected';
            return;
        }

        // Validate file size
        if (file.size > MAX_FILE_SIZE) {
            const sizeMB = (file.size / (1024 * 1024)).toFixed(1);
            const maxMB = (MAX_FILE_SIZE / (1024 * 1024)).toFixed(0);
            statusMsg.style.color = 'var(--error)';
            statusMsg.textContent = `File too large (${sizeMB}MB). Maximum size: ${maxMB}MB`;
            uploadBtn.disabled = true;
            fileNameDisplay.textContent = 'No file selected';
            return;
        }

        if (file.size === 0) {
            statusMsg.style.color = 'var(--error)';
            statusMsg.textContent = 'File is empty. Please select a file with data.';
            uploadBtn.disabled = true;
            fileNameDisplay.textContent = 'No file selected';
            return;
        }

        // Show warning for large files
        if (file.size > LARGE_FILE_WARNING) {
            const sizeMB = (file.size / (1024 * 1024)).toFixed(1);
            statusMsg.style.color = 'var(--warning)';
            statusMsg.textContent = `Large file detected (${sizeMB}MB). Processing may take longer and will use memory-efficient mode.`;
        } else {
            statusMsg.style.color = 'var(--text-secondary)';
            statusMsg.textContent = 'File ready to upload';
        }

        // Update UI
        fileNameDisplay.textContent = file.name;
        uploadBtn.disabled = false;
        reportBtn.disabled = false;  // Enable report button
        currentFile = file;

        // Use DataTransfer to sync with input if dropped
        const dt = new DataTransfer();
        dt.items.add(file);
        fileInput.files = dt.files;
    }

    // Upload Action
    uploadBtn.addEventListener('click', async () => {
        if (!fileInput.files.length) return;

        const file = fileInput.files[0];
        const formData = new FormData();
        formData.append('file', file);
        formData.append('sample_rows', document.getElementById('sample-rows').value);

        // UI Loading State
        uploadBtn.disabled = true;
        uploadBtn.textContent = 'Processing...';
        statusMsg.style.color = 'var(--text-secondary)';
        statusMsg.textContent = 'Uploading and analyzing your data...';
        resultsArea.classList.add('hidden');

        try {
            const startTime = performance.now();
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (!response.ok) {
                // Display structured error with suggestion
                const errorMsg = data.error || 'Upload failed';
                const suggestion = data.suggestion ? `\n💡 ${data.suggestion}` : '';
                throw new Error(errorMsg + suggestion);
            }

            const elapsed = ((performance.now() - startTime) / 1000).toFixed(1);

            statusMsg.style.color = 'var(--success)';
            statusMsg.textContent = `Analysis complete in ${elapsed}s!`;

            // Show sampling notification if data was sampled
            if (data.is_sampled) {
                const backendInfo = data.backend ? ` | Backend: ${data.backend.toUpperCase()}` : '';
                const samplingMsg = document.createElement('div');
                samplingMsg.style.cssText = 'margin-top:10px; padding:10px; background:rgba(245,158,11,0.1); border-left:3px solid var(--warning); border-radius:6px; font-size:0.9rem;';
                samplingMsg.innerHTML = `
                    <strong>📊 Large Dataset Detected (${data.file_size_mb}MB${backendInfo})</strong><br>
                    Showing ${data.sampled_rows.toLocaleString()} sampled rows from ${data.total_rows.toLocaleString()} total rows for visualization.
                    Statistics are based on the full dataset.
                `;
                statusMsg.parentElement.appendChild(samplingMsg);
            }

            renderDashboard(data);

        } catch (error) {
            statusMsg.style.color = 'var(--error)';
            // Handle multi-line error messages
            const lines = error.message.split('\n');
            if (lines.length > 1) {
                statusMsg.innerHTML = lines.map((line, i) =>
                    i === 0 ? `❌ ${line}` : `<div style="margin-top:8px; font-size:0.9em;">${line}</div>`
                ).join('');
            } else {
                statusMsg.textContent = `❌ ${error.message}`;
            }
        } finally {
            uploadBtn.disabled = false;
            uploadBtn.textContent = 'Analyze Dataset';
        }
    });

    // Clean & Download Action
    const cleanBtn = document.getElementById('clean-btn');
    if (cleanBtn) {
        cleanBtn.addEventListener('click', async () => {
            if (!currentFile) return;

            cleanBtn.disabled = true;
            cleanBtn.textContent = 'Cleaning...';
            const downloadArea = document.getElementById('download-area');
            downloadArea.innerHTML = ''; // clear previous

            const formData = new FormData();
            formData.append('file', currentFile);
            formData.append('remove_duplicates', document.getElementById('opt-duplicates').checked);
            formData.append('impute_missing', document.getElementById('opt-missing').checked);
            formData.append('drop_constant', document.getElementById('opt-constant').checked);

            try {
                const response = await fetch('/preprocess', {
                    method: 'POST',
                    body: formData
                });

                if (!response.ok) {
                    const data = await response.json();
                    const errorMsg = data.error || 'Cleaning failed';
                    const suggestion = data.suggestion ? `\n💡 ${data.suggestion}` : '';
                    throw new Error(errorMsg + suggestion);
                }

                const res = await response.json();

                // Show success
                cleanBtn.textContent = 'Clean & Download';
                downloadArea.innerHTML = `
                    <div style="color:var(--text-secondary); margin-bottom:8px; font-size:0.9rem;">
                        Reduced rows from <b>${res.original_rows}</b> to <b>${res.cleaned_rows}</b>
                    </div>
                    <a href="${res.download_url}" class="download-link" target="_blank">
                        ⬇️ Download Cleaned File
                    </a>
                `;

            } catch (error) {
                downloadArea.innerHTML = `<div style="color:var(--error)">Error: ${error.message}</div>`;
            } finally {
                cleanBtn.disabled = false;
                cleanBtn.textContent = 'Clean & Download';
            }
        });
    }

    function renderDashboard(data) {
        resultsArea.classList.remove('hidden');

        // Text Stats - show both original and sampled if applicable
        const rowsText = data.is_sampled
            ? `${data.total_rows.toLocaleString()} (${data.sampled_rows.toLocaleString()} sampled)`
            : data.total_rows.toLocaleString();
        document.getElementById('stat-rows').textContent = rowsText;
        document.getElementById('stat-cols').textContent = data.headers.length;

        // Duplicate Stats
        const dupes = data.duplicates || { count: 0, percentage: 0 };
        const dupeElem = document.getElementById('stat-dupes');
        dupeElem.textContent = `${dupes.count} (${(dupes.percentage * 100).toFixed(1)}%)`;
        dupeElem.style.color = dupes.count > 0 ? 'var(--warning)' : 'var(--success)';

        // Data Health / Quality Issues
        renderQualityIssues(data.quality_issues);

        // Profile - New Component
        renderProfile(data.profile.columns);

        // Charts
        const chartsGrid = document.getElementById('charts-grid');
        chartsGrid.innerHTML = ''; // Clear previous

        if (data.recommendations && data.recommendations.length > 0) {
            data.recommendations.forEach((rec, index) => {
                createChartCard(rec, data.data_preview, index, chartsGrid);
            });
        } else {
            chartsGrid.innerHTML = `
                <div class="card full-width" style="text-align:center; color:var(--text-secondary)">
                    <h3>No specific visualizations recommended for this data structure.</h3>
                </div>
            `;
        }
    }

    function renderQualityIssues(issues) {
        const container = document.getElementById('quality-issues');
        container.innerHTML = '';

        if (!issues || issues.length === 0) {
            container.innerHTML = `
                <div style="text-align:center; padding:20px; color:var(--success);">
                    <div style="font-size:2rem; margin-bottom:10px;">✨</div>
                    <div>No critical issues found!</div>
                </div>
            `;
            return;
        }

        issues.forEach(issue => {
            const div = document.createElement('div');
            div.className = `issue-item issue-${issue.type}`;
            div.innerHTML = `
                <span><b>${issue.column}</b>: ${issue.message}</span>
                <span style="font-size:1.2rem;">${issue.type === 'critical' ? '🔴' : '⚠️'}</span>
            `;
            container.appendChild(div);
        });
    }

    function renderProfile(columns) {
        const profileContainer = document.getElementById('profile-preview');
        // Replace pre tag with a div container if it exists, or clear it
        profileContainer.innerHTML = '';
        profileContainer.className = 'profile-grid'; // Switch from 'json-preview' to grid

        Object.entries(columns).forEach(([name, stats]) => {
            const card = document.createElement('div');
            card.className = 'profile-card';

            let details = '';
            // Add specific details based on type
            if (stats.type === 'numeric') {
                if (stats.mean != null) details += `<div class="col-stat"><span>Mean</span> <span>${stats.mean.toFixed(2)}</span></div>`;
                if (stats.min != null) details += `<div class="col-stat"><span>Min</span> <span>${stats.min}</span></div>`;
                if (stats.max != null) details += `<div class="col-stat"><span>Max</span> <span>${stats.max}</span></div>`;
            } else if (stats.type === 'categorical' || stats.type === 'text') {
                details += `<div class="col-stat"><span>Unique</span> <span>${stats.unique}</span></div>`;
                // Top value
                if (stats.top_values) {
                    const top = Object.entries(stats.top_values).sort((a, b) => b[1] - a[1])[0];
                    if (top) details += `<div class="col-stat"><span>Top</span> <span>${top[0]} (${top[1]})</span></div>`;
                }
            } else {
                details += `<div class="col-stat"><span>Unique</span> <span>${stats.unique}</span></div>`;
            }

            // Common stats
            const missingClass = stats.missing > 0 ? 'color:#ef4444' : 'color:#10b981';

            card.innerHTML = `
                <div class="col-header">
                    <span class="col-name" title="${name}">${name.length > 15 ? name.substring(0, 15) + '...' : name}</span>
                    <span class="col-type">${stats.type}</span>
                </div>
                ${details}
                <div class="col-stat" style="margin-top:10px; border-top:1px solid rgba(255,255,255,0.05); padding-top:8px;">
                    <span>Missing</span> 
                    <span style="${missingClass}">${stats.missing} (${(stats.missing_pct * 100).toFixed(1)}%)</span>
                </div>
            `;
            profileContainer.appendChild(card);
        });
    }

    function createChartCard(rec, data, index, container) {
        const card = document.createElement('div');
        card.className = 'card chart-card';
        // Span full width if it's a heatmap or complex chart or many pie charts
        if (rec.type === 'heatmap' || rec.type === 'map') card.classList.add('full-width');

        const chartId = `chart-${index}`;

        card.innerHTML = `
            <h3>${rec.type.toUpperCase()} <span style="font-weight:400; font-size:0.9em; margin-left:10px; color:var(--text-secondary);">${rec.reason}</span></h3>
            <div id="${chartId}" style="width:100%; height:400px;"></div>
        `;

        container.appendChild(card);

        renderPlotlyChart(chartId, rec, data);
    }

    function renderPlotlyChart(elemId, rec, data) {
        const getCol = (name) => data.map(row => row[name]);

        // Premium Palette
        const palette = [
            '#6366f1', // Indigo
            '#8b5cf6', // Violet
            '#ec4899', // Pink
            '#f43f5e', // Rose
            '#10b981', // Emerald
            '#3b82f6', // Blue
            '#f59e0b', // Amber
            '#06b6d4', // Cyan
            '#d946ef', // Fuchsia
            '#84cc16'  // Lime
        ];

        const commonLayout = {
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: { family: 'Outfit, sans-serif', color: '#94a3b8' },
            margin: { t: 20, r: 20, l: 50, b: 50 },
            xaxis: { gridcolor: '#334155' },
            yaxis: { gridcolor: '#334155' },
            // Legend
            legend: { font: { color: '#cbd5e1' } }
        };

        let traces = [];
        let layout = { ...commonLayout };

        try {
            if (rec.type === 'line') {
                traces.push({
                    x: getCol(rec.x),
                    y: getCol(rec.y[0]),
                    type: 'scatter',
                    mode: 'lines',
                    line: { color: palette[Math.floor(Math.random() * 5)], width: 3, shape: 'spline' }, // Random cool color
                    fill: 'tozeroy', // Add fill for cooler look
                    fillcolor: 'rgba(99, 102, 241, 0.1)'
                });
            } else if (rec.type === 'histogram') {
                traces.push({
                    x: getCol(rec.column),
                    type: 'histogram',
                    marker: {
                        color: palette, // Cycle colors if possible, or just one nice one
                        color: getCol(rec.column), // Try to color by value if sensible, else solid
                        colorscale: 'Viridis',
                        line: { color: 'rgba(255,255,255,0.1)', width: 1 }
                    },
                    opacity: 0.8
                });
                // Fix for histogram color: usually needs single color or array matching bins. 
                // Let's stick to a nice gradient or single distinct color.
                traces[0].marker.color = palette[1];
            } else if (rec.type === 'bar') {
                const counts = {};
                getCol(rec.column).forEach(x => counts[x] = (counts[x] || 0) + 1);
                const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 20);

                traces.push({
                    x: sorted.map(x => x[0]),
                    y: sorted.map(x => x[1]),
                    type: 'bar',
                    marker: {
                        color: sorted.map((_, i) => palette[i % palette.length]) // Cycle through palette
                    }
                });
            } else if (rec.type === 'pie') {
                const counts = {};
                getCol(rec.column).forEach(x => counts[x] = (counts[x] || 0) + 1);
                const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1]);

                traces.push({
                    labels: sorted.map(x => x[0]),
                    values: sorted.map(x => x[1]),
                    type: 'pie',
                    hole: 0.4, // Donut style
                    textinfo: 'label+percent',
                    textposition: 'inside',
                    marker: {
                        colors: palette // Use full palette
                    },
                    hoverinfo: 'label+value+percent'
                });
            } else if (rec.type === 'scatter') {
                const xData = getCol(rec.x);
                const yData = getCol(rec.y);
                const useWebGL = xData.length > 10000; // Use WebGL for large datasets

                traces.push({
                    x: xData,
                    y: yData,
                    mode: 'markers',
                    type: useWebGL ? 'scattergl' : 'scatter',  // WebGL for >10k points
                    marker: {
                        color: yData, // Color by Y value
                        colorscale: 'Plasma',
                        size: useWebGL ? 5 : 8,  // Smaller points for WebGL
                        opacity: useWebGL ? 0.6 : 0.7,
                        line: { width: 0 }
                    }
                });
            } else if (rec.type === 'heatmap') {
                traces.push({
                    y: getCol(rec.columns[0]),
                    type: 'box',
                    name: rec.columns[0],
                    marker: { color: palette[0] },
                    boxpoints: 'all',
                    jitter: 0.3,
                    pointpos: -1.8
                });
                traces.push({
                    y: getCol(rec.columns[1]),
                    type: 'box',
                    name: rec.columns[1],
                    marker: { color: palette[2] },
                    boxpoints: 'all',
                    jitter: 0.3,
                    pointpos: -1.8
                });
            } else if (rec.type === 'map') {
                traces.push({
                    type: 'scattergeo',
                    lat: getCol(rec.lat),
                    lon: getCol(rec.lon),
                    marker: {
                        color: getCol(rec.lat),
                        colorscale: 'Inferno',
                        size: 8
                    }
                });
                layout.geo = {
                    bgcolor: 'rgba(0,0,0,0)',
                    showland: true,
                    landcolor: '#1e293b',
                    showocean: true,
                    oceancolor: '#020617',
                    showlakes: true,
                    lakecolor: '#020617'
                };
            }

            Plotly.newPlot(elemId, traces, layout, { responsive: true, displayModeBar: false });

        } catch (e) {
            console.error("Chart Error", e);
            document.getElementById(elemId).innerHTML = `<div style="text-align:center; padding:50px; color:var(--error);">Failed to render chart: ${e.message}</div>`;
        }
    }
});
