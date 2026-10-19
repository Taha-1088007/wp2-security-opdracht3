import sqlite3

DB_PATH = "app.db"


def seed():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    cur = con.cursor()
    cur.execute("DELETE FROM enrollments")
    cur.execute("DELETE FROM study_disabilities")
    cur.execute("DELETE FROM studies")
    cur.execute("DELETE FROM profile_disabilities")
    cur.execute("DELETE FROM profiles")
    cur.execute("DELETE FROM users")
    cur.execute("DELETE FROM organizations")

    admin = ["admin@hub.com"]

    # 1x | Create Admin
    for email in admin:
        cur.execute(
            "INSERT INTO users (email, password, role, status) "
            "VALUES (?, 'admin', 'admin', 'goedgekeurd') ",
            (email,),
        )

    experts = [
        "expert1@seed.nl",
        "expert2@seed.nl",
        "expert3@seed.nl",
        "expert4@seed.nl",
        "expert5@seed.nl",
    ]

    organizations = [
        (
            "Microsoft",
            "non-profit",
            "https://microsoft.org",
            "Onderzoek digitale toegankelijkheid",
            "Bill Gates",
            "billgates@microsoft.com",
            "0123456789",
            None,
        ),
        (
            "Facebook",
            "commercieel",
            "https://facebook.com",
            "Profiel formulieren",
            "Mark Zuckerburg",
            "markzuckerburg@facebook.com",
            "0123456789",
            None,
        ),
        (
            "Apple",
            "commercieel",
            "https://apple.com",
            "Telefoon toegankhelijkeid",
            "Steve Jobs",
            "stevejobs@apple.com",
            "0123456789",
            None,
        ),
    ]

    # 3x | Create organization profiles
    cur.executemany(
        "INSERT INTO organizations (name, type, website, description, contact_person, email, phone, details) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        organizations,
    )

    cur.execute("SELECT id, name FROM organizations ")
    org_ids = {row["name"]: row["id"] for row in cur.fetchall()}

    org_users = [
        (
            "org-microsoft@seed.nl",
            "secret",
            "organization",
            "goedgekeurd",
            org_ids["Microsoft"],
        ),
        (
            "org-facebook@seed.nl",
            "secret",
            "organization",
            "goedgekeurd",
            org_ids["Facebook"],
        ),
        (
            "org-apple@seed.nl",
            "secret",
            "organization",
            "goedgekeurd",
            org_ids["Apple"],
        ),
    ]

    # 3x | Assign organizations to users
    for email, password, role, status, organization_id in org_users:
        cur.execute(
            "INSERT INTO users (email, password, role, status, organization_id) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                email,
                password,
                role,
                status,
                organization_id,
            ),
        )

    # 5x | Create Experts
    for email in experts:
        cur.execute(
            "INSERT INTO users (email, password, role, status) "
            "VALUES (?, 'secret', 'expert', 'goedgekeurd') ",
            (email,),
        )

    profiles = [
        (
            "expert1@seed.nl",
            "Ali",
            "Sheikh",
            "9999ZX",
            "0123456789",
            "19-2-1955",
            "e-mail",
            "online",
        ),
        (
            "expert2@seed.nl",
            "Baron",
            "Beton",
            "8888SS",
            "0123456789",
            "11-3-10",
            "telefoon",
            "telefonisch",
        ),
        (
            "expert3@seed.nl",
            "Kees",
            "Maf",
            "7777AS",
            "0123456789",
            "31-6-1935",
            "e-mail",
            "op locatie",
        ),
        (
            "expert4@seed.nl",
            "Nina",
            "Boef",
            "1232ZT",
            "0123456789",
            "15-4-1965",
            "telefoon",
            "online",
        ),
        (
            "expert5@seed.nl",
            "Lara",
            "Croft",
            "3343FD",
            "0123456789",
            "23-3-1933",
            "e-mail",
            "online",
        ),
    ]

    # 5x | Assign Experts to Profiles
    for email, first, last, postcode, tel, birth, contact, preference in profiles:
        cur.execute(
            "INSERT INTO profiles "
            "(user_id, first_name, last_name, postcode, phone, birth_date, contact_preference, preferred_study_type) "
            "SELECT id, ?, ?, ?, ?, ?, ?, ? "
            "FROM users WHERE email = ?",
            (first, last, postcode, tel, birth, contact, preference, email),
        )

    profile_disabilities = [
        ("expert1@seed.nl", "Blind"),
        ("expert2@seed.nl", "ADHD"),
        ("expert3@seed.nl", "Autisme"),
        ("expert4@seed.nl", "RSI"),
        ("expert5@seed.nl", "Dyslexie"),
    ]

    # Assign Profiles with disabilities
    for email, disability in profile_disabilities:
        cur.execute(
            "INSERT INTO profile_disabilities (profile_id, disability_id) "
            "SELECT p.id, d.id "
            "FROM profiles p "
            "JOIN users u ON u.id = p.user_id "
            "JOIN disabilities d ON d.name = ? "
            "WHERE u.email = ? ",
            (disability, email),
        )

    studies = [
        (
            org_ids["Microsoft"],
            "Seed onderzoek A",
            "goedgekeurd",
            "2025-12-30",
            "2026-01-30",
            "online",
        ),
        (
            org_ids["Facebook"],
            "Seed onderzoek B",
            "goedgekeurd",
            "2025-12-29",
            "2026-01-29",
            "online",
        ),
        (
            org_ids["Apple"],
            "Seed onderzoek C",
            "goedgekeurd",
            "2025-12-28",
            "2026-01-28",
            "online",
        ),
        (
            org_ids["Microsoft"],
            "Seed onderzoek D",
            "goedgekeurd",
            "2026-01-01",
            "2026-02-01",
            "online",
        ),
        (
            org_ids["Facebook"],
            "Seed onderzoek E",
            "goedgekeurd",
            "2026-01-02",
            "2026-02-02",
            "online",
        ),
        (
            org_ids["Apple"],
            "Seed onderzoek F",
            "goedgekeurd",
            "2026-01-05",
            "2026-02-05",
            "op locatie",
        ),
        (
            org_ids["Microsoft"],
            "Seed onderzoek G",
            "goedgekeurd",
            "2026-01-08",
            "2026-02-08",
            "telefonisch",
        ),
        (
            org_ids["Facebook"],
            "Seed onderzoek H",
            "nieuw",
            "2026-01-10",
            "2026-02-10",
            "online",
        ),
        (
            org_ids["Apple"],
            "Seed onderzoek I",
            "nieuw",
            "2026-01-11",
            "2026-02-11",
            "op locatie",
        ),
        (
            org_ids["Microsoft"],
            "Seed onderzoek J",
            "nieuw",
            "2026-01-12",
            "2026-02-12",
            "telefonisch",
        ),
    ]

    # Create studies assigned to organizations
    cur.executemany(
        "INSERT INTO studies "
        "(organization_id, title, status, start_date, end_date, study_type) "
        "VALUES (?, ?, ?, ?, ?, ?) ",
        studies,
    )

    # Select id and title from studies
    cur.execute("SELECT id, title FROM studies ")
    study_ids = {row["title"]: row["id"] for row in cur.fetchall()}

    # Assign studies with disabilities
    study_disabilities = [
        (study_ids["Seed onderzoek A"], 1),
        (study_ids["Seed onderzoek B"], 2),
        (study_ids["Seed onderzoek C"], 3),
        (study_ids["Seed onderzoek D"], 4),
        (study_ids["Seed onderzoek E"], 5),
        (study_ids["Seed onderzoek F"], 6),
        (study_ids["Seed onderzoek G"], 7),
        (study_ids["Seed onderzoek H"], 8),
        (study_ids["Seed onderzoek I"], 9),
        (study_ids["Seed onderzoek J"], 10),
    ]

    for study, disability in study_disabilities:
        cur.execute(
            "INSERT INTO study_disabilities (study_id, disability_id) VALUES (?, ?) ",
            (study, disability),
        )

    enrollments = [
        ("expert1@seed.nl", "Seed onderzoek A"),
        ("expert2@seed.nl", "Seed onderzoek B"),
        ("expert3@seed.nl", "Seed onderzoek C"),
        ("expert4@seed.nl", "Seed onderzoek D"),
        ("expert5@seed.nl", "Seed onderzoek E"),
        ("expert6@seed.nl", "Seed onderzoek F"),
        ("expert1@seed.nl", "Seed onderzoek G"),
        ("expert2@seed.nl", "Seed onderzoek H"),
        ("expert3@seed.nl", "Seed onderzoek I"),
        ("expert4@seed.nl", "Seed onderzoek J"),
    ]

    # Create enrollments and assign them to Experts
    for study_id, profile_id in enrollments:
        cur.execute(
            "INSERT INTO enrollments "
            "(study_id, profile_id, status) "
            "SELECT s.id, p.id, 'nieuw'"
            "FROM studies s "
            "JOIN profiles p ON p.user_id = (SELECT id FROM users WHERE email = ?)"
            "WHERE s.title = ?",
            (study_id, profile_id),
        )

    for a in admin:
        print("------------------")
        print(a, "| admin")

    for e in experts:
        print(e, "| secret")
    print("------------------")

    for o in org_users:
        print(o[0], "| secret")
    print("------------------")

    print("\nRemoved old database records.")
    print("Database created successfully.")

    con.commit()
    con.close()


if __name__ == "__main__":
    seed()
