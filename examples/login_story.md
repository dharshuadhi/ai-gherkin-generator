# User login

As a registered user, I want to log in with my email and password,
so that I can access my account securely.

Acceptance Criteria:
- When the user submits valid credentials, then they are taken to the dashboard
- When the user submits an invalid password 3 times, then the account is temporarily locked
- An error is shown when the email format is invalid
- Sessions expire after 30 minutes of inactivity
