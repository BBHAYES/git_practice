Issue: Fix login 500 error

Description:
The login endpoint is returning a 500 Internal Server Error when valid credentials are submitted.

Repro steps:
1. Open the login page.
2. Enter a valid username and password.
3. Click "Login".
4. Observe a 500 error response instead of successful authentication.

Assignee: Copilot
