# Integration checklist

- [ ] Copy `templates/index.html` into the bot repository.
- [ ] Keep exactly one route mapped to `/`; replace the old dashboard template rather than adding a duplicate route.
- [ ] Confirm `/api/status` returns JSON and contains aggregate metrics only.
- [ ] Confirm `/health` returns HTTP 200 when the service is healthy.
- [ ] Verify that the service binds to the host/port required by the deployment platform.
- [ ] Redeploy and open the root URL on desktop and mobile.
- [ ] Test the manual refresh button, theme switch, accent switch, and live progress cards.
- [ ] Confirm the public status API does not expose file names, object keys, user IDs, session strings, or credentials.

Example Flask root route (use only if a root route does not already exist):

```python
from flask import render_template

@app.get("/")
def dashboard():
    return render_template("index.html")
```

The dashboard is compatible with a same-origin `/api/status` endpoint. The field adapter in `index.html` can be adjusted to match the exact JSON structure returned by the current bot.
