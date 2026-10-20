"""Patch ONLY the contact fields inside the COLLEGE dictionary of your own data.py.

Usage (from your project folder, after restoring your own data.py):
    python apply_contact_data.py            # edits data.py in place, saves data.py.bak first
Everything outside COLLEGE (ACHIEVEMENTS, ILLUSTRATIVE_ACHIEVEMENTS, COURSES, ...) is left untouched.
Safe to run twice.
"""
import re
import shutil
import sys

PATH = sys.argv[1] if len(sys.argv) > 1 else "data.py"
WANT = {
    "address": '"Knowledge Park, Sector 12, Bengaluru, Karnataka, India – 560001"',
    "phone": '"+91 98765 43210"',
    "email": '"info@yourcollege.example"',
    "admissions_phone": '"+91 91234 56780"',
    "admissions_email": '"admissions@yourcollege.example"',
    "office_hours": '"Monday–Saturday, 9:00 AM–5:00 PM; Sunday closed."',
}

raw = open(PATH, "rb").read().decode("utf-8")
nl = "\r\n" if "\r\n" in raw else "\n"
text = raw.replace("\r\n", "\n")

m = re.search(r"^COLLEGE\s*=\s*\{\n(.*?)^\}", text, re.S | re.M)
if not m:
    sys.exit("Could not find the COLLEGE = { ... } block in " + PATH + ". Nothing was changed.")
body = m.group(1)

for key, value in WANT.items():
    line = f'    "{key}": {value},'
    pattern = re.compile(rf'^[ \t]*"{key}"\s*:.*$', re.M)
    if pattern.search(body):
        body = pattern.sub(lambda _: line, body, count=1)
    else:
        body += line + "\n"
note = "    # SAMPLE contact details for the prototype. Placeholders, not a real college's details.\n"
if "SAMPLE contact details" not in body:
    body = body.replace('    "address"', note + '    "address"', 1)

new = text[:m.start(1)] + body + text[m.end(1):]
if new == text:
    print("Already up to date. Nothing changed.")
else:
    shutil.copyfile(PATH, PATH + ".bak")
    open(PATH, "wb").write(new.replace("\n", nl).encode("utf-8"))
    print(f"Updated COLLEGE contact fields in {PATH} (backup: {PATH}.bak).")
