"""course_catalogue.py - the course catalogue (single source of course data).

ALL fees and seat numbers here are ILLUSTRATIVE prototype figures, not verified
details of a real institution. Eligibility, procedure and documents are
illustrative defaults that the college must confirm. Replace with verified data.
Each course id must be linked to a department in faculty_seed.py / catalogue_seed.py.
"""
BSC_CORE = "B.Sc. Core Sciences"
BSC_APPLIED = "B.Sc. Applied Sciences"
BTECH_CORE = "B.Tech. Core Engineering"
BTECH_SPECIAL = "B.Tech. Specialized Engineering"
OTHER = "Other programmes"
GROUPS = [BSC_CORE, BSC_APPLIED, BTECH_CORE, BTECH_SPECIAL, OTHER]   # display order

PROCEDURE = [
    "Select this course on the website.",
    "Complete the online registration form (your selected course carries forward).",
    "Submit the registration for review by the college.",
    "Registration approval is granted through the college's own process.",
    "Complete the subsequent admission requirements (document verification, fee payment and other formalities).",
]
ADMISSION_UG = "Merit-based on Class 12 marks. Any entrance-test requirement is to be confirmed by the college."
ADMISSION_PG = "Based on bachelor's-degree marks. Any entrance-test or interview requirement is to be confirmed by the college."
DOCS_UG = [
    "Class 10 mark sheet", "Class 12 mark sheet or provisional certificate", "Transfer certificate",
    "Government photo ID", "Recent passport-size photographs",
    "Entrance score card and category or migration certificate, if applicable",
]
DOCS_PG = [
    "Bachelor's degree mark sheets and certificate (or provisional certificate)",
    "Class 10 and Class 12 mark sheets", "Transfer or migration certificate",
    "Government photo ID", "Recent passport-size photographs",
    "Entrance score card or interview call letter, if applicable",
]
DOCS_LATERAL = ["Diploma certificate and mark sheets (lateral entry only)"]
LATERAL = ("A relevant recognized engineering diploma may qualify for lateral entry into the second year, "
           "subject to the applicable rules. Lateral entry is not automatic; confirm with the admissions office.")
ENG_12 = ("Physics, Mathematics and one of Chemistry / Computer Science / a technical vocational subject "
          "(programme-specific subject to be confirmed by the college)")


def _semesters(years: int) -> str:
    if years == 4:
        return ("Semesters 1-2: foundation sciences, mathematics and engineering basics. "
                "Semesters 3-6: core subjects of the department with laboratories. "
                "Semesters 7-8: electives, internship and final-year project.")
    if years == 3:
        return ("Semesters 1-2: foundation papers and languages. "
                "Semesters 3-4: core papers with practicals. "
                "Semesters 5-6: advanced electives and project work.")
    return ("Semesters 1-2: core courses. Semester 3: electives and specialization. "
            "Semester 4: project, dissertation or internship.")


def _c(cid, name, group, category, years, fee, seats, overview, subjects, class12, careers, higher,
       degree=None, min_pct=45):
    pg = degree is not None
    btech = name.startswith("B.Tech")
    return {
        "id": cid, "name": name, "group": group, "category": category,
        "level": "Postgraduate" if pg else "Undergraduate",
        "years": years, "tuition": fee, "seats": seats,          # tuition = illustrative ANNUAL fee
        "overview": overview, "subjects": subjects,
        "class12": class12, "degree": degree, "min_pct": min_pct,
        "diploma": LATERAL if btech else None,
        "semesters": _semesters(years),
        "admission_mode": ADMISSION_PG if pg else ADMISSION_UG,
        "procedure": PROCEDURE,
        "documents": DOCS_PG if pg else DOCS_UG + (DOCS_LATERAL if btech else []),
        "careers": careers, "higher_studies": higher,
    }


