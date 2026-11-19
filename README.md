# Student Leave Management System — LeaveFlow

A beginner-friendly academic project built with Python, Flask, SQLite, HTML, CSS, and JavaScript.

## Features
- Role-based login for students, faculty, and administrators
- Student leave application and history
- Date and reason validation
- Prevents overlapping pending/approved requests for the same student
- Faculty approval/rejection with optional comments
- Students can cancel pending requests
- Admin can create accounts and review all requests
- Dashboard statistics and doughnut charts

## Windows setup
1. Install Python 3.10 or newer.
2. Open Command Prompt in this folder.
3. Create a virtual environment:
   `python -m venv .venv`
4. Activate it:
   `.venv\Scripts\activate`
5. Install dependencies:
   `python -m pip install -r requirements.txt`
6. Start the app:
   `python app.py`
7. Open `http://127.0.0.1:5000` in your browser.

The SQLite database is created automatically on the first run.

## Demo accounts
- Student: `student@example.com` / `Student123!`
- Faculty: `faculty@example.com` / `Faculty123!`
- Admin: `admin@example.com` / `Admin123!`

Use the demo accounts for local evaluation only. Change the secret key and demo passwords before any real deployment. This is an academic prototype, not a production-ready campus system.

## Notes
- The dashboard chart loads Chart.js from a CDN, so charts require an internet connection.
- Run only on your own computer for the academic demo.
- To reset demo data, stop the app and delete `leave_management.db`; it will be recreated on the next run.
