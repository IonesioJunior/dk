/**
 * Reusable Upload Component
 * A modular file upload component that can be used across different pages
 */

// Prevent multiple script executions
if (window.uploadComponentScriptLoaded) {
    console.log('Upload component script already loaded, skipping re-execution...');
} else {
    window.uploadComponentScriptLoaded = true;

class UploadComponent {
    constructor(containerElement, options = {}) {
        this.container = containerElement;
        this.options = {
            apiEndpoint: options.apiEndpoint || '/api/documents-collection/bulk',
            acceptedFileTypes: options.acceptedFileTypes || '.txt,.md,.json,.pdf,.doc,.docx',
            maxFileSize: options.maxFileSize || 10 * 1024 * 1024, // 10MB default
            onUploadComplete: options.onUploadComplete || (() => {}),
            onUploadError: options.onUploadError || (() => {}),
            onUploadProgress: options.onUploadProgress || (() => {}),
            allowMultiple: options.allowMultiple !== false, // default true
            ...options
        };

        this.selectedFiles = [];
        this.isUploading = false;

        this.init();
    }

    init() {
        this.setupElements();
        this.bindEvents();

        // Initialize Lucide icons if available
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    }

    setupElements() {
        // Get all the component elements
        this.triggerBtn = this.container.querySelector('.upload-trigger-btn');
        this.modal = this.container.querySelector('.upload-modal');
        this.form = this.container.querySelector('.upload-form');
        this.fileInput = this.container.querySelector('.file-input');
        this.dropArea = this.container.querySelector('.file-drop-area');
        this.browseBtn = this.container.querySelector('.browse-btn');
        this.selectedFilesDiv = this.container.querySelector('.selected-files');
        this.filesListDiv = this.container.querySelector('.files-list');
        this.filesSummary = this.container.querySelector('.files-summary');
        this.clearAllBtn = this.container.querySelector('.clear-all-files-btn');
        this.submitBtn = this.container.querySelector('.upload-submit-btn');
        this.progressDiv = this.container.querySelector('.upload-progress');

        // Progress elements
        this.progressElements = {
            overall: {
                bar: this.container.querySelector('.overall-progress-bar'),
                text: this.container.querySelector('.overall-progress-text')
            },
            current: {
                container: this.container.querySelector('.current-file-progress'),
                name: this.container.querySelector('.current-file-name'),
                bar: this.container.querySelector('.current-file-progress-bar'),
                text: this.container.querySelector('.current-file-progress-text')
            },
            status: this.container.querySelector('.upload-status-text')
        };

        this.btnText = this.container.querySelector('.upload-btn-text');
        this.spinner = this.container.querySelector('.upload-spinner');

        // Set file input accept attribute
        if (this.fileInput) {
            this.fileInput.setAttribute('accept', this.options.acceptedFileTypes);
            this.fileInput.multiple = this.options.allowMultiple;
        }

        // Get API endpoint from data attribute or use option
        const dataEndpoint = this.container.getAttribute('data-api-endpoint');
        if (dataEndpoint) {
            this.options.apiEndpoint = dataEndpoint;
        }
    }

    bindEvents() {
        // Trigger button click
        if (this.triggerBtn && this.modal) {
            this.triggerBtn.addEventListener('click', () => {
                this.openModal();
            });
        }

        // File input change
        if (this.fileInput) {
            this.fileInput.addEventListener('change', (e) => {
                if (e.target.files.length > 0) {
                    this.handleFilesSelect(Array.from(e.target.files));
                }
            });
        }

        // Browse button
        if (this.browseBtn) {
            this.browseBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.fileInput?.click();
            });
        }

        // Drag and drop events
        if (this.dropArea) {
            this.dropArea.addEventListener('dragover', (e) => {
                e.preventDefault();
                this.dropArea.classList.add('border-blue-500');
            });

            this.dropArea.addEventListener('dragleave', (e) => {
                e.preventDefault();
                this.dropArea.classList.remove('border-blue-500');
            });

            this.dropArea.addEventListener('drop', (e) => {
                e.preventDefault();
                this.dropArea.classList.remove('border-blue-500');

                const files = e.dataTransfer.files;
                if (files.length > 0) {
                    this.handleFilesSelect(Array.from(files));
                }
            });

            // Make drop area clickable
            this.dropArea.addEventListener('click', (e) => {
                // Only trigger if the click wasn't on the browse button
                if (e.target !== this.browseBtn && !this.browseBtn?.contains(e.target)) {
                    this.fileInput?.click();
                }
            });
        }

        // Form submission
        if (this.form) {
            this.form.addEventListener('submit', (e) => {
                e.preventDefault();
                this.uploadFiles();
            });
        }

        // Clear all files
        if (this.clearAllBtn) {
            this.clearAllBtn.addEventListener('click', () => {
                this.clearAllFiles();
            });
        }
    }

    openModal() {
        if (this.modal && typeof UIkit !== 'undefined') {
            UIkit.modal(this.modal).show();
        }
    }

    closeModal() {
        if (this.modal && typeof UIkit !== 'undefined') {
            UIkit.modal(this.modal).hide();
        }
    }

    handleFilesSelect(files) {
        // Validate files
        const validFiles = files.filter(file => this.validateFile(file));

        if (validFiles.length === 0) {
            this.showNotification('No valid files selected. Please check file types and sizes.', 'warning');
            return;
        }

        if (!this.options.allowMultiple) {
            this.selectedFiles = [validFiles[0]];
        } else {
            // Add new files to selection (avoid duplicates by name and size)
            validFiles.forEach(file => {
                const existingFile = this.selectedFiles.find(f =>
                    f.name === file.name && f.size === file.size
                );
                if (!existingFile) {
                    this.selectedFiles.push(file);
                }
            });
        }

        this.updateSelectedFilesDisplay();
    }

    validateFile(file) {
        // Check file type
        const acceptedFileTypes = this.options.acceptedFileTypes || '.txt,.md,.json,.pdf,.doc,.docx';
        const acceptedTypes = acceptedFileTypes.split(',').map(type => type.trim());
        const fileExtension = '.' + file.name.split('.').pop().toLowerCase();

        if (!acceptedTypes.includes(fileExtension)) {
            this.showNotification(`File type ${fileExtension} is not supported.`, 'warning');
            return false;
        }

        // Check file size
        if (file.size > this.options.maxFileSize) {
            this.showNotification(`File ${file.name} is too large. Maximum size is ${this.formatFileSize(this.options.maxFileSize)}.`, 'warning');
            return false;
        }

        return true;
    }

    updateSelectedFilesDisplay() {
        if (!this.selectedFilesDiv || !this.filesListDiv || !this.filesSummary || !this.submitBtn) return;

        if (this.selectedFiles.length === 0) {
            this.selectedFilesDiv.classList.add('hidden');
            this.submitBtn.disabled = true;
            return;
        }

        // Show selected files section
        this.selectedFilesDiv.classList.remove('hidden');
        this.submitBtn.disabled = false;

        // Update summary
        const totalSize = this.selectedFiles.reduce((sum, file) => sum + file.size, 0);
        this.filesSummary.textContent = `${this.selectedFiles.length} file${this.selectedFiles.length > 1 ? 's' : ''} selected (${this.formatFileSize(totalSize)})`;

        // Update files list
        this.filesListDiv.innerHTML = this.selectedFiles.map((file, index) => {
            const fileType = this.getFileExtension(file.name).toUpperCase();
            const typeIcon = this.getFileTypeIcon(fileType);

            return `
                <div class="flex items-center space-x-3 p-3 theme-bg-surface theme-border border rounded-lg group hover:theme-bg-background transition-colors duration-200">
                    <div class="flex-shrink-0">
                        <i data-lucide="${typeIcon}" class="h-5 w-5 theme-text-muted"></i>
                    </div>
                    <div class="flex-1 min-w-0">
                        <p class="font-medium theme-text-primary truncate">${file.name}</p>
                        <p class="text-sm theme-text-secondary">${fileType} • ${this.formatFileSize(file.size)}</p>
                    </div>
                    <button type="button" onclick="this.closest('.upload-component').uploadComponent.removeSelectedFile(${index})" class="flex-shrink-0 p-1.5 rounded-lg theme-text-muted hover:theme-danger transition-colors duration-200 opacity-0 group-hover:opacity-100" style="hover:background-color: rgba(var(--color-danger-rgb, 220, 53, 69), 0.1);">
                        <i data-lucide="x" class="h-4 w-4"></i>
                    </button>
                </div>
            `;
        }).join('');

        // Re-initialize Lucide icons
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    }

    removeSelectedFile(index) {
        if (this.selectedFiles && index >= 0 && index < this.selectedFiles.length) {
            this.selectedFiles.splice(index, 1);
            this.updateSelectedFilesDisplay();
        }
    }

    clearAllFiles() {
        this.selectedFiles = [];
        if (this.fileInput) this.fileInput.value = '';
        this.updateSelectedFilesDisplay();
    }

    async uploadFiles() {
        if (!this.selectedFiles || this.selectedFiles.length === 0 || this.isUploading) return;

        this.isUploading = true;

        try {
            // Show uploading state
            this.setUploadingState(true);

            // Upload files
            await this.uploadMultipleFiles(this.selectedFiles);

            // Success
            this.closeModal();
            const count = this.selectedFiles.length;
            this.showNotification(`${count} document${count > 1 ? 's' : ''} uploaded successfully!`, 'success');

            // Call success callback
            this.options.onUploadComplete(this.selectedFiles);

            // Reset form
            this.resetForm();

        } catch (error) {
            console.error('Upload error:', error);
            this.showNotification('Failed to upload documents. Please try again.', 'error');
            this.options.onUploadError(error);
        } finally {
            this.setUploadingState(false);
            this.isUploading = false;
        }
    }

    async uploadMultipleFiles(files) {
        const totalFiles = files.length;

        // Show current file progress
        this.progressElements.current.container?.classList.remove('hidden');

        // Process files in batches for better performance
        const batchSize = 5;
        const batches = [];
        for (let i = 0; i < files.length; i += batchSize) {
            batches.push(files.slice(i, i + batchSize));
        }

        let completedFiles = 0;
        const failedFiles = [];

        for (const batch of batches) {
            // Prepare documents for bulk upload
            const documents = [];

            // Read all files in the batch
            this.progressElements.status.textContent = `Reading files (${completedFiles + 1}-${Math.min(completedFiles + batch.length, totalFiles)} of ${totalFiles})...`;

            for (let i = 0; i < batch.length; i++) {
                const file = batch[i];

                // Update current file progress
                this.progressElements.current.name.textContent = `Reading: ${file.name}`;
                this.updateProgress(this.progressElements.current, (i / batch.length) * 100);

                try {
                    const content = await this.readFileContent(file);
                    documents.push({
                        file_name: file.name,
                        content: content,
                        metadata: {
                            original_size: file.size,
                            mime_type: file.type
                        }
                    });
                } catch (error) {
                    console.error(`Failed to read file ${file.name}:`, error);
                    failedFiles.push(file.name);
                }
            }

            // Upload batch if we have documents
            if (documents.length > 0) {
                this.progressElements.status.textContent = `Uploading batch (${completedFiles + 1}-${Math.min(completedFiles + documents.length, totalFiles)} of ${totalFiles})...`;
                this.progressElements.current.name.textContent = `Uploading ${documents.length} files...`;
                this.updateProgress(this.progressElements.current, 100);

                try {
                    const response = await fetch(this.options.apiEndpoint, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            documents: documents
                        })
                    });

                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }

                    completedFiles += documents.length;

                } catch (error) {
                    console.error('Batch upload error:', error);
                    // Add all files in this batch to failed files
                    documents.forEach(doc => failedFiles.push(doc.file_name));
                }
            }

            // Update overall progress
            const overallProgress = (completedFiles / totalFiles) * 100;
            this.updateProgress(this.progressElements.overall, overallProgress);
            this.options.onUploadProgress(overallProgress, completedFiles, totalFiles);
        }

        // Final status
        if (failedFiles.length > 0) {
            this.progressElements.status.textContent = `Completed with ${failedFiles.length} errors`;
            console.warn('Failed files:', failedFiles);
            throw new Error(`Failed to upload ${failedFiles.length} file(s): ${failedFiles.join(', ')}`);
        } else {
            this.progressElements.status.textContent = `Successfully uploaded ${completedFiles} files`;
        }
    }

    updateProgress(progressElements, percentage) {
        if (progressElements.bar) {
            progressElements.bar.style.width = `${percentage}%`;
        }
        if (progressElements.text) {
            progressElements.text.textContent = `${Math.round(percentage)}%`;
        }
    }

    readFileContent(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = (e) => resolve(e.target.result);
            reader.onerror = (e) => reject(e);
            reader.readAsText(file);
        });
    }

    setUploadingState(isUploading) {
        if (this.submitBtn && this.btnText && this.spinner && this.progressDiv) {
            this.submitBtn.disabled = isUploading;
            this.btnText.textContent = isUploading ? 'Uploading...' : 'Upload Documents';

            if (isUploading) {
                this.spinner.classList.remove('hidden');
                this.progressDiv.classList.remove('hidden');
            } else {
                this.spinner.classList.add('hidden');
                this.progressDiv.classList.add('hidden');
            }
        }
    }

    resetForm() {
        if (this.fileInput) this.fileInput.value = '';
        if (this.selectedFilesDiv) this.selectedFilesDiv.classList.add('hidden');
        if (this.submitBtn) this.submitBtn.disabled = true;
        if (this.progressDiv) this.progressDiv.classList.add('hidden');
        if (this.progressElements.current.container) this.progressElements.current.container.classList.add('hidden');

        this.selectedFiles = [];
    }

    // Utility methods
    getFileExtension(fileName) {
        return fileName.split('.').pop() || 'unknown';
    }

    getFileTypeIcon(fileType) {
        const iconMap = {
            'TXT': 'file-text',
            'MD': 'file-code',
            'JSON': 'braces',
            'PDF': 'file-type',
            'DOC': 'file-text',
            'DOCX': 'file-text'
        };
        return iconMap[fileType] || 'file';
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    showNotification(message, type = 'info') {
        // Use Toaster if available
        if (typeof window.Toaster !== 'undefined') {
            switch(type) {
                case 'success':
                    window.Toaster.success(message);
                    break;
                case 'warning':
                    window.Toaster.warning(message);
                    break;
                case 'danger':
                case 'error':
                    window.Toaster.error(message);
                    break;
                default:
                    window.Toaster.info(message);
            }
            return;
        }

        // Fallback to UIkit notifications if available
        if (typeof UIkit !== 'undefined') {
            UIkit.notification(message, { status: type, pos: 'bottom-right' });
            return;
        }

        // Fallback to console log
        console.log(`[${type.toUpperCase()}] ${message}`);
    }

    // Public API methods
    destroy() {
        // Clean up event listeners and DOM references
        this.selectedFiles = [];
        this.isUploading = false;
    }

    getSelectedFiles() {
        return [...this.selectedFiles];
    }

    setApiEndpoint(endpoint) {
        this.options.apiEndpoint = endpoint;
    }
}

// Auto-initialize upload components on page load
function initializeUploadComponents() {
    const uploadComponents = document.querySelectorAll('.upload-component');

    uploadComponents.forEach(container => {
        // Skip if already initialized
        if (container.uploadComponent) return;

        // Get options from data attributes
        const options = {
            apiEndpoint: container.getAttribute('data-api-endpoint'),
            acceptedFileTypes: container.getAttribute('data-accepted-types'),
            allowMultiple: container.getAttribute('data-allow-multiple') !== 'false'
        };

        // Initialize component
        container.uploadComponent = new UploadComponent(container, options);
    });
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeUploadComponents);
} else {
    initializeUploadComponents();
}

// Export for manual initialization
window.UploadComponent = UploadComponent;
window.initializeUploadComponents = initializeUploadComponents;

} // End of script loading protection
