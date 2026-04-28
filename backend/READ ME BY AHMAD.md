# Read Me by Ahmad

## 1. Database Tables (SQLAlchemy Models)

We have implemented two primary tables in our SQLite database, designed with strict data integrity rules to prevent redundancy.

### A. Students Table

This table manages student profiles and academic data:

- **university_id** (Primary Key): The unique student ID from JUST, ensuring no two students share the same record.
- **email** (Unique Index): The university email address, indexed for fast lookups and marked as unique.
- **first_name & last_name**: Standard string fields for the student's name.
- **password**: Stores the student's hashed credentials.
- **phone_number**: Contact information for the student.
- **academic_standing**: Reflects the student's current academic status (e.g., Excellent, Good).

### B. Faculty Table (cs_faculty_info)

This table stores details about the Computer Science department faculty:

- **email** (Primary Key): The official university email, used as the unique identifier to prevent duplicate faculty entries.
- **name**: The full name and title of the faculty member.
- **office_location**: The physical office code (e.g., A1L3).
- **office_hours**: Scheduled availability for student advising.

---

## 2. Automated Data Syncing (Seeding Logic)

We utilize a **Smart Seeding** approach in `main.py` using the `db.merge()` method. This allows the team to add or update records directly from the code without ever needing to delete the database file (`test.db`).

### How to Add a New Student

Navigate to the `seed()` function in `backend/main.py` and add a new entry to the `students_data` list:

```python
Student(
    university_id="202110500",
    email="example@just.edu.jo",
    first_name="John",
    last_name="Doe",
    password="securepassword",
    phone_number="0791234567",
    academic_standing="Good"
)
```

### How to Add a New Faculty Member

Navigate to the `faculty_data` list in `backend/main.py` and add the new faculty object:

```python
CsFacultyInfo(
    name="Dr. Ahmad Khaldoon",
    email="ahmad@just.edu.jo",
    office_location="PH2 L0",
    office_hours="Sun-Tue 12:00-14:00"
)
```

---

## 3. Key Technical Features

- **Upsert Capability**: By using `db.merge()`, the system checks if the Primary Key exists. If it does, it **Updates** the info; if not, it **Inserts** a new record.
- **Prevention of Duplication**: The database engine itself enforces the Primary Key and Unique constraints, rejecting any attempt to create duplicate IDs or Emails.
- **Auto-Creation**: The system runs `Base.metadata.create_all(bind=engine)` on startup, ensuring the database file and tables are created automatically if they are missing.

---

## 4. Essential Terminal Commands

| Command | Description |
|---|---|
| `python main.py` | Start the backend server |
| Delete `test.db` + restart | Reset environment and rebuild from seed data |
