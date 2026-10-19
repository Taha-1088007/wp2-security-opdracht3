import sqlite3
from data.database import Database


class Organization:
    def __init__(self, db_path: str):
        self.db = Database(db_path)

    def count_all(self):
        with self.db.connect() as con:
            cur = con.cursor()
            cur.execute("SELECT COUNT() FROM organizations")
            con.commit()
            return cur.fetchone()

    def select_all_organisations(self, limit=20, offset=0, search=None, org_type=None):
        """ Select all organizations """
        # Get all organisations with optional search and type filter
        with self.db.connect() as con:
            # con.row_factory = sqlite3.Row
            cur = con.cursor()

            # Build WHERE clause based on filters
            where_clauses = []
            params = []

            if search:
                where_clauses.append("organizations.name LIKE ?")
                params.append(f"%{search}%")

            if org_type:
                where_clauses.append("organizations.type = ?")
                params.append(org_type)

            where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
            params.extend([limit, offset])

            cur.execute(
                f"SELECT organizations.*, "
                "users.id AS user_id, "
                "users.email AS user_email, "
                "users.status AS user_status "
                "FROM organizations "
                "LEFT JOIN users ON organizations.id = users.organization_id "
                f"{where_sql} "
                "LIMIT ? OFFSET ?",
                params,
            )
            return cur.fetchall()

    def count_all_organizations(self, search=None, org_type=None):
        """ Count all organizations """
        with self.db.connect() as con:
            cur = con.cursor()

            # Build WHERE clause based on filters
            where_clauses = []
            params = []

            if search:
                where_clauses.append("name LIKE ?")
                params.append(f"%{search}%")

            if org_type:
                where_clauses.append("type = ?")
                params.append(org_type)

            where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

            cur.execute(f"SELECT COUNT(*) FROM organizations {where_sql}", params)
            return cur.fetchone()[0]

    def get_single_organisations(self, organization_id):
        """Get single organisation"""
        with self.db.connect() as con:
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            cur.execute(
                "SELECT * FROM organizations " "WHERE organizations.id = ? ",
                (organization_id,),
            )
            con.commit()
            return cur.fetchone()

    def create_organization(
        self,
        name,
        org_type,
        website,
        description,
        contact_person,
        email,
        phone,
        details,
    ):
        """Create organization profile"""
        with self.db.connect() as con:
            cur = con.cursor()
            cur.execute(
                "INSERT INTO organizations (name, type, website, description, contact_person, email, phone, details) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    name,
                    org_type,
                    website,
                    description,
                    contact_person,
                    email,
                    phone,
                    details,
                ),
            )
            con.commit()
            return cur.lastrowid

    def set_organization(self, user_id, organization_id):
        """Set organization"""
        with self.db.connect() as con:
            cur = con.cursor()
            cur.execute(
                "UPDATE users "
                "SET organization_id = NULL "
                "WHERE organization_id = ? ",
                (organization_id,),
            )

            cur.execute(
                "UPDATE users " "SET organization_id = ?" "WHERE id = ? "
                # "AND role = 'organization'"
                ,
                (organization_id, user_id),
            )
            con.commit()

    def set_role(self, user_id, role):
        """Set user role from Expert to Organization"""
        with self.db.connect() as con:
            cur = con.cursor()
            cur.execute("UPDATE users " "SET role = ? WHERE id = ?", (role, user_id))
            con.commit()

    def update_status(self, user_id, status,  clear_email=False):
        """ Update user status """
        with self.db.connect() as con:
            cur = con.cursor()
            if clear_email:
                cur.execute(
                    "UPDATE users "
                    "SET status = ?, organization_id = NULL "
                    "WHERE id = ? AND role = 'organization'",
                    (status, user_id),
                )
            else:
                cur.execute(
                    "UPDATE users "
                    "SET status = ?"
                    "WHERE id = ? AND role = 'organization'",
                    (status, user_id),
                )
            con.commit()
    #
    # def accept_organization(self, organization_id):
    #     """ Accepting user as organization changing status to accepted. """
    #     with self.db.connect() as con:
    #         con.row_factory = sqlite3.Row
    #         cur = con.cursor()
    #         cur.execute(
    #             "UPDATE users "
    #             "SET status = 'goedgekeurd' "
    #             "WHERE role = 'organization' "
    #             "AND organization_id = ? ", (organization_id, )
    #         )
    #         con.commit()
    #         return cur.rowcount
    #
    # def reject_organization(self, organization_id):
    #     """ Rejecting user as organization changing status to rejected. """
    #     with self.db.connect() as con:
    #         con.row_factory = sqlite3.Row
    #         cur = con.cursor()
    #         cur.execute(
    #             "UPDATE users "
    #             "SET status = 'afgekeurd' "
    #             "WHERE role = 'organization' "
    #             "AND organization_id = ? ", (organization_id,)
    #         )
    #         con.commit()
    #         return cur.rowcount

    # update organization profile
    def update_organization(self, organization_id, name, org_type,
                            website, description, contact_person, email, phone, details):
        """ Update organization profile """
        with self.db.connect() as con:
            cur = con.cursor()
            cur.execute(
                "UPDATE organizations "
                "SET name = ?, type = ?, website = ?, description = ?, "
                "contact_person = ?, email = ?, phone = ?, details = ? "
                "WHERE id = ?",
                (
                    name,
                    org_type,
                    website,
                    description,
                    contact_person,
                    email,
                    phone,
                    details,
                    organization_id,
                ),
            )
            con.commit()
            return cur.rowcount
