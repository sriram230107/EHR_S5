import os
from datetime import datetime, date, timedelta
import random
from app import create_app, db
from app.models.role import Role
from app.models.department import Department
from app.models.user import User
from app.models.patient import Patient
from app.models.appointment import Appointment
from app.models.icd_code import ICDCode
from app.models.medical_visit import MedicalVisit, Prescription
from app.models.audit_log import AuditLog
from werkzeug.security import generate_password_hash

def seed_database():
    app = create_app()
    with app.app_context():
        print("Initializing database tables...")
        db.create_all()
        
        # 1. Seed Roles
        print("Seeding Roles...")
        roles_data = [
            ('Hospital System Administrator', 'System administration, config settings, audit logs, backup downloads.'),
            ('Administrator', 'Staff management, appointment scheduling, password resets, patient records viewing.'),
            ('Doctor', 'Patient search, medical visits creation, prescribing medications, ICD coding assist, file uploads.'),
            ('Receptionist', 'Patient registration, basic demographics view, appointment scheduling.')
        ]
        roles = {}
        for name, desc in roles_data:
            role = Role.query.filter_by(name=name).first()
            if not role:
                role = Role(name=name, description=desc)
                db.session.add(role)
            roles[name] = role
        db.session.commit()

        # 2. Seed Departments
        print("Seeding Departments...")
        depts_data = [
            ('General Medicine', 'Primary care, general health, routine checkups.'),
            ('Cardiology', 'Heart and cardiovascular system treatments.'),
            ('Pediatrics', 'Infant, child, and adolescent healthcare.'),
            ('Orthopedics', 'Musculoskeletal system, bone, and joint treatments.'),
            ('ENT', 'Ear, Nose, and Throat specialties.'),
            ('Dermatology', 'Skin, hair, and nail health.'),
            ('Neurology', 'Brain and nervous system disorders.'),
            ('Gynecology', 'Women reproductive health services.')
        ]
        departments = {}
        for name, desc in depts_data:
            dept = Department.query.filter_by(name=name).first()
            if not dept:
                dept = Department(name=name, description=desc)
                db.session.add(dept)
            departments[name] = dept
        db.session.commit()

        # Common password hash for test accounts
        hashed_password = generate_password_hash("Password123")

        # 3. Seed Users (1 Sys Admin, 2 Admins, 8 Doctors, 4 Receptionists)
        print("Seeding Staff Users...")
        
        # 3a. Hospital System Admin
        if not User.query.filter_by(username='sysadmin').first():
            sysadmin = User(
                username='sysadmin',
                email='sysadmin@hospital.com',
                password_hash=hashed_password,
                role_id=roles['Hospital System Administrator'].id,
                first_name='Albert',
                last_name='Einstein',
                phone='123-456-7890',
                is_active=True
            )
            db.session.add(sysadmin)

        # 3b. Administrators
        for i in range(1, 3):
            uname = f"admin{i}"
            if not User.query.filter_by(username=uname).first():
                admin = User(
                    username=uname,
                    email=f"admin{i}@hospital.com",
                    password_hash=hashed_password,
                    role_id=roles['Administrator'].id,
                    first_name=f"Admin{i}",
                    last_name="Staff",
                    phone=f"222-333-444{i}",
                    is_active=True
                )
                db.session.add(admin)

        # 3c. Doctors (8 Doctors, one for each department)
        docs_info = [
            ('drjohn', 'John', 'Smith', 'General Medicine', 'Cardiopulmonary health', 'LIC-GM-1001'),
            ('drjane', 'Jane', 'Doe', 'Cardiology', 'Cardiology and Heart Failure', 'LIC-CD-1002'),
            ('drrobert', 'Robert', 'Brown', 'Pediatrics', 'Neonatology and pediatrics', 'LIC-PD-1003'),
            ('dremily', 'Emily', 'Green', 'Orthopedics', 'Joint replacements and sports medicine', 'LIC-OP-1004'),
            ('drwilliam', 'William', 'White', 'ENT', 'Otology and rhinology', 'LIC-ENT-1005'),
            ('drsarah', 'Sarah', 'Black', 'Dermatology', 'Cosmetic and clinical dermatology', 'LIC-DM-1006'),
            ('drdavid', 'David', 'Grey', 'Neurology', 'Stroke and neuromuscular care', 'LIC-NL-1007'),
            ('drlisa', 'Lisa', 'Blue', 'Gynecology', 'Obstetrics and maternal healthcare', 'LIC-GY-1008'),
        ]
        doctors = []
        for username, fname, lname, dept_name, spec, license_num in docs_info:
            doc = User.query.filter_by(username=username).first()
            if not doc:
                doc = User(
                    username=username,
                    email=f"{username}@hospital.com",
                    password_hash=hashed_password,
                    role_id=roles['Doctor'].id,
                    first_name=fname,
                    last_name=lname,
                    phone=f"777-888-990{docs_info.index((username, fname, lname, dept_name, spec, license_num))}",
                    is_active=True,
                    specialization=spec,
                    license_number=license_num,
                    department_id=departments[dept_name].id
                )
                db.session.add(doc)
            doctors.append(doc)

        # 3d. Receptionists
        for i in range(1, 5):
            uname = f"reception{i}"
            if not User.query.filter_by(username=uname).first():
                rec = User(
                    username=uname,
                    email=f"reception{i}@hospital.com",
                    password_hash=hashed_password,
                    role_id=roles['Receptionist'].id,
                    first_name=f"Receptionist{i}",
                    last_name="Staff",
                    phone=f"555-666-777{i}",
                    is_active=True
                )
                db.session.add(rec)
        db.session.commit()

        # Retrieve the doctors to use in generating visits/appointments
        db_doctors = User.query.filter(User.role_id == roles['Doctor'].id).all()

        # 4. Seed ICD-10 Codes
        print("Seeding ICD-10 Dataset...")
        icd_data = [
            ('R50.9', 'Fever, unspecified', 'fever, temp, hot, pyrexia, high temperature'),
            ('I10', 'Essential (primary) hypertension', 'hypertension, high blood pressure, bp, hypertensive'),
            ('E11.9', 'Type 2 diabetes mellitus without complications', 'diabetes, sugar, glucose, dm2, type 2, diabetic'),
            ('J45.909', 'Unspecified asthma, uncomplicated', 'asthma, wheezing, breathing, shortness of breath, respiratory'),
            ('J06.9', 'Acute upper respiratory infection, unspecified', 'cold, cough, runny nose, uri, respiratory, sore throat'),
            ('K21.9', 'Gastro-esophageal reflux disease without esophagitis', 'gerd, acid, heartburn, stomach, acid reflux'),
            ('G43.909', 'Migraine, unspecified, not intractable', 'migraine, headache, head pain, aura'),
            ('J20.9', 'Acute bronchitis, unspecified', 'bronchitis, cough, chest congestion, bronchial'),
            ('U07.1', 'COVID-19', 'covid, corona, sars-cov-2, virus'),
            ('M25.561', 'Pain in right knee', 'knee pain, joint pain, leg pain, knee injury'),
            ('L20.9', 'Atopic dermatitis, unspecified', 'eczema, rash, itchy skin, skin allergy, dermatitis'),
            ('H10.9', 'Unspecified conjunctivitis', 'pink eye, conjunctivitis, eye redness, eye itching'),
            ('N39.0', 'Urinary tract infection, site not specified', 'uti, burning urination, bladder infection, urinary'),
            ('F41.9', 'Anxiety disorder, unspecified', 'anxiety, stress, panic, nervous'),
            ('E03.9', 'Hypothyroidism, unspecified', 'thyroid, low thyroid, fatigue, weight gain'),
            ('I25.10', 'Atherosclerotic heart disease of native coronary artery', 'heart disease, coronary, chest pain, ischemia'),
            ('M54.5', 'Low back pain', 'back pain, lumbago, spine pain, lumbar'),
            ('A09', 'Infectious gastroenteritis and colitis, unspecified', 'food poisoning, diarrhea, vomiting, stomach flu, stomach ache')
        ]
        icd_codes = {}
        for code, desc, keywords in icd_data:
            icd = ICDCode.query.filter_by(code=code).first()
            if not icd:
                icd = ICDCode(code=code, description=desc, keywords=keywords)
                db.session.add(icd)
            icd_codes[code] = icd
        db.session.commit()

        # 5. Seed 25 Patients
        print("Seeding 25 Patient Records...")
        patient_names = [
            ('James', 'Smith', 'Male', '1980-05-15', '555-0101', 'james.smith@gmail.com', '123 Oak St, Springfield'),
            ('Mary', 'Johnson', 'Female', '1992-09-22', '555-0102', 'mary.j@yahoo.com', '456 Pine St, Springfield'),
            ('John', 'Williams', 'Male', '1965-03-10', '555-0103', 'jwilliams@outlook.com', '789 Maple Rd, Springfield'),
            ('Patricia', 'Brown', 'Female', '1974-12-05', '555-0104', 'pat.brown@gmail.com', '101 Cedar Ln, Metro City'),
            ('Robert', 'Jones', 'Male', '1988-07-19', '555-0105', 'rjones@gmail.com', '202 Birch Rd, Metro City'),
            ('Jennifer', 'Miller', 'Female', '1995-02-28', '555-0106', 'jenn.miller@live.com', '303 Ash Way, Oakville'),
            ('Michael', 'Davis', 'Male', '1950-11-03', '555-0107', 'mdavis@yahoo.com', '404 Walnut Pl, Oakville'),
            ('Elizabeth', 'Garcia', 'Female', '1983-04-12', '555-0108', 'egarcia@gmail.com', '505 Cherry Ct, Greenwood'),
            ('William', 'Rodriguez', 'Male', '1990-08-30', '555-0109', 'wrodriguez@outlook.com', '606 Elm St, Greenwood'),
            ('Linda', 'Wilson', 'Female', '1958-06-14', '555-0110', 'lwilson@gmail.com', '707 Plum Ave, Springfield'),
            ('David', 'Martinez', 'Male', '1977-10-25', '555-0111', 'dmartinez@gmail.com', '808 Spruce St, Oakville'),
            ('Barbara', 'Anderson', 'Female', '1969-01-08', '555-0112', 'banderson@yahoo.com', '909 Fir Dr, Greenwood'),
            ('Richard', 'Taylor', 'Male', '1985-06-20', '555-0113', 'rtaylor@gmail.com', '111 Larch St, Metro City'),
            ('Susan', 'Thomas', 'Female', '1998-11-17', '555-0114', 'sthomas@outlook.com', '222 Yew St, Springfield'),
            ('Joseph', 'Hernandez', 'Male', '1945-05-02', '555-0115', 'jhernandez@gmail.com', '333 Willow Rd, Greenwood'),
            ('Jessica', 'Moore', 'Female', '1991-03-14', '555-0116', 'jmoore@yahoo.com', '444 Poplar Ct, Metro City'),
            ('Thomas', 'Martin', 'Male', '1971-08-01', '555-0117', 'tmartin@gmail.com', '555 Beech St, Oakville'),
            ('Sarah', 'Jackson', 'Female', '1986-10-12', '555-0118', 'sjackson@gmail.com', '666 Aspen Ln, Springfield'),
            ('Charles', 'Thompson', 'Male', '1955-04-09', '555-0119', 'cthompson@outlook.com', '777 Chestnut St, Greenwood'),
            ('Karen', 'White', 'Female', '1981-12-30', '555-0120', 'kwhite@gmail.com', '888 Alder Rd, Metro City'),
            ('Christopher', 'Lopez', 'Male', '1994-07-07', '555-0121', 'clopez@gmail.com', '999 Cypress Ave, Springfield'),
            ('Nancy', 'Lee', 'Female', '1962-09-05', '555-0122', 'nlee@yahoo.com', '124 Sycamore St, Greenwood'),
            ('Matthew', 'Gonzalez', 'Male', '1989-10-15', '555-0123', 'mgonzalez@outlook.com', '135 Linden Rd, Oakville'),
            ('Lisa', 'Harris', 'Female', '1975-01-26', '555-0124', 'lharris@gmail.com', '146 Hickory Ct, Metro City'),
            ('Betty', 'Clark', 'Female', '1949-03-18', '555-0125', 'bclark@gmail.com', '157 Magnolia Dr, Springfield')
        ]
        patients = []
        for idx, item in enumerate(patient_names):
            fname, lname, gender, dob_str, phone, email, addr = item
            dob_val = datetime.strptime(dob_str, '%Y-%m-%d').date()
            
            # Generate sequential PAT-2026-0001 format
            mrn = f"PAT-2026-{str(idx + 1).zfill(4)}"
            
            # We soft delete the last 2 patients for testing purposes
            is_active = True if idx < 23 else False
            
            pat = Patient.query.filter_by(patient_number=mrn).first()
            if not pat:
                pat = Patient(
                    patient_number=mrn,
                    first_name=fname,
                    last_name=lname,
                    dob=dob_val,
                    gender=gender,
                    phone=phone,
                    email=email,
                    address=addr,
                    emergency_contact_name=f"Contact of {fname}",
                    emergency_contact_phone="555-0000",
                    is_active=is_active
                )
                db.session.add(pat)
            patients.append(pat)
        db.session.commit()

        # Re-fetch patients to link IDs
        db_patients = Patient.query.all()

        # 6. Seed Sample Appointments
        print("Seeding Appointments...")
        # Add a few scheduled, completed, and cancelled appointments
        appointment_reasons = [
            "Routine health checkup",
            "Follow-up visit for hypertension",
            "Severe dry cough and sore throat",
            "Knee joint pain during climbing stairs",
            "Routine skin screening",
            "Stomach upset and vomiting since last night",
            "Anxiety attacks and chronic sleeplessness"
        ]
        
        statuses = ["Scheduled", "Completed", "Cancelled", "No-Show"]
        
        for idx in range(30):
            patient = random.choice(db_patients)
            doctor = random.choice(db_doctors)
            reason = random.choice(appointment_reasons)
            status = random.choice(statuses)
            
            # Dates range from 15 days ago to 15 days in the future
            days_delta = random.randint(-15, 15)
            appt_time = datetime.now() + timedelta(days=days_delta, hours=random.randint(-4, 4))
            
            # Completed appts are in the past, Scheduled are usually in the future
            if days_delta < 0 and status == "Scheduled":
                status = "Completed"
            elif days_delta > 0 and status == "Completed":
                status = "Scheduled"
                
            appt = Appointment(
                patient_id=patient.id,
                doctor_id=doctor.id,
                appointment_date=appt_time,
                status=status,
                reason=reason
            )
            db.session.add(appt)
        db.session.commit()

        # 7. Seed Medical Visits and Prescriptions
        print("Seeding Medical Visit Chronological Timelines...")
        # Seed several medical visits in the past
        visit_symptoms_list = [
            ("Persistent dry cough, mild fever, runny nose.", "J06.9", [("Amoxicillin", "500mg", "Three times daily", "7 days", "Take after food"), ("Paracetamol", "650mg", "As needed for fever", "3 days", "Max 4 tablets daily")]),
            ("Elevated blood pressure readings, occasional throbbing headaches.", "I10", [("Amlodipine", "5mg", "Once daily in morning", "30 days", "Monitor blood pressure regularly")]),
            ("Increased thirst, frequent urination, fatigue.", "E11.9", [("Metformin", "500mg", "Twice daily with meals", "90 days", "Check blood glucose daily")]),
            ("Shortness of breath, wheezing on exertion.", "J45.909", [("Albuterol Inhaler", "90mcg", "2 puffs every 4-6 hours as needed", "30 days", "Inhale through spacer")]),
            ("Sharp pain in the right knee joint after playing tennis.", "M25.561", [("Ibuprofen", "400mg", "Twice daily as needed", "5 days", "Take with food")]),
            ("Burning sensation during urination, frequent bladder urges.", "N39.0", [("Nitrofurantoin", "100mg", "Twice daily", "5 days", "Complete the full course")]),
            ("Severe headache with nausea, light sensitivity.", "G43.909", [("Sumatriptan", "500mg", "Once at onset of headache", "3 days", "Rest in dark room")]),
            ("Chronic anxiety, palpitations, insomnia.", "F41.9", [("Sertraline", "500mg", "Once daily in the morning", "30 days", "Avoid sudden withdrawal")])
        ]

        # Let's seed at least 15 visits across the 25 patients
        for idx in range(18):
            patient = db_patients[idx % len(db_patients)]
            # Match doctor to specialization if possible, otherwise pick random doctor
            doctor = db_doctors[idx % len(db_doctors)]
            symptoms, code_str, meds = random.choice(visit_symptoms_list)
            
            # Historical date: 1 to 60 days ago
            visit_date = datetime.now() - timedelta(days=random.randint(1, 60), hours=random.randint(1, 10))
            
            # Vitals
            bp = f"{random.randint(110, 145)}/{random.randint(70, 95)}"
            pulse = random.randint(65, 95)
            temp = round(random.uniform(97.5, 101.5), 1)
            weight = round(random.uniform(50.0, 95.0), 1)
            
            icd_code = icd_codes.get(code_str)
            icd_code_id = icd_code.id if icd_code else None
            diag_desc = icd_code.description if icd_code else "Unspecified Diagnosis"
            
            visit = MedicalVisit(
                patient_id=patient.id,
                doctor_id=doctor.id,
                visit_date=visit_date,
                symptoms=symptoms,
                vitals_bp=bp,
                vitals_pulse=pulse,
                vitals_temp=temp,
                vitals_weight=weight,
                icd_code_id=icd_code_id,
                diagnosis_notes=f"Patient diagnosed with: {diag_desc}.",
                clinical_notes="Patient is advised to take rest, monitor symptoms, and follow prescription instructions. Follow-up suggested if condition worsens.",
                follow_up_date=(visit_date + timedelta(days=14)).date() if random.choice([True, False]) else None
            )
            db.session.add(visit)
            db.session.flush() # Flushes to get the visit.id
            
            for m_name, dose, freq, dur, inst in meds:
                pres = Prescription(
                    visit_id=visit.id,
                    medication_name=m_name,
                    dosage=dose,
                    frequency=freq,
                    duration=dur,
                    instructions=inst
                )
                db.session.add(pres)
        db.session.commit()

        # 8. Seed Audit Logs
        print("Seeding Audit logs...")
        sysadmin_user = User.query.filter_by(username='sysadmin').first()
        admin_user = User.query.filter_by(username='admin1').first()
        doctor_user = User.query.filter_by(username='drjohn').first()
        receptionist_user = User.query.filter_by(username='reception1').first()

        audit_events = [
            (sysadmin_user.id, "Login Success", "System administrator logged in successfully from 192.168.1.50"),
            (sysadmin_user.id, "User Create", "Created Administrator user: admin1"),
            (admin_user.id, "Login Success", "Administrator logged in from 192.168.1.55"),
            (admin_user.id, "User Create", "Created Doctor user: drjohn"),
            (admin_user.id, "User Create", "Created Receptionist user: reception1"),
            (receptionist_user.id, "Login Success", "Receptionist logged in from 192.168.1.60"),
            (receptionist_user.id, "Record Create", "Registered new patient record: PAT-2026-0001 (James Smith)"),
            (receptionist_user.id, "Record Create", "Registered new patient record: PAT-2026-0002 (Mary Johnson)"),
            (doctor_user.id, "Login Success", "Doctor drjohn logged in from 192.168.1.62"),
            (doctor_user.id, "Record Create", "Created new Medical Visit for Patient PAT-2026-0001 (James Smith)"),
            (None, "Login Failed", "Failed login attempt for username 'unauthorized_user' from 192.168.1.99")
        ]

        for u_id, action, details in audit_events:
            log = AuditLog(
                user_id=u_id,
                username_attempted=None if u_id else "unauthorized_user",
                action=action,
                ip_address="127.0.0.1",
                timestamp=datetime.now() - timedelta(minutes=random.randint(10, 500)),
                details=details
            )
            db.session.add(log)
        db.session.commit()

        print("Database initialized and seeded successfully!")

if __name__ == '__main__':
    seed_database()
