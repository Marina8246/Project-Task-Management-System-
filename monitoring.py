import logging
from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from app.dependencies import require_admin, redis_client

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
def health_check():
    redis_status = "connected"
    try:
        if redis_client is None:
            redis_status = "unavailable"
        else:
            redis_client.ping()
    except Exception:
        redis_status = "unavailable"

    logger.info(f"Health check called – Redis: {redis_status}")
    return {"server": "running", "redis": redis_status}


@router.get("/stats")
def cache_stats(payload: dict = Depends(require_admin)):
    cache_keys = 0
    redis_status = "connected"
    try:
        if redis_client is None:
            redis_status = "unavailable"
        else:
            cache_keys = len(redis_client.keys("*"))
    except Exception:
        redis_status = "unavailable"

    logger.info(f"Admin '{payload.get('sub')}' fetched cache stats")
    return {"redis": redis_status, "cached_keys": cache_keys}


@router.get("/metrics")
def get_metrics():
    from app.main import request_counts, response_times, error_counts

    avg_time = 0
    if response_times:
        avg_time = round(
            sum(r["ms"] for r in response_times) / len(response_times), 2
        )

    return {
        "total_requests": sum(request_counts.values()),
        "requests_by_endpoint": dict(request_counts),
        "average_response_time_ms": avg_time,
        "recent_response_times": response_times[-10:],
        "total_errors": sum(error_counts.values()),
        "errors_by_endpoint": dict(error_counts),
    }


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Monitoring Dashboard</title>
        <style>
            body { font-family: Arial, sans-serif; background: #1e1e2e; color: #cdd6f4; margin: 0; padding: 20px; }
            h1 { color: #89b4fa; }
            h3 { color: #89b4fa; }
            .card { background: #313244; border-radius: 10px; padding: 20px; margin: 15px 0; }
            .card h2 { color: #cba6f7; margin-top: 0; }
            .status { font-size: 1.2em; font-weight: bold; }
            .ok { color: #a6e3a1; }
            .error { color: #f38ba8; }
            button { background: #89b4fa; color: #1e1e2e; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; font-size: 1em; margin-top: 10px; }
            button:hover { background: #cba6f7; }
            input { padding: 8px; border-radius: 5px; border: none; margin-right: 10px; width: 300px; }
            table { width: 100%; border-collapse: collapse; margin-top: 10px; }
            th, td { padding: 10px; text-align: left; border-bottom: 1px solid #45475a; }
            th { color: #89b4fa; }
            .metric { font-size: 1.1em; margin: 8px 0; }
            .metric span { color: #a6e3a1; font-weight: bold; }
        </style>
    </head>
    <body>
        <h1>🖥️ Monitoring Dashboard</h1>

        <!-- System Health -->
        <div class="card">
            <h2>🟢 System Health</h2>
            <p>Server: <span class="status ok" id="server-status">Loading...</span></p>
            <p>Redis: <span class="status" id="redis-status">Loading...</span></p>
            <button onclick="loadHealth()">Refresh</button>
        </div>

        <!-- API Metrics -->
        <div class="card">
            <h2>📈 API Metrics</h2>
            <button onclick="loadMetrics()">Load Metrics</button>
            <div class="metric">Total Requests: <span id="total-req">-</span></div>
            <div class="metric">Avg Response Time: <span id="avg-time">-</span> ms</div>
            <div class="metric">Total Errors: <span id="total-errors" style="color:#f38ba8">-</span></div>
            <h3>Requests by Endpoint:</h3>
            <div id="endpoints-table"></div>
            <h3>Recent Response Times:</h3>
            <div id="recent-times"></div>
        </div>

        <!-- Cache Stats -->
        <div class="card">
            <h2>📊 Cache Stats (Admin Only)</h2>
            <input type="text" id="token-input" placeholder="Paste your Bearer token here..." />
            <button onclick="loadStats()">Load Stats</button>
            <div class="metric">Redis Status: <span id="stats-redis">-</span></div>
            <div class="metric">Cached Keys: <span id="stats-keys">-</span></div>
        </div>

        <!-- API Endpoints -->
        <div class="card">
            <h2>📋 API Endpoints</h2>
            <table>
                <tr><th>Method</th><th>Endpoint</th><th>Description</th><th>Role</th></tr>
                <tr><td>POST</td><td>/auth/login</td><td>Login</td><td>Public</td></tr>
                <tr><td>POST</td><td>/auth/register-with-role</td><td>Register</td><td>Admin</td></tr>
                <tr><td>GET</td><td>/users/</td><td>All users</td><td>Admin</td></tr>
                <tr><td>GET</td><td>/users/me</td><td>My profile</td><td>All</td></tr>
                <tr><td>GET</td><td>/projects/</td><td>All projects</td><td>All</td></tr>
                <tr><td>POST</td><td>/projects/</td><td>Create project</td><td>Manager+</td></tr>
                <tr><td>GET</td><td>/tasks/</td><td>All tasks</td><td>Manager+</td></tr>
                <tr><td>POST</td><td>/tasks/</td><td>Create task</td><td>Manager+</td></tr>
                <tr><td>PUT</td><td>/tasks/{id}</td><td>Update task</td><td>Employee+</td></tr>
                <tr><td>DELETE</td><td>/tasks/{id}</td><td>Delete task</td><td>Admin</td></tr>
                <tr><td>GET</td><td>/monitoring/health</td><td>Health check</td><td>Public</td></tr>
                <tr><td>GET</td><td>/monitoring/metrics</td><td>API Metrics</td><td>Public</td></tr>
                <tr><td>GET</td><td>/monitoring/stats</td><td>Cache stats</td><td>Admin</td></tr>
                <tr><td>GET</td><td>/monitoring/dashboard</td><td>Dashboard</td><td>Public</td></tr>
            </table>
        </div>

        <script>
            async function loadHealth() {
                const res = await fetch('/monitoring/health');
                const data = await res.json();
                document.getElementById('server-status').textContent = data.server;
                const redisEl = document.getElementById('redis-status');
                redisEl.textContent = data.redis;
                redisEl.className = 'status ' + (data.redis === 'connected' ? 'ok' : 'error');
            }

            async function loadMetrics() {
                const res = await fetch('/monitoring/metrics');
                const data = await res.json();

                document.getElementById('total-req').textContent = data.total_requests;
                document.getElementById('avg-time').textContent = data.average_response_time_ms;
                document.getElementById('total-errors').textContent = data.total_errors;

                // Requests by endpoint table
                let html = '<table><tr><th>Endpoint</th><th>Requests</th><th>Errors</th></tr>';
                for (const [ep, count] of Object.entries(data.requests_by_endpoint)) {
                    const errors = data.errors_by_endpoint[ep] || 0;
                    html += `<tr><td>${ep}</td><td>${count}</td><td style="color:${errors > 0 ? '#f38ba8' : '#a6e3a1'}">${errors}</td></tr>`;
                }
                html += '</table>';
                document.getElementById('endpoints-table').innerHTML = html;

                // Recent response times
                let timesHtml = '<table><tr><th>Endpoint</th><th>Response Time (ms)</th></tr>';
                for (const item of data.recent_response_times) {
                    timesHtml += `<tr><td>${item.endpoint}</td><td>${item.ms}</td></tr>`;
                }
                timesHtml += '</table>';
                document.getElementById('recent-times').innerHTML = timesHtml;
            }

            async function loadStats() {
                const token = document.getElementById('token-input').value;
                const res = await fetch('/monitoring/stats', {
                    headers: { 'Authorization': 'Bearer ' + token }
                });
                if (res.ok) {
                    const data = await res.json();
                    document.getElementById('stats-redis').textContent = data.redis;
                    document.getElementById('stats-keys').textContent = data.cached_keys;
                } else {
                    document.getElementById('stats-redis').textContent = 'Unauthorized';
                    document.getElementById('stats-keys').textContent = '-';
                }
            }

            loadHealth();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)