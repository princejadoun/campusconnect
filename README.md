# CampusConnect
> **Project Title:** Design and Development of a College Event Management System with QR-Based Attendance Tracking and Automated Certificate Generation Using Python  
> **Course:** Advanced Python for AI | **Team Size:** 5 | **AI Tooling:** Google Antigravity & Gemini

## Project Overview
CampusConnect is a full-stack Python web application that centralizes college event discovery, online student registration, QR-code entry pass verification with duplicate-scan prevention, automated PDF certificate generation, and live administrative attendance analytics.

## Technology Stack
| Component | Technology |
| :--- | :--- |
| **Backend** | Python 3, Flask (Blueprints) |
| **Database & ORM** | SQLite, Flask-SQLAlchemy |
| **Authentication** | Flask-Login, Custom Role Decorators |
| **Frontend** | HTML5, CSS3, JavaScript, Bootstrap 5 |
| **QR Codes** | Python `qrcode` + `html5-qrcode` (Web Scanner) |
| **PDF Certificates** | `ReportLab` |
| **Analytics** | `Chart.js` |
| **Testing & AI Workflow** | `pytest`, Google Antigravity |

## Team Architecture & GitHub Ownership
| Member | GitHub Handle | Owned Modules | Responsibilities |
| :--- | :--- | :--- | :--- |
| Member 1 (Team Head) | `@princejadoun` | `app.py`, `models.py`, `decorators.py`, `routes/auth.py` | Core architecture, SQLAlchemy ORM, authentication & final integration |
| Member 2 | `@dhruvtanwar` | `routes/events.py`, `templates/events/` | Event creation, seat limits, deadlines & student registration |
| Member 3 | `@boyasaicharanboyasaicharan8-svg` | `routes/attendance.py`, `utils/qr_helper.py` | QR pass generation, webcam scanner & duplicate-entry prevention |
| Member 4 | `@jaswanthreddypalle6-spec` | `routes/certificates.py`, `utils/pdf_helper.py` | Attendance eligibility checks & dynamic ReportLab PDF certificates |
| Member 5 | `@eswar-kumar1786` | `routes/admin.py`, `templates/admin/`, `tests/` | Admin dashboard, Chart.js analytics & automated Pytest suite |

## How to Run Locally
1. Clone the repository:
   ```bash
   git clone <your-repo-url>
   cd campusconnect