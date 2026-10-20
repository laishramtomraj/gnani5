"""faculty_seed.py - FICTIONAL sample data for the faculty prototype.

Every name, qualification, email, office and publication below is invented for
layout and testing. Replace with verified college data before publishing.
Department course ids must match the ids in data.py (COURSES).
"""
from datetime import date

SAMPLE_NOTICE = (
    "All faculty profiles are fictional sample data for this prototype. Names, "
    "qualifications, contact details, publications and other entries are "
    "illustrative and are not real people or verified institutional information."
)

# (department name, ids of the courses in data.py that the department teaches)
DEPARTMENTS = [
    ("Computer Science and Engineering", ["btech-cse"]),
    ("Information Technology", ["btech-it"]),
    ("Artificial Intelligence and Data Science", ["btech-aiml", "btech-ds"]),
    ("Electronics and Communication Engineering", ["btech-ece"]),
    ("Electrical and Electronics Engineering", ["btech-eee"]),
    ("Mechanical Engineering", ["btech-mech"]),
    ("Civil Engineering", ["btech-civil"]),
    ("Management", ["bba", "mba", "bcom"]),
    ("Computer Applications", ["bca", "mca", "bsc-cs"]),
]

_RAW = [
    dict(name="Dr. Arvind Menon", qualifications="B.Tech, M.Tech, Ph.D.", designation="Professor",
         post="Head of Department", department="Computer Science and Engineering",
         specialization="Distributed Systems", teaching=22, industry=4,
         subjects=["Operating Systems", "Distributed Computing", "Cloud Computing"],
         interests="Distributed systems, fault tolerance, cloud architecture"),
    dict(name="Ms. Priya Nair", qualifications="B.Tech, M.Tech", designation="Assistant Professor",
         post="", department="Computer Science and Engineering",
         specialization="Software Engineering", teaching=6, industry=3,
         subjects=["Software Engineering", "Data Structures", "Database Management Systems"],
         interests="Software testing, agile practices, requirements engineering"),
    dict(name="Dr. Kavita Rao", qualifications="B.E., M.Tech, Ph.D.", designation="Associate Professor",
         post="Head of Department", department="Information Technology",
         specialization="Information Security", teaching=14, industry=2,
         subjects=["Information Security", "Cryptography", "Computer Networks"],
         interests="Network security, applied cryptography, secure web systems"),
    dict(name="Dr. Sanjay Iyer", qualifications="B.Tech, M.Tech, Ph.D.", designation="Professor",
         post="Head of Department", department="Artificial Intelligence and Data Science",
         specialization="Machine Learning", teaching=19, industry=5,
         subjects=["Machine Learning", "Deep Learning", "Data Mining"],
         interests="Machine learning, computer vision, responsible AI"),
    dict(name="Ms. Nisha Kulkarni", qualifications="B.Tech, M.Tech", designation="Assistant Professor",
         post="", department="Artificial Intelligence and Data Science",
         specialization="Data Analytics", teaching=5, industry=2,
         subjects=["Statistics for Data Science", "Big Data Analytics", "Data Mining"],
         interests="Data analytics, visualization, statistical modelling"),
    dict(name="Dr. Rohit Deshpande", qualifications="B.E., M.Tech, Ph.D.", designation="Associate Professor",
         post="Head of Department", department="Electronics and Communication Engineering",
         specialization="VLSI Design", teaching=13, industry=6,
         subjects=["VLSI Design", "Digital Electronics", "Embedded Systems"],
         interests="Low-power VLSI, embedded systems, IoT hardware"),
    dict(name="Dr. Lakshmi Pillai", qualifications="B.E., M.E., Ph.D.", designation="Professor",
         post="Head of Department", department="Electrical and Electronics Engineering",
         specialization="Power Systems", teaching=21, industry=3,
         subjects=["Power Systems", "Electrical Machines", "Control Systems"],
         interests="Smart grids, renewable integration, power quality"),
    dict(name="Mr. Karthik Subramanian", qualifications="B.E., M.E.", designation="Associate Professor",
         post="Head of Department", department="Mechanical Engineering",
         specialization="Thermal Engineering", teaching=12, industry=7,
         subjects=["Thermodynamics", "Heat Transfer", "Fluid Mechanics"],
         interests="Heat exchangers, energy efficiency, CFD"),
    dict(name="Dr. Farhan Sheikh", qualifications="B.E., M.Tech, Ph.D.", designation="Associate Professor",
         post="Head of Department", department="Civil Engineering",
         specialization="Structural Engineering", teaching=15, industry=5,
         subjects=["Structural Analysis", "Concrete Technology", "Surveying"],
         interests="Structural health monitoring, sustainable construction materials"),
    dict(name="Dr. Anita Joshi", qualifications="B.Com, MBA, Ph.D.", designation="Professor",
         post="Dean, School of Management", department="Management",
         specialization="Marketing", teaching=20, industry=8,
         subjects=["Marketing Management", "Organizational Behaviour", "Business Statistics"],
         interests="Consumer behaviour, brand strategy, digital marketing"),
    dict(name="Mr. Vikram Shetty", qualifications="BBA, MBA", designation="Lecturer",
         post="", department="Management",
         specialization="Finance", teaching=4, industry=3,
         subjects=["Financial Management", "Financial Accounting"],
         interests="Corporate finance, personal finance education"),
    dict(name="Dr. Rekha Bhat", qualifications="BCA, MCA, Ph.D.", designation="Associate Professor",
         post="Head of Department", department="Computer Applications",
         specialization="Database Systems", teaching=16, industry=3,
         subjects=["Database Systems", "Python Programming", "Software Testing"],
         interests="Database design, data modelling, query optimisation"),
    dict(name="Mr. Imran Qureshi", qualifications="BCA, MCA", designation="Lecturer",
         post="", department="Computer Applications",
         specialization="Web Development", teaching=3, industry=2,
         subjects=["Web Development", "Python Programming"],
         interests="Front-end development, web accessibility"),
]

