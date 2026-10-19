from data.database import Database
import sqlite3


class Study:
    def __init__(self, db_path: str):
        self.db = Database(db_path)

    def count_all(self):
        with self.db.connect() as con:
            cur = con.cursor()
            cur.execute("SELECT COUNT() FROM studies")
            con.commit()
            return cur.fetchone()

    def count_studies_by_status(self, status):
        # Count studies by status (nieuw, goedgekeurd, afgekeurd, gesloten)
        with self.db.connect() as con:
            cur = con.cursor()
            cur.execute("SELECT COUNT(*) FROM studies WHERE status = ?", (status,))
            return cur.fetchone()[0]

    def get_pending_studies(self, limit=10):
        with self.db.connect() as con:
            cur = con.cursor()
            cur.execute(
                """
                SELECT s.id, s.title, o.name as org_name, 
                       s.date, s.type, s.location, s.duration, s.reward
                FROM studies s
                JOIN organizations o ON s.organization_id = o.id
                ORDER BY s.id DESC
                LIMIT ?
            """,
                (limit,),
            )

    def get_studies_by_organization_paginated(self, organization_id, limit, offset):
        """Retrieves all studies that belong to organization with pagination"""
        with self.db.connect() as con:
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            cur.execute(
                """SELECT * FROM studies 
                        WHERE organization_id = ? 
                        ORDER BY id DESC 
                        LIMIT ? OFFSET ?""",
                (organization_id, limit, offset),
            )
            return cur.fetchall()

    def get_study_by_id(self, study_id):
        """Retrieves a study by its id"""
        with self.db.connect() as con:
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            cur.execute("SELECT * FROM studies WHERE id = ?", (study_id,))
            return cur.fetchone()

    def create_study(
        self, title, description, start_date, end_date, reward, organization_id
    ):
        """Creates a new study"""
        with self.db.connect() as con:
            cur = con.cursor()
            cur.execute(
                """INSERT INTO studies
                        (title, description, start_date, end_date, status, reward, organization_id)
                        VALUES (?, ?, ?, ?, 'nieuw', ?, ?)""",
                (title, description, start_date, end_date, reward, organization_id),
            )
            con.commit()

    def update_study(
        self,
        study_id,
        title,
        description,
        start_date,
        end_date,
        reward,
        status,
        organization_id,
        study_type,
    ):
        # Update study with all editable fields including status, organization and study_type
        with self.db.connect() as con:
            cur = con.cursor()
            cur.execute(
                """UPDATE studies
            SET title = ?, description = ?, start_date = ?, end_date = ?, reward = ?, status = ?, organization_id = ?, study_type = ? 
            WHERE id = ?""",
                (
                    title,
                    description,
                    start_date,
                    end_date,
                    reward,
                    status,
                    organization_id,
                    study_type,
                    study_id,
                ),
            )
            con.commit()

    def get_all_studies(self, limit=20, offset=0, search=None, status=None):
        # Get all studies with organization name via JOIN
        with self.db.connect() as con:
            cur = con.cursor()

            # Build WHERE clause based on filters
            where_clauses = []
            params = []

            if search:
                where_clauses.append("studies.title LIKE ?")
                params.append(f"%{search}%")

            if status:
                where_clauses.append("studies.status = ?")
                params.append(status)

            where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
            params.extend([limit, offset])

            cur.execute(
                f"SELECT studies.*, organizations.name AS org_name "
                f"FROM studies "
                f"LEFT JOIN organizations ON studies.organization_id = organizations.id "
                f"{where_sql} "
                f"ORDER BY studies.id DESC "
                f"LIMIT ? OFFSET ?",
                params,
            )
            return cur.fetchall()

    def count_all_studies(self, search=None, status=None):
        with self.db.connect() as con:
            cur = con.cursor()

            # Build WHERE clause based on filters
            where_clauses = []
            params = []

            if search:
                where_clauses.append("title LIKE ?")
                params.append(f"%{search}%")

            if status:
                where_clauses.append("status = ?")
                params.append(status)

            where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

            cur.execute(f"SELECT COUNT(*) FROM studies {where_sql}", params)
            return cur.fetchone()[0]

    def update_status(self, study_id, status):
        with self.db.connect() as con:
            cur = con.cursor()
            cur.execute(
                """UPDATE studies SET status = ? WHERE id = ?""", (status, study_id)
            )
            con.commit()

    def get_study_with_organization(self, study_id):
        # Get study with organization name via JOIN
        with self.db.connect() as con:
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            cur.execute(
                """
                SELECT 
                    studies.*, organizations.name AS org_name,
                    organizations.email AS organization_email,
                    organizations.contact_person AS contact_person
                FROM studies LEFT JOIN organizations
                ON studies.organization_id = organizations.id
                WHERE studies.id = ?
                """,
                (study_id,),
            )
            return cur.fetchone()

    # disabilities for a study with category and name
    def get_study_disabilities_details(self, study_id):
        with self.db.connect() as con:
            cur = con.cursor()
            cur.execute(
                """
                SELECT d.category, d.name 
                FROM study_disabilities sd
                JOIN disabilities d ON sd.disability_id = d.id
                WHERE sd.study_id = ?
                ORDER BY d.category, d.name
            """,
                (study_id,),
            )
            return cur.fetchall()

    def count_studies_by_organization(self, organization_id):
        """counts studies that belong to an organization"""
        with self.db.connect() as con:
            cur = con.cursor()
            cur.execute(
                """SELECT COUNT(*) FROM studies WHERE organization_id = ?""",
                (organization_id,),
            )
            return cur.fetchone()[0]