COURSES = [
    # ------------------------------------------------ B.Tech. core engineering
    _c("btech-cse", "B.Tech Computer Science & Engineering", BTECH_CORE, "Engineering", 4, 150000, 120,
       "Covers programming, algorithms, systems and software engineering for building modern computing solutions.",
       ["Data Structures and Algorithms", "Operating Systems", "Database Systems", "Computer Networks", "Software Engineering"],
       ENG_12, ["Software engineer", "Systems or cloud engineer", "Data engineer", "Cybersecurity analyst"],
       ["M.Tech / M.E.", "MBA", "MS abroad or research programmes"]),
    _c("btech-it", "B.Tech Information Technology", BTECH_CORE, "Engineering", 4, 130000, 60,
       "Focuses on information systems, web and network technologies, and the software that runs organisations.",
       ["Programming and Data Structures", "Web Technologies", "Information Security", "Database Management", "Cloud Computing"],
       ENG_12, ["Web or full-stack developer", "IT consultant", "Network or security engineer", "QA or DevOps engineer"],
       ["M.Tech in IT / Computer Science", "MBA", "MS abroad"]),
    _c("btech-mech", "B.Tech Mechanical Engineering", BTECH_CORE, "Engineering", 4, 100000, 60,
       "Applies mechanics, thermal science and manufacturing to design and build machines and systems.",
       ["Engineering Mechanics", "Thermodynamics", "Fluid Mechanics", "Machine Design", "Manufacturing Processes"],
       ENG_12, ["Design engineer", "Manufacturing or production engineer", "Maintenance engineer", "Automotive or energy-sector roles"],
       ["M.Tech in Thermal / Design / Manufacturing", "MBA", "Public-sector technical services"]),
    _c("btech-civil", "B.Tech Civil Engineering", BTECH_CORE, "Engineering", 4, 90000, 60,
       "Teaches the planning, design and construction of buildings, roads, bridges and water systems.",
       ["Structural Analysis", "Surveying", "Concrete Technology", "Geotechnical Engineering", "Transportation Engineering"],
       ENG_12, ["Site or construction engineer", "Structural design engineer", "Infrastructure project coordinator", "Quantity surveyor"],
       ["M.Tech in Structural / Environmental / Transportation", "MBA in Construction Management", "Government technical services"]),
    _c("btech-eee", "B.Tech Electrical Engineering", BTECH_CORE, "Engineering", 4, 100000, 60,
       "Covers electrical machines, power systems, control and electronics for generating and using electrical energy.",
       ["Circuit Theory", "Electrical Machines", "Power Systems", "Control Systems", "Power Electronics"],
       ENG_12, ["Power-sector engineer", "Electrical design engineer", "Automation or control engineer", "Renewable energy engineer"],
       ["M.Tech in Power Systems / Control", "MBA", "MS abroad"]),
    _c("btech-ece", "B.Tech Electronics & Communication", BTECH_CORE, "Engineering", 4, 120000, 60,
       "Covers electronic circuits, communication systems, signal processing and embedded technologies.",
       ["Analog and Digital Electronics", "Signals and Systems", "Communication Systems", "VLSI Design", "Embedded Systems"],
       ENG_12, ["Electronics or VLSI engineer", "Telecom engineer", "Embedded systems developer", "IoT solutions engineer"],
       ["M.Tech in VLSI / Communication / Embedded Systems", "MBA", "MS abroad"]),
    _c("btech-chem", "B.Tech Chemical Engineering", BTECH_CORE, "Engineering", 4, 110000, 60,
       "Applies chemistry, physics and mathematics to design and run processes that turn raw materials into useful products.",
       ["Chemical Process Calculations", "Fluid Mechanics", "Heat and Mass Transfer", "Chemical Reaction Engineering", "Process Control"],
       "Physics, Chemistry and Mathematics",
       ["Process engineer", "Production or plant engineer", "Safety and environmental engineer", "Quality control engineer"],
       ["M.Tech in Chemical / Petroleum / Environmental Engineering", "MBA", "M.S. or Ph.D. research"]),
    # ------------------------------------------- B.Tech. specialized engineering
    _c("btech-engphy", "B.Tech Engineering Physics", BTECH_SPECIAL, "Engineering", 4, 100000, 30,
       "Combines core physics with engineering to prepare for work in electronics, optics, materials and instrumentation.",
       ["Mathematical Physics", "Quantum Mechanics", "Solid State Physics", "Optics and Photonics", "Electronic Devices"],
       ENG_12, ["R&D engineer", "Photonics or semiconductor engineer", "Instrumentation engineer", "Data analyst"],
       ["M.Tech or M.Sc. in Physics", "Ph.D.", "MS abroad"]),
    _c("btech-aero", "B.Tech Aeronautical Engineering", BTECH_SPECIAL, "Engineering", 4, 140000, 60,
       "Focuses on the design, aerodynamics, structures and maintenance of aircraft.",
       ["Aerodynamics", "Aircraft Structures", "Propulsion", "Flight Mechanics", "Aircraft Systems"],
       ENG_12, ["Aircraft design engineer", "Aircraft maintenance engineer (with licensing)", "Aviation-sector engineer", "Aerospace research roles"],
       ["M.Tech in Aerospace / Aerodynamics", "MS abroad", "MBA in Aviation Management"]),
    _c("btech-aerospace", "B.Tech Aerospace Engineering", BTECH_SPECIAL, "Engineering", 4, 150000, 30,
       "Covers aircraft, spacecraft and launch systems, including orbital mechanics and space propulsion.",
       ["Aerodynamics", "Orbital Mechanics", "Space Propulsion", "Spacecraft Structures", "Avionics"],
       ENG_12, ["Space systems engineer", "Propulsion engineer", "Satellite or avionics engineer", "Defence and aerospace research roles"],
       ["M.Tech in Aerospace / Space Technology", "MS abroad", "Ph.D."]),
    _c("btech-aiml", "B.Tech Artificial Intelligence & Machine Learning", BTECH_SPECIAL, "Engineering", 4, 160000, 60,
       "Builds skills in machine learning, deep learning and intelligent systems on a strong programming and mathematics base.",
       ["Machine Learning", "Deep Learning", "Natural Language Processing", "Computer Vision", "Probability and Statistics"],
       ENG_12, ["Machine learning engineer", "AI or data scientist", "Computer vision engineer", "AI product analyst"],
       ["M.Tech in AI / Data Science", "MS abroad", "Ph.D."]),
    _c("btech-biotech", "B.Tech Biotechnology Engineering", BTECH_SPECIAL, "Engineering", 4, 120000, 40,
       "Combines biology with engineering to develop biological products, processes and diagnostics.",
       ["Biochemistry", "Molecular Biology", "Genetic Engineering", "Bioprocess Engineering", "Bioinformatics"],
       "Physics, Chemistry and Mathematics or Biology",
       ["Bioprocess engineer", "Biopharma or quality-control roles", "Research associate", "Bioinformatics analyst"],
       ["M.Tech in Biotechnology", "M.S. or Ph.D.", "MBA in Biotech Management"]),
    _c("btech-robotics", "B.Tech Robotics and Automation Engineering", BTECH_SPECIAL, "Engineering", 4, 140000, 40,
       "Integrates mechanics, electronics and software to design robots and automated systems.",
       ["Robot Kinematics and Dynamics", "Control Systems", "Sensors and Actuators", "Embedded Systems", "Industrial Automation"],
       ENG_12, ["Robotics engineer", "Automation engineer", "Mechatronics engineer", "PLC or SCADA engineer"],
       ["M.Tech in Robotics / Mechatronics", "MS abroad", "Ph.D."]),
    # --------------------------------- existing programmes outside the revised list
    _c("btech-ds", "B.Tech Data Science", OTHER, "Engineering", 4, 150000, 60,
       "Teaches data engineering, statistics and machine learning to turn data into decisions.",
       ["Probability and Statistics", "Data Mining", "Big Data Analytics", "Machine Learning", "Data Visualization"],
       ENG_12, ["Data scientist", "Data analyst", "Business intelligence developer", "Data engineer"],
       ["M.Tech in Data Science / AI", "MBA in Business Analytics", "MS abroad"]),
    _c("bca", "BCA", OTHER, "Computing", 3, 70000, 120,
       "Builds a foundation in programming, databases and web development for software and IT-services careers.",
       ["Programming in C and Python", "Data Structures", "Database Management", "Web Development", "Computer Networks"],
       "Class 12 in any stream",
       ["Software developer", "Web developer", "IT support or systems analyst", "Software tester"],
       ["MCA", "MBA", "M.Sc. Computer Science"]),
    _c("mca", "MCA", OTHER, "Computing", 2, 100000, 60,
       "Advanced computing programme covering software development, data and systems for graduates from computing backgrounds.",
       ["Advanced Algorithms", "Software Architecture", "Cloud Computing", "Machine Learning", "Information Security"],
       None, ["Software engineer", "Application architect", "Data or cloud specialist", "IT project lead"],
       ["Ph.D.", "Professional certifications", "Research programmes"],
       degree="BCA or a relevant computer science / IT bachelor's degree; Mathematics requirement to be checked for the course",
       min_pct=50),
    _c("bba", "BBA", OTHER, "Management & Commerce", 3, 70000, 120,
       "Introduces management fundamentals including marketing, finance and human resources.",
       ["Principles of Management", "Marketing Management", "Financial Accounting", "Business Economics", "Organizational Behaviour"],
       "Class 12 in any stream",
       ["Management trainee", "Marketing or sales executive", "HR executive", "Entry-level business analyst"],
       ["MBA", "PGDM", "Professional certifications"]),
    _c("bcom", "B.Com", OTHER, "Management & Commerce", 3, 45000, 120,
       "Covers accounting, taxation, business law and economics for careers in finance and commerce.",
       ["Financial Accounting", "Business Law", "Cost Accounting", "Taxation", "Business Economics"],
       "An accepted stream; Commerce preferred (accepted streams to be confirmed by the college)",
       ["Accountant", "Tax or audit assistant", "Banking and finance executive", "Business operations roles"],
       ["M.Com", "MBA", "Professional courses such as CA / CMA / CS"], min_pct=40),
    _c("mba", "MBA", OTHER, "Management & Commerce", 2, 180000, 60,
       "Develops leadership and functional expertise in marketing, finance, operations and analytics.",
       ["Managerial Economics", "Marketing Management", "Corporate Finance", "Operations Management", "Business Analytics"],
       None, ["Management consultant", "Marketing or finance manager", "Operations manager", "Entrepreneur"],
       ["Ph.D. in Management", "Executive programmes", "Professional certifications"],
       degree="Any accepted bachelor's degree; entrance-test or interview requirements to be confirmed", min_pct=50),
    # ------------------------------------------------------- B.Sc. core sciences
    _c("bsc-phy", "B.Sc. Physics", BSC_CORE, "Science", 3, 45000, 40,
       "Studies matter, energy and the laws of nature with strong laboratory training.",
       ["Classical Mechanics", "Electromagnetism", "Quantum Physics", "Thermal Physics", "Optics"],
       "Physics and Mathematics",
       ["Research assistant", "Laboratory or instrumentation technician", "Data analyst", "Teaching (with further study)"],
       ["M.Sc. Physics", "M.Sc. Astrophysics / Materials Science", "Ph.D. and research programmes"]),
    _c("bsc-math", "B.Sc. Mathematics", BSC_CORE, "Science", 3, 40000, 40,
       "Develops rigorous mathematical reasoning across algebra, analysis, calculus and applied topics.",
       ["Calculus", "Linear Algebra", "Real Analysis", "Differential Equations", "Numerical Methods"],
       "Mathematics",
       ["Data or quantitative analyst", "Actuarial trainee (with exams)", "Banking and finance roles", "Teaching (with further study)"],
       ["M.Sc. Mathematics", "M.Sc. Statistics / Data Science", "Ph.D."]),
    _c("bsc-chem", "B.Sc. Chemistry", BSC_CORE, "Science", 3, 45000, 40,
       "Covers organic, inorganic and physical chemistry with extensive practical work.",
       ["Organic Chemistry", "Inorganic Chemistry", "Physical Chemistry", "Analytical Chemistry", "Spectroscopy"],
       "Chemistry and Physics, plus Mathematics or Biology",
       ["Quality-control chemist", "Laboratory analyst", "Pharmaceutical or chemical industry roles", "Research assistant"],
       ["M.Sc. Chemistry", "M.Sc. Analytical / Industrial Chemistry", "Ph.D."]),
    _c("bsc-bio", "B.Sc. Biology", BSC_CORE, "Science", 3, 45000, 40,
       "Surveys the life sciences from cells and genetics to ecology and human physiology.",
       ["Cell Biology", "Genetics", "Biochemistry", "Ecology", "Human Physiology"],
       "Biology and Chemistry",
       ["Laboratory technician", "Research assistant", "Healthcare or diagnostic support roles", "Science educator (with further study)"],
       ["M.Sc. Biology / Life Sciences", "M.Sc. Biotechnology", "Ph.D."]),
    _c("bsc-bot", "B.Sc. Botany", BSC_CORE, "Science", 3, 40000, 30,
       "Studies plant life, including structure, physiology, classification and plant biotechnology.",
       ["Plant Anatomy", "Plant Physiology", "Taxonomy of Angiosperms", "Plant Ecology", "Plant Biotechnology"],
       "Biology (Botany) and Chemistry",
       ["Plant-science or nursery roles", "Forestry and conservation support", "Agricultural research assistant", "Herbal and food-industry roles"],
       ["M.Sc. Botany", "M.Sc. Plant Biotechnology", "Ph.D."]),
    _c("bsc-zoo", "B.Sc. Zoology", BSC_CORE, "Science", 3, 40000, 30,
       "Studies animal life, from structure and physiology to behaviour, evolution and ecology.",
       ["Animal Diversity", "Animal Physiology", "Genetics and Evolution", "Developmental Biology", "Wildlife Biology"],
       "Biology (Zoology) and Chemistry",
       ["Wildlife or conservation assistant", "Laboratory technician", "Fisheries and animal-science roles", "Research assistant"],
       ["M.Sc. Zoology", "M.Sc. Wildlife Science", "Ph.D."]),
    _c("bsc-stat", "B.Sc. Statistics", BSC_CORE, "Science", 3, 45000, 30,
       "Teaches how to collect, analyse and interpret data using probability and statistical methods.",
       ["Probability Theory", "Statistical Inference", "Regression Analysis", "Sampling Techniques", "Statistical Computing"],
       "Mathematics",
       ["Statistician or data analyst", "Market and survey researcher", "Quality and operations analyst", "Actuarial trainee (with exams)"],
       ["M.Sc. Statistics", "M.Sc. Data Science", "Ph.D."]),
    # ----------------------------------------------------- B.Sc. applied sciences
    _c("bsc-cs", "B.Sc. Computer Science", BSC_APPLIED, "Computing", 3, 55000, 60,
       "Covers programming, algorithms, databases and computer systems with a strong theoretical base.",
       ["Programming in Python and Java", "Data Structures", "Database Systems", "Operating Systems", "Computer Networks"],
       "Mathematics or other specified subjects",
       ["Software developer", "Web developer", "Systems or IT support analyst", "Data analyst"],
       ["M.Sc. Computer Science", "MCA", "MBA"]),
    _c("bsc-biotech", "B.Sc. Biotechnology", BSC_APPLIED, "Science", 3, 65000, 40,
       "Applies biology and chemistry to develop products and processes in healthcare, agriculture and industry.",
       ["Biochemistry", "Molecular Biology", "Genetic Engineering", "Immunology", "Bioinformatics"],
       "Biology and Chemistry, with Physics or Mathematics",
       ["Biotech or pharma laboratory associate", "Quality-control analyst", "Research assistant", "Clinical research associate (with training)"],
       ["M.Sc. Biotechnology", "M.Tech Biotechnology (where eligible)", "Ph.D."]),
    _c("bsc-micro", "B.Sc. Microbiology", BSC_APPLIED, "Science", 3, 55000, 40,
       "Studies bacteria, viruses, fungi and other microorganisms and their role in health, food and the environment.",
       ["General Microbiology", "Microbial Genetics", "Immunology", "Medical Microbiology", "Industrial Microbiology"],
       "Biology and Chemistry",
       ["Laboratory microbiologist", "Quality assurance in food or pharma", "Clinical laboratory technician", "Research assistant"],
       ["M.Sc. Microbiology", "M.Sc. Biotechnology", "Ph.D."]),
    _c("bsc-env", "B.Sc. Environmental Science", BSC_APPLIED, "Science", 3, 50000, 30,
       "Examines environmental systems, pollution, conservation and sustainability through field and laboratory study.",
       ["Ecology and Ecosystems", "Environmental Chemistry", "Climate Change", "Waste and Water Management", "Environmental Impact Assessment"],
       "Any science stream (Physics, Chemistry, Biology or Mathematics)",
       ["Junior environmental consultant", "Pollution-control or EHS officer", "Sustainability analyst", "NGO and conservation roles"],
       ["M.Sc. Environmental Science", "MBA in Sustainability", "Ph.D."]),
    _c("bsc-ds", "B.Sc. Data Science", BSC_APPLIED, "Science", 3, 70000, 60,
       "Combines statistics, programming and machine learning to analyse and interpret data.",
       ["Probability and Statistics", "Python Programming", "Data Mining", "Machine Learning", "Data Visualization"],
       "Mathematics (Statistics or Computer Science preferred)",
       ["Data analyst", "Junior data scientist", "Business intelligence analyst", "Machine learning assistant"],
       ["M.Sc. Data Science", "M.Sc. Statistics", "MBA in Business Analytics"]),
]


