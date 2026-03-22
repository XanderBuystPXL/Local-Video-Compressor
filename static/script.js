document.addEventListener('DOMContentLoaded', () => {
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('file-input');
    const fileNameDisplay = document.getElementById('file-name-display');
    const compressBtn = document.getElementById('compress-btn');
    const targetSizeInput = document.getElementById('target-size');
    const statusDiv = document.getElementById('status');
    const statusText = document.getElementById('status-text');
    const errorDiv = document.getElementById('error-message');

    let selectedFile = null;

    // Handle drag events
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropzone.addEventListener(eventName, () => {
            dropzone.classList.add('active');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, () => {
            dropzone.classList.remove('active');
        }, false);
    });

    // Handle drops
    dropzone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFiles(files);
    });

    // Handle clicks
    dropzone.addEventListener('click', () => {
        fileInput.click();
    });

    fileInput.addEventListener('change', function() {
        handleFiles(this.files);
    });

    function handleFiles(files) {
        hideError();
        if (files.length === 0) return;
        
        const file = files[0];
        
        if (!file.type.startsWith('video/')) {
            showError("Please select a valid video file.");
            resetSelection();
            return;
        }

        selectedFile = file;
        fileNameDisplay.textContent = file.name;
        fileNameDisplay.style.color = "var(--accent)";
        compressBtn.disabled = false;
        
        const fileSizeMB = file.size / (1024 * 1024);
        let currentTarget = parseFloat(targetSizeInput.value);
        if (isNaN(currentTarget)) {
            currentTarget = 10;
        }
        
        if (currentTarget >= fileSizeMB) {
            targetSizeInput.value = Math.max(0.1, (fileSizeMB * 0.9)).toFixed(1);
        }
    }

    function resetSelection() {
        selectedFile = null;
        fileNameDisplay.textContent = "Drag & Drop your video here";
        fileNameDisplay.style.color = "var(--text-primary)";
        compressBtn.disabled = true;
        fileInput.value = "";
    }

    function showError(msg) {
        errorDiv.textContent = msg;
        errorDiv.classList.remove('hidden');
    }
    
    function hideError() {
        errorDiv.classList.add('hidden');
    }

    compressBtn.addEventListener('click', async () => {
        if (!selectedFile) return;

        const targetSize = parseFloat(targetSizeInput.value);
        if (isNaN(targetSize) || targetSize <= 0) {
            showError("Please enter a valid target size.");
            return;
        }

        const originalSizeMB = selectedFile.size / (1024 * 1024);
        if (targetSize >= originalSizeMB) {
            showError(`Target size (${targetSize}MB) must be smaller than the original file size (${originalSizeMB.toFixed(2)}MB).`);
            return;
        }

        hideError();
        compressBtn.disabled = true;
        dropzone.style.pointerEvents = 'none';
        statusDiv.classList.remove('hidden');
        statusText.textContent = 'Compressing video... (This may take a while)';
        statusText.style.color = "var(--text-primary)";

        const formData = new FormData();
        formData.append('file', selectedFile);
        formData.append('target_size', targetSize);

        try {
            const response = await fetch('/compress', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                let errorData;
                try {
                    errorData = await response.json();
                } catch {
                    throw new Error(`Compression failed with status: ${response.status}`);
                }
                throw new Error(errorData.detail || 'Compression failed');
            }

            let downloadFilename = selectedFile.name.replace(/\.[^/.]+$/, "") + "_compressed.mp4";
            const disposition = response.headers.get('Content-Disposition');
            if (disposition && disposition.indexOf('filename=') !== -1) {
                const filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
                const matches = filenameRegex.exec(disposition);
                if (matches != null && matches[1]) { 
                    downloadFilename = matches[1].replace(/['"]/g, '');
                }
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = downloadFilename;
            document.body.appendChild(a);
            a.click();
            
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            statusText.textContent = 'Compression complete! Download started.';
            statusText.style.color = "var(--success-text)";
            
            setTimeout(() => {
                resetSelection();
                dropzone.style.pointerEvents = 'auto';
                statusDiv.classList.add('hidden');
                statusText.style.color = "var(--text-primary)";
            }, 5000);

        } catch (error) {
            showError(error.message);
            compressBtn.disabled = false;
            dropzone.style.pointerEvents = 'auto';
            statusDiv.classList.add('hidden');
        }
    });
});