_TITLES = {"dr.", "mr.", "ms.", "prof."}


def _extras(r: dict, n: int) -> dict:
    """Placeholder details so every profile section can be previewed."""
    parts = [p.lower() for p in r["name"].split() if p.lower() not in _TITLES]
    spec = r["specialization"].lower()
    rank = r["designation"]
    pubs = {"Professor": 3, "Associate Professor": 2, "Assistant Professor": 1}.get(rank, 0)
    return dict(
        slug="-".join(parts),
        email=".".join(parts) + "@college.example",        # reserved .example domain: cannot be real
        phone="",
        office=f"Block {'ABCD'[n % 4]}, Room {101 + n * 7} (sample)",
        consultation_hours="Mon & Wed, 2:00 PM - 4:00 PM (sample)",
        publications="\n".join(
            f"Sample publication {i}: illustrative paper on {spec} (placeholder entry)"
            for i in range(1, pubs + 1)),
        patents=f"Sample patent: illustrative filing in {spec} (placeholder entry)" if rank == "Professor" else "",
        projects="" if rank == "Lecturer" else f"Sample project: illustrative {spec} project (placeholder entry)",
        certifications=f"Sample certification: professional certificate in {spec} (placeholder entry)",
        achievements="Sample achievement: illustrative recognition (placeholder entry)" if r["post"] else "",
    )


FACULTY_SAMPLE = [
    {
        **{k: v for k, v in r.items() if k not in ("teaching", "industry", "interests")},
        "teaching_years": r["teaching"],
        "industry_years": r["industry"],
        "research_interests": r["interests"],
        **_extras(r, n),
        "is_sample": 1,
        "source": "Fictional prototype data",
        "last_updated": date.today().isoformat(),
    }
    for n, r in enumerate(_RAW)
]