# ---------------------------------------------------------------------------
# Structured Class 12 subject rules (used by the assistant's eligibility checker).
# Keep these in step with the readable 'class12' text of each course above.
#   all: subjects that are all required      one_of: groups where at least one is required
#   any_stream: no subject requirement       unverified: requirement not stored precisely
#   other_unverified: other subjects may be accepted but are not listed
# Postgraduate courses use bachelor's-degree rules, so their entry is empty.
# ---------------------------------------------------------------------------
_ENG = {"all": ["physics", "mathematics"], "one_of": [["chemistry", "computer science", "technical vocational subject"]]}
_LIFE = {"all": ["biology", "chemistry"]}
_REQ12 = {
    "btech-cse": _ENG, "btech-it": _ENG, "btech-mech": _ENG, "btech-civil": _ENG, "btech-eee": _ENG,
    "btech-ece": _ENG, "btech-engphy": _ENG, "btech-aero": _ENG, "btech-aerospace": _ENG,
    "btech-aiml": _ENG, "btech-robotics": _ENG, "btech-ds": _ENG,
    "btech-chem": {"all": ["physics", "chemistry", "mathematics"]},
    "btech-biotech": {"all": ["physics", "chemistry"], "one_of": [["mathematics", "biology"]]},
    "bca": {"any_stream": True}, "bba": {"any_stream": True},
    "bcom": {"unverified": "The accepted streams are to be confirmed by the college."},
    "mca": {}, "mba": {},
    "bsc-phy": {"all": ["physics", "mathematics"]},
    "bsc-math": {"all": ["mathematics"]},
    "bsc-chem": {"all": ["chemistry", "physics"], "one_of": [["mathematics", "biology"]]},
    "bsc-bio": _LIFE, "bsc-bot": _LIFE, "bsc-zoo": _LIFE, "bsc-micro": _LIFE,
    "bsc-stat": {"all": ["mathematics"]},
    "bsc-cs": {"all": ["mathematics"], "other_unverified": True},
    "bsc-biotech": {"all": ["biology", "chemistry"], "one_of": [["physics", "mathematics"]]},
    "bsc-env": {"one_of": [["physics", "chemistry", "biology", "mathematics"]]},
    "bsc-ds": {"all": ["mathematics"]},
}
for _course in COURSES:
    _course["req12"] = _REQ12[_course["id"]]       # KeyError here means a course has no rule yet