// Robust API Client for AI-Based Student Productivity and Study Planner

/**
 * Automatically resolves the backend API base URL:
 * - Production: Always returns '' so all requests use clean relative URLs (e.g. '/api/planner/generate').
 * - Local Development: When running from a separate static server (e.g. VS Code Live Server on port 5500)
 *   or local file:// protocol, targets the local Flask backend on port 5000.
 */
function resolveApiBase() {
    if (typeof window !== 'undefined' && window.location) {
        const protocol = window.location.protocol;
        const hostname = window.location.hostname;
        const port = window.location.port;

        // When opened directly via local file:// protocol
        if (protocol === 'file:') {
            return 'http://127.0.0.1:5000';
        }

        // Only use cross-port fallback if explicitly running on local loopback with non-Flask dev server port (e.g. 5500)
        const isLocalLoopback = (hostname === 'localhost' || hostname === '127.0.0.1');
        if (isLocalLoopback && port && port !== '5000') {
            return `http://${hostname}:5000`;
        }
    }
    // In production (Render, Railway, Heroku, VPS, or Flask-served), use relative paths
    return '';
}

let API_BASE = resolveApiBase();

/**
 * Safely executes a fetch request, verifying HTTP status, content-type,
 * and ensuring that empty bodies, HTML error pages, or wrong-port requests
 * provide crystal-clear diagnostic error messages.
 */
async function safeFetchJson(url, options = {}) {
    let res;
    let attemptedUrl = url;
    try {
        res = await fetch(attemptedUrl, options);
    } catch (networkError) {
        // If fetch failed on a local loopback server, attempt alternate loopback (127.0.0.1 <-> localhost)
        let retryUrl = null;
        if (attemptedUrl.includes('//localhost:5000')) {
            retryUrl = attemptedUrl.replace('//localhost:5000', '//127.0.0.1:5000');
        } else if (attemptedUrl.includes('//127.0.0.1:5000')) {
            retryUrl = attemptedUrl.replace('//127.0.0.1:5000', '//localhost:5000');
        }

        if (retryUrl) {
            try {
                res = await fetch(retryUrl, options);
                API_BASE = retryUrl.split('/api/')[0];
                attemptedUrl = retryUrl;
            } catch (retryErr) {
                throw new Error(
                    `Unable to connect to backend server at ${attemptedUrl} (${networkError.message}). ` +
                    `Please check network connection and ensure backend service is running.`
                );
            }
        } else {
            const isLocal = typeof window !== 'undefined' && window.location && 
                (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');
            const helpHint = isLocal
                ? 'Please ensure your Flask backend is running (python app.py) on port 5000.'
                : 'Please check your internet connection and ensure the backend service is running.';
            throw new Error(`Unable to connect to backend server at ${attemptedUrl} (${networkError.message}). ${helpHint}`);
        }
    }

    // Read the response as text first to handle empty or HTML bodies safely
    const rawText = await res.text();
    let data = null;

    if (rawText && rawText.trim().length > 0) {
        try {
            data = JSON.parse(rawText);
        } catch (parseErr) {
            console.warn(`Response from ${url} is not valid JSON:`, rawText.substring(0, 200));
        }
    }

    // Handle HTTP error statuses (4xx, 5xx)
    if (!res.ok) {
        if (data && data.error) {
            throw new Error(data.error);
        }
        if (data && data.message) {
            throw new Error(data.message);
        }
        if (res.status === 405) {
            const hostPort = (typeof window !== 'undefined' && window.location && window.location.port) ? window.location.port : '';
            const isLocalLoopback = (typeof window !== 'undefined' && window.location && 
                (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'));
            if (isLocalLoopback && hostPort && hostPort !== '5000') {
                throw new Error(
                    `HTTP 405 Method Not Allowed: The request was sent to port ${hostPort} (static server) instead of Flask on port 5000. ` +
                    `Please open the web application at http://localhost:5000 in your browser.`
                );
            }
            throw new Error(`HTTP 405 Method Not Allowed for ${url}. The endpoint expects POST with JSON.`);
        }
        if (rawText && rawText.trim().length > 0) {
            // Strip HTML tags if Flask generated a standard HTML error page
            const cleanText = rawText.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
            throw new Error(`Server error (${res.status}): ${cleanText.substring(0, 180)}`);
        }
        throw new Error(`Server returned an empty error response (HTTP ${res.status} ${res.statusText || 'Error'}).`);
    }

    // On success (2xx): return parsed JSON data
    if (data !== null) {
        return data;
    }

    // If HTTP 200/204 with empty response body
    if (res.status === 204 || !rawText || rawText.trim().length === 0) {
        return {};
    }

    throw new Error('Server returned an unexpected response format. Please try again.');
}

const API = {
    // System Status
    getStatus: async () => {
        return safeFetchJson(`${API_BASE}/api/status`);
    },

    // Student Profile
    getProfile: async () => {
        return safeFetchJson(`${API_BASE}/api/profile`);
    },

    updateProfile: async (profileData) => {
        return safeFetchJson(`${API_BASE}/api/profile`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(profileData)
        });
    },

    // Tasks
    getTasks: async (filters = {}) => {
        const params = new URLSearchParams();
        if (filters.status) params.append('status', filters.status);
        if (filters.subject) params.append('subject', filters.subject);
        if (filters.search) params.append('search', filters.search);
        
        const url = `${API_BASE}/api/tasks${params.toString() ? '?' + params.toString() : ''}`;
        return safeFetchJson(url);
    },

    createTask: async (taskData) => {
        return safeFetchJson(`${API_BASE}/api/tasks`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(taskData)
        });
    },

    updateTask: async (taskId, taskData) => {
        return safeFetchJson(`${API_BASE}/api/tasks/${taskId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(taskData)
        });
    },

    toggleTask: async (taskId) => {
        return safeFetchJson(`${API_BASE}/api/tasks/${taskId}/toggle`, {
            method: 'PATCH'
        });
    },

    deleteTask: async (taskId) => {
        return safeFetchJson(`${API_BASE}/api/tasks/${taskId}`, {
            method: 'DELETE'
        });
    },

    // Progress & Analytics
    getAnalytics: async () => {
        return safeFetchJson(`${API_BASE}/api/analytics/progress`);
    },

    // Study Planner
    generatePlan: async (planPayload) => {
        return safeFetchJson(`${API_BASE}/api/planner/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(planPayload)
        });
    },

    getActivePlan: async () => {
        return safeFetchJson(`${API_BASE}/api/planner/active`);
    },

    getPlanHistory: async () => {
        return safeFetchJson(`${API_BASE}/api/planner/history`);
    },

    // Motivational Quotes
    getQuote: async () => {
        return safeFetchJson(`${API_BASE}/api/quote`);
    },

    // Focus Music
    getMusicSuggest: async (mood, language, ptype) => {
        return safeFetchJson(`${API_BASE}/api/music-suggest`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mood, language, ptype })
        });
    },

    // AI Study Assistant
    askAssistant: async (prompt, lengthHint = 1.0) => {
        return safeFetchJson(`${API_BASE}/api/assistant`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt, length_hint: lengthHint })
        });
    }
};
