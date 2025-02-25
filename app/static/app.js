document.addEventListener('DOMContentLoaded', function() {
    // Fetch service status data from API
    fetchServiceStatus();

    // Set up refresh interval (every 30 seconds)
    setInterval(fetchServiceStatus, 30000);

    // Add event listener for historical uptime link
    document.getElementById('view-historical').addEventListener('click', function(e) {
        e.preventDefault();
        alert('Historical uptime view is not implemented yet.');
    });
});

function fetchServiceStatus() {
    fetch('/api/status')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            renderServiceStatus(data);
        })
        .catch(error => {
            console.error('Error fetching service status:', error);
            document.getElementById('services-container').innerHTML = `
                <div class="error">
                    Error loading service status data. Please try again later.
                </div>
            `;
        });
}

function renderServiceStatus(services) {
    const servicesContainer = document.getElementById('services-container');
    const incidentsContainer = document.getElementById('incidents-container');
    
    // Clear containers
    servicesContainer.innerHTML = '';
    incidentsContainer.innerHTML = '';
    
    // Track if there are any active incidents
    let hasActiveIncidents = false;
    
    // Render each service
    services.forEach(service => {
        // Create service component
        const serviceElement = createServiceElement(service);
        servicesContainer.appendChild(serviceElement);
        
        // Check if service has an active incident
        if (service.current_status !== 'operational') {
            hasActiveIncidents = true;
            const incidentElement = createIncidentElement(service);
            incidentsContainer.appendChild(incidentElement);
        }
    });
    
    // Show "No active incidents" message if needed
    if (!hasActiveIncidents) {
        incidentsContainer.innerHTML = '<div id="no-incidents">No active incidents reported.</div>';
    }

    // Initialize tooltips
    initializeTooltips();
}

function createServiceElement(service) {
    const serviceElement = document.createElement('div');
    serviceElement.className = 'component-container';
    
    // Format the uptime timeline
    const uptimeTimeline = createUptimeTimeline(service.status_history);
    
    serviceElement.innerHTML = `
        <div class="component-inner-container">
            <div class="service-header">
                <span class="service-name">
                    ${service.name}
                    <a href="${service.url}" target="_blank" class="link-icon">
                        <i class="fas fa-external-link-alt"></i>
                    </a>
                </span>
            </div>
            <div class="status-tag ${service.current_status}">
                ${capitalizeFirstLetter(service.current_status)}
            </div>
            <div class="uptime-wrapper">
                <div class="shared-partial">
                    <svg class="availability-time-line-graphic" viewBox="0 0 1000 34" preserveAspectRatio="none">
                        ${uptimeTimeline}
                    </svg>
                    <div class="time-range">
                        <span>${service.hours_ago} hours ago</span>
                        <span>Now</span>
                    </div>
                    <div class="legend">
                        <span class="legend-item light">${service.uptime}% uptime</span>
                        <span class="spacer"></span>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    return serviceElement;
}

function createUptimeTimeline(statusHistory) {
    if (!statusHistory || statusHistory.length === 0) {
        return '';
    }
    
    const totalBlocks = statusHistory.length;
    const blockWidth = 1000 / totalBlocks;
    
    let timeline = '';
    
    statusHistory.forEach((status, index) => {
        const x = index * blockWidth;
        const tooltipText = `${status.date} ${status.hour}:${status.minute.toString().padStart(2, '0')}
Status: ${capitalizeFirstLetter(status.status)}`;
        
        // Determine fill color based on status
        let fillColor = '#999999'; // Default gray for unknown
        if (status.status === 'operational') {
            fillColor = '#00B16A'; // Green
        } else if (status.status === 'issue') {
            fillColor = '#FFB020'; // Yellow/Orange
        } else if (status.status === 'outage') {
            fillColor = '#D14343'; // Red
        }
        
        timeline += `
            <rect 
                class="uptime-day" 
                x="${x}" 
                y="0" 
                width="${blockWidth}" 
                height="34"
                fill="${fillColor}"
                data-tooltip="${tooltipText}"
            ></rect>
        `;
    });
    
    return timeline;
}

function createIncidentElement(service) {
    const incidentElement = document.createElement('div');
    incidentElement.className = 'incident-item';
    
    incidentElement.innerHTML = `
        <h3>${service.name} - ${capitalizeFirstLetter(service.current_status)}</h3>
        <p>${service.failure_duration || 'Issue detected recently'}</p>
    `;
    
    return incidentElement;
}

function capitalizeFirstLetter(string) {
    return string.charAt(0).toUpperCase() + string.slice(1);
}

function initializeTooltips() {
    // Add tooltip functionality for the uptime timeline
    const uptimeRects = document.querySelectorAll('.uptime-day');
    
    uptimeRects.forEach(rect => {
        rect.addEventListener('mouseover', function(e) {
            const tooltipText = this.getAttribute('data-tooltip');
            if (!tooltipText) return;
            
            // Check if tooltip already exists
            let tooltip = document.getElementById('custom-tooltip');
            if (!tooltip) {
                // Create tooltip element if it doesn't exist
                tooltip = document.createElement('div');
                tooltip.id = 'custom-tooltip';
                tooltip.className = 'custom-tooltip';
                document.body.appendChild(tooltip);
            }
            
            // Set tooltip content and position
            tooltip.textContent = tooltipText;
            tooltip.style.display = 'block';
            tooltip.style.left = (e.pageX + 10) + 'px';
            tooltip.style.top = (e.pageY + 10) + 'px';
        });
        
        rect.addEventListener('mouseout', function() {
            const tooltip = document.getElementById('custom-tooltip');
            if (tooltip) {
                tooltip.style.display = 'none';
            }
        });
        
        rect.addEventListener('mousemove', function(e) {
            const tooltip = document.getElementById('custom-tooltip');
            if (tooltip) {
                tooltip.style.left = (e.pageX + 10) + 'px';
                tooltip.style.top = (e.pageY + 10) + 'px';
            }
        });
    });
} 