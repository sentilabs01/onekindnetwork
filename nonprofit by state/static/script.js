// Dark mode functionality
const themeToggle = document.getElementById('themeToggle');
const html = document.documentElement;
const advancedSearchToggle = document.getElementById('advancedSearchToggle');
const advancedSearch = document.getElementById('advancedSearch');

// Check for saved theme preference
const savedTheme = localStorage.getItem('theme') || 'light';
html.setAttribute('data-bs-theme', savedTheme);
updateThemeButton(savedTheme);

themeToggle.addEventListener('click', () => {
    const currentTheme = html.getAttribute('data-bs-theme');
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    html.setAttribute('data-bs-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateThemeButton(newTheme);
});

// Advanced search toggle
advancedSearchToggle.addEventListener('click', () => {
    const isVisible = advancedSearch.style.display !== 'none';
    advancedSearch.style.display = isVisible ? 'none' : 'block';
    advancedSearchToggle.textContent = isVisible ? 'Advanced Search' : 'Hide Advanced Search';
});

function updateThemeButton(theme) {
    const icon = themeToggle.querySelector('i');
    const text = theme === 'light' ? 'Dark Mode' : 'Light Mode';
    icon.className = theme === 'light' ? 'bi bi-moon-stars' : 'bi bi-sun';
    themeToggle.innerHTML = `<i class="${icon.className}"></i> ${text}`;
}

// Search functionality
document.getElementById('searchForm').addEventListener('submit', function(e) {
    e.preventDefault();
    performSearch();
});

function performSearch() {
    const query = document.getElementById('searchQuery').value.toLowerCase().trim();
    const state = document.getElementById('stateSelect').value;
    const internationalOnly = document.getElementById('internationalOnly').checked;
    
    if (!query) {
        const resultsDiv = document.getElementById('results');
        resultsDiv.innerHTML = '<div class="alert alert-info">Please enter a search term</div>';
        return;
    }
    
    // Show loading state
    const resultsDiv = document.getElementById('results');
    resultsDiv.innerHTML = '<div class="loading">Searching for "' + query + '"...</div>';

    // Disable search button during search
    const searchButton = document.querySelector('button[type="submit"]');
    const originalButtonText = searchButton.innerHTML;
    searchButton.disabled = true;
    searchButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Searching...';

    // Perform the search
    fetch(`/search?q=${encodeURIComponent(query)}&state=${encodeURIComponent(state)}&international_only=${internationalOnly}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            displayResults(data, query, internationalOnly);
        })
        .catch(error => {
            console.error('Error:', error);
            resultsDiv.innerHTML = `
                <div class="alert alert-danger">
                    <h5>Search Error</h5>
                    <p>An error occurred while searching. Please try again.</p>
                    <small class="text-muted">If the problem persists, try refreshing the page.</small>
                </div>
            `;
        })
        .finally(() => {
            // Re-enable search button
            searchButton.disabled = false;
            searchButton.innerHTML = originalButtonText;
        });
}

function displayResults(results, query, internationalOnly) {
    const resultsDiv = document.getElementById('results');
    
    if (results.length === 0) {
        resultsDiv.innerHTML = `
            <div class="no-results">
                <p>No results found for "${query}"</p>
                <p class="text-muted">Try these suggestions:</p>
                <ul>
                    <li>Check your spelling</li>
                    <li>Try different keywords</li>
                    <li>Use the Advanced Search to filter by location</li>
                    ${internationalOnly ? '<li>Try searching without the "International Only" filter</li>' : ''}
                </ul>
            </div>
        `;
        return;
    }

    let html = '<div class="row">';
    results.forEach(result => {
        const orgName = result['Organization Name'] || 'Unknown Organization';
        const city = result.City || '';
        const state = result.State || '';
        const country = result.Country || '';
        const website = result.Website || '';
        const ein = result.EIN || '';

        html += `
            <div class="col-12 mb-4">
                <div class="card">
                    <div class="card-body">
                        <h5 class="card-title">${orgName}</h5>
                        <p class="card-text">
                            ${ein ? `<strong>EIN:</strong> ${ein}<br>` : ''}
                            ${city || state || country ? `<strong>Location:</strong> ${[city, state, country].filter(Boolean).join(', ')}<br>` : ''}
                            ${website ? `<strong>Website:</strong> <a href="${website}" target="_blank">${website}</a>` : ''}
                        </p>
                    </div>
                </div>
            </div>
        `;
    });
    html += '</div>';

    resultsDiv.innerHTML = html;
} 