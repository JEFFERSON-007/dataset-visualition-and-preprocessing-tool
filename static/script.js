document.addEventListener('DOMContentLoaded', () => {
    console.log("🚀 DataLyze Pro JS Loaded - Build 19:05");
    // Elements
    const fileInput = document.getElementById('file-input');
    const uploadBtn = document.getElementById('upload-btn');
    const dropZone = document.getElementById('drop-zone');
    const statusMsg = document.getElementById('status-message');
    const fileNameDisplay = document.getElementById('file-name-display');
    const resultsArea = document.getElementById('results-area');
    const fileInfoArea = document.getElementById('file-info-area');
    const sessionIdInput = document.getElementById('session-id');

    // Theme Toggle
    const themeBtn = document.getElementById('theme-toggle');
    if (themeBtn) {
        themeBtn.addEventListener('click', () => {
            document.body.classList.toggle('theme-light');
            themeBtn.textContent = document.body.classList.contains('theme-light') ? '🌙' : '☀️';
        });
    }

    // --- File Handling ---
    dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('dragover'); });
    dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault(); dropZone.classList.remove('dragover');
        if (e.dataTransfer.files.length) handleFileSelect(e.dataTransfer.files[0]);
    });
    dropZone.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', () => { if (fileInput.files.length) handleFileSelect(fileInput.files[0]); });

    function handleFileSelect(file) {
        if (file.size > 25 * 1024 * 1024 * 1024) return alert("File too large (>25GB)");

        fileNameDisplay.textContent = `Selected: ${file.name} (${(file.size / 1048576).toFixed(1)}MB)`;
        fileInfoArea.classList.remove('hidden');
        uploadBtn.disabled = false;

        // Reset state
        resultsArea.classList.add('hidden');
        statusMsg.textContent = '';
    }

    // --- Upload ---
    uploadBtn.addEventListener('click', async () => {
        const file = fileInput.files[0];
        if (!file) return;

        setStatus('Uploading & Processing...', 'info');
        uploadBtn.disabled = true;

        const formData = new FormData();
        formData.append('file', file);

        try {
            const res = await fetch('/upload', { method: 'POST', body: formData });
            const data = await res.json();

            if (!res.ok) throw new Error(data.error || 'Upload failed');

            // Success
            sessionIdInput.value = data.session_id;
            setStatus('Analysis Complete!', 'success');
            renderDashboard(data);

            // Populate merge dropdown
            updateKeyDropdown(data.columns);

        } catch (e) {
            setStatus('Error: ' + e.message, 'error');
        } finally {
            uploadBtn.disabled = false;
        }
    });

    // --- Merge Studio ---
    window.toggleSection = function (id) {
        const sec = document.getElementById(id);
        if (sec) sec.classList.toggle('hidden');
    }
    const mergeBtn = document.getElementById('merge-btn');
    if (mergeBtn) {
        mergeBtn.addEventListener('click', async () => {
            const sessionId = sessionIdInput.value;
            const files = document.getElementById('merge-file-input').files;
            const leftKey = document.getElementById('merge-left-key').value;
            const rightKey = document.getElementById('merge-right-key').value;
            const how = document.getElementById('merge-how').value;

            if (!sessionId) return alert("Upload a primary dataset first.");
            if (files.length === 0) return alert("Select at least one secondary file.");
            if (!leftKey || !rightKey) return alert("Please specify the merge keys.");

            mergeBtn.disabled = true;
            mergeBtn.textContent = 'Merging...';

            const formData = new FormData();
            formData.append('primary_id', sessionId);
            formData.append('left_key', leftKey);
            formData.append('right_key', rightKey);
            formData.append('how', how);

            for (let file of files) {
                formData.append('secondary_files', file);
            }

            try {
                const res = await fetch('/merge', { method: 'POST', body: formData });
                const data = await res.json();

                if (!res.ok) throw new Error(data.error || 'Merge failed');

                alert(`Merge Successful! Result: ${data.total_rows.toLocaleString()} rows and ${data.columns.length} columns.`);

                // Re-download the result automatically for large datasets
                postToEndpoint('/download', { session_id: sessionId });

            } catch (e) {
                alert('Connection Error: ' + e.message);
                console.error(e);
            } finally {
                mergeBtn.disabled = false;
                mergeBtn.textContent = 'Run Bulk Merge';
            }
        });
    }

    // --- Clean Studio ---
    const cleanBtn = document.getElementById('clean-btn');
    if (cleanBtn) {
        cleanBtn.addEventListener('click', async () => {
            const sessionId = sessionIdInput.value;
            if (!sessionId) return alert("No active session");

            cleanBtn.disabled = true;
            cleanBtn.textContent = 'Cleaning...';

            const formData = new FormData();
            formData.append('session_id', sessionId);
            formData.append('remove_duplicates', document.getElementById('opt-duplicates').checked);
            formData.append('impute_missing', document.getElementById('opt-missing').checked);
            formData.append('drop_constant', document.getElementById('opt-constant').checked);

            try {
                const res = await fetch('/clean', { method: 'POST', body: formData });
                const data = await res.json();

                if (!res.ok) throw new Error(data.error || 'Cleaning failed');

                const downloadArea = document.getElementById('download-area');
                downloadArea.innerHTML = `
                    <div style="color:var(--success); margin-bottom:10px;">
                        Cleaned! Rows: ${data.rows_before} ➝ ${data.rows_after}
                    </div>
                `;
                // Trigger actual file download
                postToEndpoint('/download', { session_id: sessionId });

            } catch (e) {
                alert('Cleaning Error: ' + e.message);
            } finally {
                cleanBtn.disabled = false;
                cleanBtn.textContent = 'Clean & Download';
            }
        });
    }


    // --- Rendering ---
    function renderDashboard(data) {
        resultsArea.classList.remove('hidden');

        // Stats
        document.getElementById('stat-rows').textContent = data.total_rows.toLocaleString();
        document.getElementById('stat-cols').textContent = data.columns.length;
        document.getElementById('stat-dupes').textContent = (data.profile.duplicates || 0).toLocaleString();

        // Quality Issues (Data Health)
        const qualityDiv = document.getElementById('quality-issues');
        if (data.profile.health && data.profile.health.length > 0) {
            qualityDiv.innerHTML = data.profile.health.map(issue => `
                <div class="issue-card ${issue.type}">
                    <div class="issue-title">
                        <span>${issue.type === 'warning' ? '⚠️' : 'ℹ️'}</span>
                        <b>${issue.title}</b>
                    </div>
                    <div class="issue-desc">${issue.desc}</div>
                </div>
            `).join('');
        } else {
            qualityDiv.innerHTML = `<div style="color:var(--success)">✨ No major issues detected. Data looks healthy!</div>`;
        }

        // Charts
        const grid = document.getElementById('charts-grid');
        grid.innerHTML = '';
        data.recommendations.forEach((rec, i) => {
            const id = `chart-${i}`;
            const card = document.createElement('div');
            card.className = 'card chart-card';
            card.innerHTML = `<h3>${rec.reason}</h3><div id="${id}" style="height:300px"></div>`;
            grid.appendChild(card);
            renderPlotly(id, rec, data.preview);
        });

        // Profile
        const prof = document.getElementById('profile-preview');
        prof.innerHTML = Object.entries(data.profile.columns).map(([k, v]) => `
            <div class="col-card">
                <b>${k}</b> <span style="font-size:0.8em; opacity:0.7">(${v.type})</span><br>
                Missing: <span style="color:${v.missing > 0 ? 'var(--error)' : 'var(--success)'}">${v.missing}</span><br>
                Unique: ${v.unique}
            </div>
        `).join('');
    }

    function renderPlotly(id, rec, previewData) {
        const getCol = (c) => previewData.map(r => r[c]);
        const theme = document.body.classList.contains('theme-light') ? 'light' : 'dark';
        const color = theme === 'light' ? '#333' : '#cbd5e1';

        let trace = {};
        if (rec.type === 'bar' || rec.type === 'histogram') {
            trace = { x: getCol(rec.column), type: rec.type, marker: { color: '#6366f1' } };
        } else if (rec.type === 'scatter') {
            trace = { x: getCol(rec.x), y: getCol(rec.y), mode: 'markers', type: 'scatter', marker: { color: '#ec4899' } };
        } else if (rec.type === 'box') {
            trace = { y: getCol(rec.column), type: 'box', marker: { color: '#a855f7' } };
        } else if (rec.type === 'pie') {
            // aggregate for pie
            const counts = {}; getCol(rec.column).forEach(x => counts[x] = (counts[x] || 0) + 1);
            trace = { labels: Object.keys(counts), values: Object.values(counts), type: 'pie' };
        }

        const layout = {
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: { color: color, family: 'Outfit' },
            margin: { t: 10, b: 30, l: 30, r: 10 },
            showlegend: false
        };

        Plotly.newPlot(id, [trace], layout, { displayModeBar: false, responsive: true });
    }

    // Tools
    function updateKeyDropdown(cols) {
        const sel = document.getElementById('merge-left-key');
        if (sel) sel.innerHTML = cols.map(c => `<option value="${c}">${c}</option>`).join('');
    }

    function setStatus(msg, type) {
        statusMsg.textContent = msg;
        statusMsg.className = type;
        statusMsg.style.color = type === 'error' ? 'var(--error)' : (type === 'success' ? 'var(--success)' : 'var(--text-primary)');
    }

    // Unified helper for file download endpoints (POST)
    function postToEndpoint(endpoint, params) {
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = endpoint;
        form.style.display = 'none';

        for (const [key, value] of Object.entries(params)) {
            const input = document.createElement('input');
            input.type = 'hidden';
            input.name = key;
            input.value = value;
            form.appendChild(input);
        }

        document.body.appendChild(form);
        form.submit();
        document.body.removeChild(form);
    }

    // Globals
    window.cleanData = () => toggleSection('clean-studio');

    window.autoPrepML = () => {
        const sid = sessionIdInput.value;
        if (!sid) return alert("Please upload data first");
        postToEndpoint('/auto_prep_ml', { session_id: sid });
    }

    window.downloadReport = () => {
        const sid = sessionIdInput.value;
        if (!sid) return alert("Please upload data first");
        postToEndpoint('/generate_report', { session_id: sid });
    };
});
