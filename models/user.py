from data.database import Database
import sqlite3


class User:
    def __init__(self, db_path: str):
        self.db = Database(db_path)

    def count_all(self):
        with self.db.connect() as con:
            cur = con.cursor()
            cur.execute("SELECT COUNT() FROM users")
            con.commit()
            return cur.fetchone()

    def count_experts_by_status(self, status):
        # Count experts by status (nieuw, goedgekeurd, afgekeurd)
        with self.db.connect() as con:
            cur = con.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM users WHERE role = 'expert' AND status = ?",
                (status,),
            )
            return cur.fetchone()[0]

    def get_new_resgistrations(self):
        with self.db.connect() as con:
            cur = con.cursor()
            cur.execute("SELECT * FROM users WHERE status = 'nieuw'")
            con.commit()
            return cur.fetchall()

    def get_user(self, user_id):
        """Select user that is logged in from the database."""
        with self.db.connect() as con:
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            cur.execute(
                "SELECT users.email, users.role, profiles.first_name FROM users JOIN profiles ON users.id = profiles.user_id WHERE user_id = ?",
                (user_id,),
            )
            return cur.fetchone()

    def get_profile_by_user_id(self, user_id):
        """Select user that is logged in from the database."""
        with self.db.connect() as con:
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            cur.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,))
            return cur.fetchone()

    def get_user_organization_id(self, organization_id):
        """Select user that is logged in from the database."""
        with self.db.connect() as con:
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            cur.execute(
                "SELECT users.email, users.status, profiles.first_name "
                "FROM users "
                "LEFT JOIN profiles ON users.id = profiles.user_id "
                "WHERE organization_id = ?",
                (organization_id,),
            )
            return cur.fetchone()

    def get_users_by_role(self, role):
        """Get all users that are organization as role"""
        with self.db.connect() as con:
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            cur.execute("SELECT * FROM users WHERE role = ?", (role,))
            return cur.fetchall()

    def get_all_users(self):
        """Get list of users"""
        with self.db.connect() as con:
            cur = con.cursor()
            cur.execute("SELECT * from users")
            return cur.fetchall()

    def get_all_experts(self, limit=20, offset=0, search=None, status=None):
        with self.db.connect() as con:
            cur = con.cursor()

            # Build WHERE clause based on filters
            where_clauses = ["u.role = 'expert'"]
            params = []

            if search:
                where_clauses.append(
                    "(p.first_name LIKE ? OR p.last_name LIKE ? OR u.email LIKE ?)"
                )
                search_param = f"%{search}%"
                params.extend([search_param, search_param, search_param])

            if status:
                where_clauses.append("u.status = ?")
                params.append(status)

            where_sql = " AND ".join(where_clauses)
            params.extend([limit, offset])

            cur.execute(
                f"""
                SELECT 
                    u.id,
                    u.email,
                    u.status,
                    p.first_name,
                    p.last_name,
                    p.birth_date,
                    GROUP_CONCAT(d.name, ', ') as disabilities
                FROM users u
                LEFT JOIN profiles p ON u.id = p.user_id
                LEFT JOIN profile_disabilities pd ON p.id = pd.profile_id
                LEFT JOIN disabilities d ON pd.disability_id = d.id
                WHERE {where_sql}
                GROUP BY u.id, u.email, u.status, p.first_name, p.last_name, p.birth_date
                ORDER BY u.id
                LIMIT ? OFFSET ?
            """,
                params,
            )
            con.commit()
            return cur.fetchall()

    def count_all_experts(self, search=None, status=None):
        with self.db.connect() as con:
            cur = con.cursor()

            # Build WHERE clause based on filters
            where_clauses = ["u.role = 'expert'"]
            params = []

            if search:
                where_clauses.append(
                    "(p.first_name LIKE ? OR p.last_name LIKE ? OR u.email LIKE ?)"
                )
                search_param = f"%{search}%"
                params.extend([search_param, search_param, search_param])

            if status:
                where_clauses.append("u.status = ?")
                params.append(status)

            where_sql = " AND ".join(where_clauses)

            cur.execute(
                f"SELECT COUNT(DISTINCT u.id) FROM users u LEFT JOIN profiles p ON u.id = p.user_id WHERE {where_sql}",
                params,
            )
            return cur.fetchone()[0]

    # get detailed information for a specific expert including all profile data.
    def get_expert_detail_by_id(self, expert_id):
        with self.db.connect() as con:
            cur = con.cursor()
            cur.execute(
                """
                SELECT 
                    u.id,
                    u.email,
                    u.status,
                    p.first_name,
                    p.last_name,
                    p.birth_date,
                    p.gender,
                    p.postcode,
                    p.phone,
                    p.assistive_tools,
                    p.intro,
                    p.notes,
                    p.agreed_terms,
                    p.has_guardian,
                    p.guardian_name,
                    p.guardian_email,
                    p.guardian_phone,
                    p.contact_preference,
                    p.preferred_study_type,
                    p.availability,
                    GROUP_CONCAT(d.name, ', ') as disabilities
                FROM users u
                LEFT JOIN profiles p ON u.id = p.user_id
                LEFT JOIN profile_disabilities pd ON p.id = pd.profile_id
                LEFT JOIN disabilities d ON pd.disability_id = d.id
                WHERE u.role = 'expert' AND u.id = ?
                GROUP BY u.id
            """,
                (expert_id,),
            )
            con.commit()
            return cur.fetchone()

    def get_studies_list(self):
        """Get full study list from DB"""
        with self.db.connect() as con:
            cur = con.cursor()
            cur.execute(
                "SELECT org.id AS org_id, "
                "org.name AS org_name, "
                "org.type AS org_type, "
                "org.website AS org_website, "
                "org.description AS org_description, "
                "org.contact_person AS org_contact_person, "
                "org.email AS org_email, "
                "org.phone AS org_phone, "
                "org.phone AS org_phone, "
                "study.id AS study_id, "
                "study.organization_id AS study_org_id, "
                "study.title AS study_title, "
                "study.status AS study_status, "
                "study.available AS study_available, "
                "study.description AS study_description, "
                "study.start_date AS study_start_date, "
                "study.end_date AS study_end_date, "
                "study.study_type AS study_study_type, "
                "study.location AS study_location, "
                "study.reward AS study_reward, "
                "study.has_reward AS study_has_reward, "
                "study.age_min AS study_age_min, "
                "study.age_max AS study_age_max "
                "FROM organizations org "
                "LEFT JOIN studies study ON org.id = study.organization_id"
            )
            con.commit()
            return cur.fetchall()

    def get_study_list_by_id(self, study_id):
        """Get full study list from DB with study_id"""
        with self.db.connect() as con:
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            cur.execute(
                "SELECT organizations.id AS org_id, "
                "organizations.name AS org_name, "
                "organizations.type AS org_type, "
                "organizations.website AS org_website, "
                "organizations.description AS org_description, "
                "organizations.contact_person AS org_contact_person, "
                "organizations.email AS org_email, "
                "organizations.phone AS org_phone, "
                "studies.id AS study_id, "
                "studies.organization_id AS study_organization_id, "
                "studies.title AS study_title, "
                "studies.status AS study_status, "
                "studies.available AS study_available, "
                "studies.description AS study_description, "
                "studies.start_date AS study_start_date, "
                "studies.end_date AS study_end_date, "
                "studies.study_type AS study_study_type, "
                "studies.location AS study_location, "
                "studies.reward AS study_reward, "
                "studies.has_reward AS study_has_reward, "
                "studies.age_min AS study_age_min, "
                "studies.age_max AS study_age_max "
                "FROM organizations "
                "LEFT JOIN studies ON organizations.id = studies.organization_id WHERE studies.id = ?",
                (study_id,),
            )
            return cur.fetchone()

    def get_enrollment_list_filtered_disability(self, profile_id):
        """Get enrollment list filtered disability from DB"""
        with self.db.connect() as con:
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            cur.execute(
                "SELECT disability_id FROM profile_disabilities WHERE profile_id = ?",
                (profile_id,),
            )
            row = cur.fetchone()

            if not row:

                return []
            disability_id = int(row["disability_id"])

            cur.execute(
                "SELECT studies.id AS study_id, "
                "studies.title AS study_title, "
                "studies.status AS study_status, "
                "studies.description AS study_description, "
                "studies.study_type AS study_study_type, "
                "studies.location AS study_location, "
                "studies.reward AS study_reward, "
                "studies.start_date AS study_start_date, "
                "studies.end_date AS study_end_date, "
                "organizations.name AS org_name "
                "FROM studies "
                "JOIN study_disabilities sd ON studies.id = sd.study_id "
                "JOIN organizations ON organizations.id = studies.organization_id "
                "WHERE sd.disability_id = ? AND studies.status = 'goedgekeurd'",
                (disability_id,),
            )
            return cur.fetchall()

    def get_enrollment_id(self, enrollment_id):
        """Get enrollment test from DB"""
        with self.db.connect() as con:
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            cur.execute(
                "SELECT enrollments.id AS enrollment_id, "
                "enrollments.status AS enrollment_status, "
                "enrollments.created_at AS enrollment_created_at, "
                "organizations.id AS organization_id, "
                "organizations.name AS organization_name, "
                "organizations.website AS organization_website, "
                "organizations.description AS organization_description, "
                "studies.id AS study_id, "
                "studies.title AS study_title, "
                "studies.status AS study_status, "
                "studies.description AS study_description, "
                "studies.start_date AS study_start_date, "
                "studies.end_date AS study_end_date, "
                "studies.study_type AS study_type, "
                "studies.location AS study_location, "
                "studies.reward AS study_reward, "
                "studies.available AS study_available, "
                "studies.age_min AS study_age_min, "
                "studies.age_max AS study_age_max "
                "FROM enrollments "
                "JOIN studies ON studies.id = enrollments.study_id "
                "JOIN organizations ON organizations.id = studies.organization_id "
                "WHERE enrollments.id = ?",
                (enrollment_id,),
            )
            return cur.fetchone()

    def get_enrollment_by_id(self, profile_id):
        """Get Enrollment by Organization, Profiles, and Studies ID from DB"""
        with self.db.connect() as con:
            cur = con.cursor()
            con.row_factory = sqlite3.Row
            cur.execute(
                "SELECT enrollments.id AS enrollment_id,"
                "enrollments.status AS enrollment_status,"
                "enrollments.created_at AS enrollment_created_at,"
                "profiles.id AS profile_id,"
                "organizations.id AS organization_id,"
                "organizations.name AS organization_name,"
                "organizations.website AS organization_website,"
                "organizations.description AS organization_description,"
                "studies.id AS study_id,"
                "studies.title AS study_title,"
                "studies.status AS study_status,"
                "studies.description AS study_description,"
                "studies.start_date AS study_start_date,"
                "studies.end_date AS study_end_date,"
                "studies.study_type AS study_type,"
                "studies.location AS study_location,"
                "studies.reward AS study_reward, "
                "studies.available AS study_available, "
                "studies.age_min AS study_age_min, "
                "studies.age_max AS study_age_max "
                "FROM enrollments "
                "INNER JOIN studies ON enrollments.study_id = studies.id "
                "INNER JOIN profiles ON enrollments.profile_id = profiles.id "
                "INNER JOIN organizations ON studies.organization_id = organizations.id WHERE enrollments.profile_id = ?",
                (profile_id,),
            )
            return cur.fetchall()

    def register_enrollment(self, study_id, profile_id):
        """Register enrollment, check if already registered."""
        with self.db.connect() as con:
            cur = con.cursor()
            cur.execute(
                "INSERT or IGNORE INTO enrollments(study_id, profile_id, status, created_at) VALUES(?, ?, ?, CURRENT_TIMESTAMP)",
                (study_id, profile_id, "nieuw"),
            )
            con.commit()

    def get_profile(self, user_id):
        """Get Profile from DB."""
        if not user_id:
            return None

        with self.db.connect() as con:
            cur = con.cursor()
            cur.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,))
            return cur.fetchone()

    def update_profile(
        self,
        first_name,
        last_name,
        postcode,
        gender,
        phone,
        birth_date,
        assistive_tools,
        intro,
        notes,
        contact_preference,
        disability_id,
        profile_id,
    ):
        """Update Profile from DB"""
        with self.db.connect() as con:
            cur = con.cursor()
            cur.execute(
                "UPDATE profiles SET first_name = ?, last_name = ?, postcode = ?, gender = ?, phone = ?, birth_date = ?, assistive_tools = ?, intro = ?, notes = ?, contact_preference = ? WHERE id = ?",
                (
                    first_name,
                    last_name,
                    postcode,
                    gender,
                    phone,
                    birth_date,
                    assistive_tools,
                    intro,
                    notes,
                    contact_preference,
                    profile_id,
                ),
            )
            cur.execute(
                "DELETE FROM profile_disabilities WHERE profile_id = ?", (profile_id,)
            )
            cur.execute(
                "INSERT INTO profile_disabilities (profile_id, disability_id) VALUES (?, ?)",
                (profile_id, disability_id),
            )
            con.commit()

    def get_profile_disability(self, profile_id):
        """Get Disability from DB"""
        with self.db.connect() as con:
            cur = con.cursor()
            cur.execute(
                "SELECT d.id, d.name FROM disabilities d "
                "JOIN profile_disabilities pd ON d.id = pd.disability_id "
                "WHERE pd.profile_id = ? ",
                (profile_id,),
            )
            return cur.fetchall()

    def get_all_disabilities(self):
        """Get Disability List from DB"""
        with self.db.connect() as con:
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            cur.execute("SELECT * FROM disabilities ")
            return cur.fetchall()

    def authenticate_register(self, email):
        """validates the user's email if it already exists"""
        if not email:
            return None

        with self.db.connect() as con:
            cur = con.cursor()
            cur.execute("SELECT * FROM users WHERE email = ?", (email,))
            con.commit()
            return cur.fetchone()

    def create_new_user(self, email, password, role):
        """creates a new user"""
        if not email or not password or not role:
            return False

        with self.db.connect() as con:
            cur = con.cursor()
            cur.execute(
                "INSERT INTO users (email, password, role) VALUES (?, ?, ?)",
                (email, password, role),
            )
            con.commit()
            print(cur.lastrowid)
            return cur.lastrowid

    def create_new_profile(
        self,
        user_id,
        first_name,
        last_name,
        postcode,
        gender,
        phone,
        birth_date,
        assistive_tools,
        contact_preference,
        intro,
        notes,
        disability_id,
    ):
        """creates a new profile with the given data"""
        with self.db.connect() as con:
            cur = con.cursor()
            cur.execute(
                "INSERT INTO profiles (user_id, first_name, last_name, postcode, gender, phone, birth_date, "
                "assistive_tools, contact_preference, intro, notes) VALUES (?, ?, ?, ?, ?, ?, ? ,?, ?, ?, ?)",
                (
                    user_id,
                    first_name,
                    last_name,
                    postcode,
                    gender,
                    phone,
                    birth_date,
                    assistive_tools,
                    contact_preference,
                    intro,
                    notes,
                ),
            )
            cur.execute(
                "DELETE FROM profile_disabilities WHERE profile_id = ?",
                (cur.lastrowid,),
            )
            cur.execute(
                "INSERT INTO profile_disabilities (profile_id, disability_id) VALUES (?, ?)",
                (cur.lastrowid, disability_id),
            )
            con.commit()
            print(cur.lastrowid)
            return cur.lastrowid

    def authenticate(self, email, password):
        """validate user's email and password"""
        with self.db.connect() as con:
            cur = con.cursor()
            cur.execute(
                "SELECT * FROM users WHERE email = ? and password = ?",
                (email, password),
            )
            con.commit()
            return cur.fetchone()

    def get_current_user(self, user_id):
        """Getting the current user"""
        if not user_id:
            return None

        with self.db.connect() as con:
            cur = con.cursor()
            cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            con.commit()
            return cur.fetchone()

    def approve_expert(self, expert_id):
        with self.db.connect() as con:
            cur = con.cursor()
            cur.execute(
                """
                UPDATE users 
                SET status = 'goedgekeurd' 
                WHERE id = ? AND role = 'expert'
            """,
                (expert_id,),
            )
            con.commit()
            return cur.rowcount > 0

    def reject_expert(self, expert_id):
        with self.db.connect() as con:
            cur = con.cursor()
            cur.execute(
                """
                UPDATE users 
                SET status = 'afgekeurd' 
                WHERE id = ? AND role = 'expert'
            """,
                (expert_id,),
            )
            con.commit()
            return cur.rowcount > 0

    def update_expert(
        self,
        expert_id,
        email,
        status,
        first_name,
        last_name,
        phone,
        postcode,
        birth_date,
        gender,
        assistive_tools,
        contact_preference,
        preferred_study_type,
        availability,
        intro,
        notes,
    ):
        # Update both user and profile tables for an expert
        with self.db.connect() as con:
            cur = con.cursor()

            # Update users table
            cur.execute(
                """
                UPDATE users 
                SET email = ?, status = ? 
                WHERE id = ? AND role = 'expert'
                """,
                (email, status, expert_id),
            )

            # Update profiles table
            cur.execute(
                """
                UPDATE profiles 
                SET first_name = ?, last_name = ?, phone = ?, postcode = ?, 
                    birth_date = ?, gender = ?, assistive_tools = ?, 
                    contact_preference = ?, preferred_study_type = ?, 
                    availability = ?, intro = ?, notes = ?
                WHERE user_id = ?
                """,
                (
                    first_name,
                    last_name,
                    phone,
                    postcode,
                    birth_date,
                    gender,
                    assistive_tools,
                    contact_preference,
                    preferred_study_type,
                    availability,
                    intro,
                    notes,
                    expert_id,
                ),
            )

            con.commit()
            return cur.rowcount > 0
