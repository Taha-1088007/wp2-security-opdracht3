import sqlite3
from data.database import Database


class Enrollment:
    def __init__(self, db_path: str):
        self.db = Database(db_path)

    def count_all(self):
        """Count all enrollments"""
        with self.db.connect() as con:
            cur = con.cursor()
            cur.execute("SELECT COUNT() FROM enrollments")
            return cur.fetchone()

    def count_enrollments_by_status(self, status):
        """Count enrollments by status (nieuw, goedgekeurd, afgekeurd)"""
        with self.db.connect() as con:
            cur = con.cursor()
            cur.execute("SELECT COUNT(*) FROM enrollments WHERE status = ?", (status,))
            return cur.fetchone()[0]

    def get_new_enrollments(self):
        """Get new enrollments"""
        with self.db.connect() as con:
            cur = con.cursor()
            cur.execute("SELECT * FROM enrollments WHERE status = 'nieuw'")
            con.commit()
            return cur.fetchall()

    def approved_enrollments_study(self, study_id):
        """Returns all approved enrollments for a specific study"""
        with self.db.connect() as con:
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            cur.execute(
                """SELECT profiles.first_name, profiles.last_name, enrollments.created_at
                FROM enrollments
                JOIN profiles ON profiles.id = enrollments.profile_id
                WHERE enrollments.study_id = ?
                AND enrollments.status = 'goedgekeurd'
                ORDER BY enrollments.created_at DESC""",
                (study_id,),
            )
            return cur.fetchall()

    def get_enrollment_list(self, limit=20, offset=0, status=None):
        """Get enrollment list with optional status filter."""
        with self.db.connect() as con:
            con.row_factory = sqlite3.Row
            cur = con.cursor()

            # Build WHERE clause based on filter
            where_sql = "WHERE enrollments.status = ?" if status else ""
            params = [status] if status else []
            params.extend([limit, offset])

            cur.execute(
                "SELECT enrollments.id AS enrollment_id,"
                "enrollments.status AS enrollment_status,"
                "enrollments.created_at AS enrollment_created_at,"
                "profiles.id AS profile_id,"
                "profiles.first_name AS first_name,"
                "profiles.last_name AS last_name,"
                "profiles.phone AS phone,"
                "profiles.birth_date AS birth_date,"
                "profiles.assistive_tools AS assistive_tools,"
                "profiles.preferred_study_type AS preferred_study_type,"
                "organizations.id AS organization_id,"
                "organizations.name AS organization_name,"
                "organizations.website AS organization_website,"
                "organizations.description AS organization_description,"
                "organizations.email AS organization_email,"
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
                "studies.age_max AS study_age_max, "
                "users.email AS email "
                "FROM enrollments "
                "INNER JOIN studies ON enrollments.study_id = studies.id "
                "INNER JOIN profiles ON enrollments.profile_id = profiles.id "
                "INNER JOIN organizations ON studies.organization_id = organizations.id "
                "INNER JOIN users ON users.id = profiles.user_id "
                f"{where_sql} "
                "LIMIT ? OFFSET ?",
                params,
            )
            return cur.fetchall()

    def count_all_enrollments(self, status=None):
        """Count all enrollments"""
        with self.db.connect() as con:
            cur = con.cursor()

            # Build WHERE clause based on filter
            where_sql = "WHERE status = ?" if status else ""
            params = [status] if status else []

            cur.execute(f"SELECT COUNT(*) FROM enrollments {where_sql}", params)
            return cur.fetchone()[0]

    def get_enrollment_list_items(self, enroll_id):
        """Get enrollment list filtered disability from DB"""
        with self.db.connect() as con:
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            cur.execute(
                "SELECT enrollments.id AS enrollment_id,"
                "enrollments.status AS enrollment_status,"
                "enrollments.created_at AS enrollment_created_at,"
                "profiles.id AS profile_id,"
                "profiles.first_name AS first_name,"
                "profiles.last_name AS last_name,"
                "profiles.phone AS phone,"
                "profiles.birth_date AS birth_date,"
                "profiles.assistive_tools AS assistive_tools,"
                "profiles.preferred_study_type AS preferred_study_type,"
                "organizations.id AS organization_id,"
                "organizations.name AS organization_name,"
                "organizations.website AS organization_website,"
                "organizations.description AS organization_description,"
                "organizations.email AS organization_email,"
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
                "studies.age_max AS study_age_max, "
                "users.email AS email, "
                "disabilities.name AS disability "
                "FROM enrollments "
                "INNER JOIN studies ON enrollments.study_id = studies.id "
                "INNER JOIN profiles ON enrollments.profile_id = profiles.id "
                "INNER JOIN organizations ON studies.organization_id = organizations.id "
                "INNER JOIN users ON users.id = profiles.user_id "
                "INNER JOIN profile_disabilities ON profile_disabilities.profile_id = profiles.id "
                "INNER JOIN disabilities ON disabilities.id = profile_disabilities.disability_id "
                "WHERE enrollments.id = ?",
                (enroll_id,),
            )
            return cur.fetchone()

    def update_enrollment_status(self, enroll_id):
        """Accepting enrollment and changing status to accepted."""
        with self.db.connect() as con:
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            cur.execute(
                "UPDATE enrollments " "SET status = 'goedgekeurd' " "WHERE id = ?",
                (enroll_id,),
            )
            con.commit()
            return cur.rowcount

    def delete_enrollment_status(self, enroll_id):
        """Rejecting enrollment and changing status to rejected."""
        with self.db.connect() as con:
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            cur.execute(
                "UPDATE enrollments " "SET status = 'afgekeurd' " "WHERE id = ?",
                (enroll_id,),
            )
            con.commit()
            return cur.rowcount
