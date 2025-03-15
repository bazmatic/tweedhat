// Main JavaScript file for TweedHat web application

//  Document ready function
$(document).ready(function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Job status polling
    if ($('#job-status').length) {
        const jobId = $('#job-status').data('job-id');
        pollJobStatus(jobId);
    }
    
    // Form validation for API keys
    $('.api-key-form').on('submit', function(e) {
        const elevenlabsKey = $('#elevenlabs_api_key').val();
        const anthropicKey = $('#anthropic_api_key').val();
        
        if (!elevenlabsKey && !anthropicKey) {
            e.preventDefault();
            alert('Please provide at least one API key.');
            return false;
        }
        
        return true;
    });
    
    // Confirm job deletion
    $('.delete-job-form').on('submit', function(e) {
        if (!confirm('Are you sure you want to delete this job? This action cannot be undone.')) {
            e.preventDefault();
            return false;
        }
        return true;
    });
    
    // Toggle password visibility
    $('.toggle-password').on('click', function() {
        const passwordField = $($(this).data('target'));
        const type = passwordField.attr('type') === 'password' ? 'text' : 'password';
        passwordField.attr('type', type);
        $(this).find('i').toggleClass('fa-eye fa-eye-slash');
    });
});

/**
 * Poll job status and update UI
 * @param {string} jobId - The ID of the job to poll
 */
function pollJobStatus(jobId) {
    const statusElement = $('#job-status');
    const audioListElement = $('#audio-files-list');
    const errorElement = $('#job-error');
    
    // Function to update the UI based on job status
    function updateUI(data) {
        // Update status badge
        statusElement.removeClass().addClass('badge badge-' + data.status).text(formatStatus(data.status));
        
        // Update audio files list if available
        if (data.audio_files && data.audio_files.length > 0) {
            audioListElement.empty();
            data.audio_files.forEach(function(file, index) {
                const fileName = file.split('/').pop();
                audioListElement.append(
                    `<li class="list-group-item d-flex justify-content-between align-items-center">
                        <span>Tweet ${index + 1}</span>
                        <a href="/jobs/${jobId}/download/${fileName}" class="btn btn-sm btn-primary">
                            <i class="fas fa-download me-1"></i>Download
                        </a>
                    </li>`
                );
            });
            $('#audio-files-container').show();
        }
        
        // Show error if any
        if (data.error) {
            errorElement.text(data.error).parent().show();
        } else {
            errorElement.parent().hide();
        }
        
        // Continue polling if job is not completed or failed
        if (['pending', 'scraping', 'scraped', 'generating_audio', 'processing'].includes(data.status)) {
            setTimeout(function() {
                pollJobStatus(jobId);
            }, 5000); // Poll every 5 seconds
        } else {
            // Job is completed or failed, show appropriate message
            if (data.status === 'completed') {
                showAlert('success', 'Job completed successfully!');
            } else if (data.status === 'failed') {
                showAlert('danger', 'Job failed. Please check the error details.');
            }
        }
    }
    
    // Make AJAX request to get job status
    $.ajax({
        url: '/jobs/' + jobId + '/status',
        type: 'GET',
        dataType: 'json',
        success: updateUI,
        error: function(xhr, status, error) {
            console.error('Error polling job status:', error);
            showAlert('danger', 'Error checking job status. Please refresh the page.');
        }
    });
}

/**
 * Format job status for display
 * @param {string} status - The job status
 * @returns {string} - Formatted status text
 */
function formatStatus(status) {
    switch (status) {
        case 'pending':
            return 'Pending';
        case 'scraping':
            return 'Scraping Tweets';
        case 'scraped':
            return 'Tweets Scraped';
        case 'generating_audio':
            return 'Generating Audio';
        case 'processing':
            return 'Processing';
        case 'completed':
            return 'Completed';
        case 'failed':
            return 'Failed';
        default:
            return status.charAt(0).toUpperCase() + status.slice(1);
    }
}

/**
 * Show an alert message
 * @param {string} type - Alert type (success, danger, warning, info)
 * @param {string} message - Alert message
 */
function showAlert(type, message) {
    const alertHtml = `
        <div class="alert alert-${type} alert-dismissible fade show">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    // Insert alert before the main content
    $('.container').prepend(alertHtml);
    
    // Auto-dismiss after 5 seconds
    setTimeout(function() {
        $('.alert').alert('close');
    }, 5000);
} 