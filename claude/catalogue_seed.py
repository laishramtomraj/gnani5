"""catalogue_seed.py - departments, course links and FICTIONAL faculty for the revised catalogue.

Adds only NEW records. Existing departments and faculty (faculty_seed.py) are not changed.
All names, qualifications and contact details are invented sample data.
"""
from datetime import date

from faculty_seed import FACULTY_SAMPLE, _extras

# An existing department that also teaches a newly added course.
EXTRA_COURSE_LINKS = {"Artificial Intelligence and Data Science": ["bsc-ds"]}

# New departments (appended after the existing ones) and the course ids they teach.
EXTRA_DEPARTMENTS = [
    ("Physics", ["bsc-phy", "btech-engphy"]),
    ("Mathematics and Statistics", ["bsc-math", "bsc-stat"]),
    ("Chemistry", ["bsc-chem"]),
    ("Life Sciences", ["bsc-bio", "bsc-bot", "bsc-zoo", "bsc-micro", "bsc-env"]),
    ("Biotechnology", ["bsc-biotech", "btech-biotech"]),
    ("Chemical Engineering", ["btech-chem"]),
    ("Aerospace Engineering", ["btech-aero", "btech-aerospace"]),
    ("Robotics and Automation", ["btech-robotics"]),
]

_RAW = [
    dict(name="Dr. Harish Venkatesh", qualifications="B.Sc., M.Sc., Ph.D.", designation="Professor",
         post="Head of Department", department="Physics", specialization="Condensed Matter Physics",
         teaching=20, industry=1, subjects=["Quantum Mechanics", "Solid State Physics", "Mathematical Physics"],
         interests="Thin films, nanomaterials, semiconductor physics"),
    dict(name="Ms. Swati Bhandari", qualifications="B.Sc., M.Sc.", designation="Assistant Professor",
         post="", department="Physics", specialization="Optics and Photonics",
         teaching=5, industry=0, subjects=["Optics", "Classical Mechanics", "Electronic Devices"],
         interests="Fibre optics, laser applications"),
    dict(name="Dr. Padma Krishnan", qualifications="B.Sc., M.Sc., Ph.D.", designation="Professor",
         post="Head of Department", department="Mathematics and Statistics", specialization="Applied Mathematics",
         teaching=23, industry=0, subjects=["Calculus", "Differential Equations", "Numerical Methods"],
         interests="Numerical analysis, mathematical modelling"),
    dict(name="Mr. Naveen Gowda", qualifications="B.Sc., M.Sc.", designation="Assistant Professor",
         post="", department="Mathematics and Statistics", specialization="Statistical Inference",
         teaching=6, industry=1, subjects=["Probability Theory", "Regression Analysis", "Statistical Computing"],
         interests="Applied statistics, survey methods"),
    dict(name="Dr. Shalini Mukherjee", qualifications="B.Sc., M.Sc., Ph.D.", designation="Associate Professor",
         post="Head of Department", department="Chemistry", specialization="Organic Chemistry",
         teaching=14, industry=2, subjects=["Organic Chemistry", "Spectroscopy", "Analytical Chemistry"],
         interests="Green synthesis, natural products"),
    dict(name="Dr. Ramesh Babu", qualifications="B.Sc., M.Sc., Ph.D.", designation="Professor",
         post="Head of Department", department="Life Sciences", specialization="Plant Sciences",
         teaching=21, industry=0,
         subjects=["Plant Physiology", "Ecology and Ecosystems", "Environmental Impact Assessment"],
         interests="Plant ecology, conservation, environmental monitoring"),
    dict(name="Ms. Fathima Rahman", qualifications="B.Sc., M.Sc.", designation="Assistant Professor",
         post="", department="Life Sciences", specialization="Microbiology",
         teaching=5, industry=1, subjects=["General Microbiology", "Immunology", "Cell Biology"],
         interests="Medical and industrial microbiology"),
    dict(name="Dr. Neha Agarwal", qualifications="B.Tech, M.Tech, Ph.D.", designation="Associate Professor",
         post="Head of Department", department="Biotechnology", specialization="Genetic Engineering",
         teaching=13, industry=3, subjects=["Molecular Biology", "Genetic Engineering", "Bioinformatics"],
         interests="Genetic engineering, bioinformatics, diagnostics"),
    dict(name="Dr. Suresh Naidu", qualifications="B.Tech, M.Tech, Ph.D.", designation="Professor",
         post="Head of Department", department="Chemical Engineering", specialization="Process Control",
         teaching=22, industry=6,
         subjects=["Process Control", "Heat and Mass Transfer", "Chemical Reaction Engineering"],
         interests="Process control, process safety, energy efficiency"),
    dict(name="Dr. Vivek Chandran", qualifications="B.Tech, M.Tech, Ph.D.", designation="Professor",
         post="Head of Department", department="Aerospace Engineering", specialization="Aerodynamics",
         teaching=20, industry=5, subjects=["Aerodynamics", "Flight Mechanics", "Aircraft Structures"],
         interests="CFD, aerodynamic design, flight dynamics"),
    dict(name="Mr. Tarun Bose", qualifications="B.Tech, M.Tech", designation="Assistant Professor",
         post="", department="Aerospace Engineering", specialization="Propulsion",
         teaching=6, industry=3, subjects=["Propulsion", "Space Propulsion", "Orbital Mechanics"],
         interests="Gas turbines, rocket propulsion"),
    dict(name="Dr. Meenakshi Sundaram", qualifications="B.E., M.E., Ph.D.", designation="Associate Professor",
         post="Head of Department", department="Robotics and Automation", specialization="Robot Control Systems",
         teaching=15, industry=4,
         subjects=["Robot Kinematics and Dynamics", "Control Systems", "Industrial Automation"],
         interests="Robot control, sensors, industrial automation"),
]

EXTRA_FACULTY = [
    {
        **{k: v for k, v in r.items() if k not in ("teaching", "industry", "interests")},
        "teaching_years": r["teaching"],
        "industry_years": r["industry"],
        "research_interests": r["interests"],
        **_extras(r, len(FACULTY_SAMPLE) + n),
        "is_sample": 1,
        "source": "Fictional prototype data",
        "last_updated": date.today().isoformat(),
    }
    for n, r in enumerate(_RAW)
]