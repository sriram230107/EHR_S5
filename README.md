# Cloud-Based Electronic Health Record (EHR) Clinical Portal with Automated ICD Coding Assist

A secure, professional, and responsive Electronic Health Record (EHR) web application designed using Flask, Bootstrap 5, and SQLAlchemy. This college-level mini project provides standard clinical administration tools, role-based access control (RBAC), sequential patient MRN generation, structured document uploads, audit log tracking, and an interactive local keyword-based ICD-10 coding assistant.

---

## 🚀 Key Features

*   **Role-Based Access Control (RBAC)**: Supports 4 distinct hospital staff roles:
    *   *Hospital System Administrator*: System configurations, staff user creation, paginated security audit log searching, and direct database backup downloads.
    *   *Administrator*: Manage doctors & receptionists, schedule appointments, search patient details.
    *   *Doctor*: Clinical work, search patients, view visit history vertical timelines, create medical visits (capturing chief complaints, vitals, diagnosis/treatment notes), write prescriptions, upload patient diagnostic files, and check follow-up reminders.
    *   *Receptionist*: Patient registration, demographic profile search, and booking appointments.
*   **Sequential MRN Generation**: Automatically formats patient IDs sequentially in the format `PAT-YYYY-XXXX` based on the year of registration.
*   **Medical History Vertical Timeline**: Renders clinical visits as a beautiful chronological vertical timeline displaying symptoms, vitals, diagnoses, and prescriptions (doctors only).
*   **Automated ICD Coding Assist**: Autocompletes diagnostic codes in real-time as doctors type keyword queries against a seeded local ICD-10 dataset (e.g. Hypertension -> I10).
*   **Secure Document Vault**: Enables doctors to upload lab reports, scan reports, X-rays, and discharge summaries up to 10MB in structured directories (`uploads/patients/PAT-YYYY-XXXX/`).
*   **Ledger Auditing**: Automatically records actions (success/failed logins, account edits, document uploads, backup downloads) in the database audit log.
*   **Database Backup**: Direct download link of the live SQLite database binary file.

---

## 🛠️ Technology Stack

*   **Backend**: Python 3, Flask, Flask-Login (session management), Flask-SQLAlchemy (ORM), Werkzeug (password hashing)
*   **Database**: SQLite
*   **Frontend**: HTML5, Vanilla JavaScript, Bootstrap 5, Bootstrap Icons, Google Fonts (Inter)
*   **Deployment**: Render-ready configurations

---

## 📁 Project Directory Structure

```text
d:/Dummy_S5/Dummy_S5/
├── app/
│   ├── __init__.py           # Application factory & error handlers
│   ├── config.py             # Global configurations
│   ├── utils.py              # Audit logging helper
│   ├── models/               # SQLAlchemy Models
│   │   ├── __init__.py
│   │   ├── role.py
│   │   ├── department.py
│   │   ├── user.py
│   │   ├── patient.py
│   │   ├── appointment.py
│   │   ├── icd_code.py
│   │   ├── medical_visit.py  # MedicalVisit and Prescription
│   │   ├── document.py
│   │   └── audit_log.py
│   ├── routes/               # Modular Blueprints
│   │   ├── __init__.py
│   │   ├── auth.py           # Login/Logout & RBAC redirects
│   │   ├── decorators.py     # @role_required decorator
│   │   ├── admin.py          # Admin/SysAdmin controls & reports
│   │   ├── doctor.py         # Clinical visits & ICD searches
│   │   ├── receptionist.py   # Registration redirects
│   │   └── main.py           # Shared Patient/Appointment directories
│   ├── static/
│   │   └── css/
│   │       └── main.css      # Custom stylesheet (Sidebar, cards, timelines)
│   └── templates/            # Jinja2 Layouts
│       ├── base.html         # Base navbar & sidebar wrapper
│       ├── auth/             # login.html
│       ├── dashboard/        # sysadmin, admin, doctor, receptionist dashboards
│       ├── patient/          # search, register, edit, profile templates
│       ├── visit/            # create.html (visit encounter form)
│       ├── reports/          # dashboard.html, print.html
│       ├── appointments/     # list.html (scheduler list)
│       └── errors/           # 403, 404, 500 error cards
├── uploads/                  # Patient document files (ignored by Git)
├── instance/                 # Live sqlite db folder (ignored by Git)
├── requirements.txt          # PIP dependencies
├── run.py                    # Entrypoint server script
├── seed.py                   # DB creation & realistic seeding script
├── .gitignore
└── README.md
```

---

## 💻 Setup & Installation Instructions

Follow these steps to set up and run the portal locally:

### 1. Clone or Extract the Project
Ensure you are inside the root project directory:
```bash
cd D:/Dummy_S5/Dummy_S5
```

### 2. Set Up a Virtual Environment (Optional but Recommended)
```bash
python -m venv venv
venv\Scripts\activate      # On Windows
source venv/bin/activate  # On macOS/Linux
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Initialize and Seed the Database
Run the seeding script. This creates all schema tables and populates them with realistic test accounts, patients, and initial medical visits:
```bash
python seed.py
```

### 5. Launch the Portal Server
```bash
python run.py
```
Open your browser and navigate to `http://127.0.0.1:5000` to access the application.

---

## 🔒 Test Accounts & Roles

All accounts are pre-seeded with the password: `Password123`

| Role | Username | Department / Specialization | Capabilities |
|---|---|---|---|
| **Hospital System Admin** | `sysadmin` | N/A | Full user management, logs, database backup. |
| **Administrator** | `admin1`, `admin2` | N/A | Staff management, appointments, patient directories. |
| **Doctor (Gen Medicine)** | `drjohn` | General Medicine | Consultations, Prescriptions, ICD-10 search, file uploads. |
| **Doctor (Cardiology)** | `drjane` | Cardiology | Consultations, Prescriptions, ICD-10 search, file uploads. |
| **Doctor (Pediatrics)** | `drrobert` | Pediatrics | Consultations, Prescriptions, ICD-10 search, file uploads. |
| **Receptionist** | `reception1` | N/A | Register patients, demographics search, book appointments. |

---

## 🌐 Render Deployment Steps

To host the application on **Render**:

1.  **Repository Setup**: Push your repository code to GitHub.
2.  **Render App Creation**: Create a new **Web Service** on Render connected to your repository.
3.  **App Configurations**:
    *   **Runtime**: `Python`
    *   **Build Command**: `pip install -r requirements.txt && python seed.py`
    *   **Start Command**: `gunicorn run:app`
4.  **Environment Variables**:
    *   `SECRET_KEY` : (A secure random string)
    *   `DATABASE_URL` : (Leave blank to use default SQLite database)
