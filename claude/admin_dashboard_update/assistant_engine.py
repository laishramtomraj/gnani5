"""assistant_engine.py - College Admission Assistant (database-grounded, rule-based).

No AI text-generation model is used. Every answer is built from the course catalogue
(course_catalogue.py) and the faculty database (faculty_db.py). If something is not stored,
the assistant says so instead of guessing. Languages: English, Hindi (Devanagari) and Hinglish.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from course_catalogue import COURSES, DOCS_PG, DOCS_UG, GROUPS, PROCEDURE
from data import COLLEGE, format_inr



@dataclass
class Reply:
    text: str
    link: tuple[str, str] | None = None      # (button label, page path)
    lang: str = "en"
    redact: bool = False                     # True: do not keep the user's message in the chat history


# =============================================================== text tables
def _t(en, hi, hn):
    return {"en": en, "hi": hi, "hn": hn}


S = {
    "greet": _t(
        "Hi! I'm the College Admission Assistant. I can help with courses, fees, seats, eligibility, faculty and the registration process. What would you like to know?",
        "नमस्ते! मैं कॉलेज एडमिशन असिस्टेंट हूँ। मैं कोर्स, फीस, सीटें, पात्रता, फैकल्टी और रजिस्ट्रेशन प्रक्रिया में आपकी मदद कर सकता हूँ। आप क्या जानना चाहते हैं?",
        "Namaste! Main College Admission Assistant hoon. Main courses, fees, seats, eligibility, faculty aur registration process mein aapki madad kar sakta hoon. Aap kya jaanna chahte hain?"),
    "not_verified": _t(
        "I don't have verified information for that. Please contact the college admissions office.",
        "मेरे पास इसकी सत्यापित जानकारी नहीं है। कृपया कॉलेज प्रवेश कार्यालय (admissions office) से संपर्क करें।",
        "Mere paas iski verified jaankari nahi hai. Kripya college admissions office se sampark karein."),
    "disclaimer": _t(
        "Note: This is illustrative prototype data.",
        "Note: This is illustrative prototype data. (नोट: यह केवल उदाहरण के लिए बनाया गया प्रोटोटाइप डेटा है।)",
        "Note: This is illustrative prototype data. (Yeh sirf udaharan ke liye banaya gaya prototype data hai.)"),
    "cannot_advise": _t(
        "I can't give legal, visa, immigration or loan advice. Please consult a qualified advisor or the college admissions office.",
        "मैं कानूनी, वीज़ा, इमिग्रेशन या लोन से जुड़ी सलाह नहीं दे सकता। कृपया किसी योग्य सलाहकार या कॉलेज प्रवेश कार्यालय से संपर्क करें।",
        "Main legal, visa, immigration ya loan ki salah nahi de sakta. Kripya kisi qualified advisor ya college admissions office se baat karein."),
    "privacy": _t(
        "Please don't share sensitive details such as ID numbers, passwords or bank information here. I don't need them, and I haven't kept what you sent.",
        "कृपया यहाँ आईडी नंबर, पासवर्ड या बैंक जैसी संवेदनशील जानकारी साझा न करें। इसकी मुझे ज़रूरत नहीं है, और मैंने इसे सहेजा नहीं है।",
        "Kripya yahan ID number, password ya bank jaisi sensitive jaankari share na karein. Iski mujhe zaroorat nahi hai, aur maine ise save nahi kiya hai."),
    "found_courses": _t("Here are the matching courses ({n}):", "मेल खाने वाले कोर्स ({n}):", "Matching courses ({n}):"),
    "all_courses": _t("These are the courses in the database ({n}), by category:",
                      "डेटाबेस में उपलब्ध कोर्स ({n}), श्रेणी के अनुसार:",
                      "Database mein ye courses hain ({n}), category ke hisaab se:"),
    "no_match": _t("No course in the database matches those filters.",
                   "इन फ़िल्टर से मेल खाता कोई कोर्स डेटाबेस में नहीं मिला।",
                   "In filters se match karta koi course database mein nahi mila."),
    "which_one": _t("Which one do you mean?", "आपका मतलब कौन सा है?", "Aapka matlab kaun sa hai?"),
    "closest": _t("I couldn't find that exact course in the database. The closest courses are:",
                  "यह कोर्स डेटाबेस में नहीं मिला। सबसे मिलते-जुलते कोर्स:",
                  "Yeh course database mein nahi mila. Sabse milte-julte courses:"),
    "ask_budget": _t("What is your budget per year (for example ₹1.5 lakh)?",
                     "आपका सालाना बजट कितना है (जैसे ₹1.5 लाख)?",
                     "Aapka saalana budget kitna hai (jaise ₹1.5 lakh)?"),
    "ask_course": _t("Which course are you asking about?", "आप किस कोर्स के बारे में पूछ रहे हैं?",
                     "Aap kis course ke baare mein pooch rahe hain?"),
    "ask_dept": _t("Which department's faculty would you like to see (for example Physics or Computer Science and Engineering)?",
                   "आप किस विभाग की फैकल्टी देखना चाहते हैं (जैसे Physics या Computer Science and Engineering)?",
                   "Aap kis department ki faculty dekhna chahte hain (jaise Physics ya Computer Science and Engineering)?"),
    "ask_profile": _t("To check this, please share your {missing}.",
                      "यह जाँचने के लिए कृपया अपना {missing} बताएं।",
                      "Yeh check karne ke liye kripya apna {missing} batayein."),
    "m_subjects": _t("Class 12 subjects (for example PCM)", "कक्षा 12 के विषय (जैसे PCM)", "Class 12 ke subjects (jaise PCM)"),
    "m_percent": _t("percentage", "प्रतिशत", "percentage"),
    "m_qual": _t("qualification level (Class 12 or bachelor's degree)", "योग्यता स्तर (कक्षा 12 या स्नातक डिग्री)",
                 "qualification level (Class 12 ya bachelor's degree)"),
    "m_degree": _t("bachelor's degree name", "स्नातक डिग्री का नाम", "bachelor's degree ka naam"),
    "and": _t(" and ", " और ", " aur "),
    "elig_meets": _t("Based on what you shared, you meet the stored criteria for {course}.",
                     "आपकी दी गई जानकारी के अनुसार आप {course} के संग्रहीत मानदंड पूरे करते हैं।",
                     "Aapki di gayi jaankari ke hisaab se aap {course} ke stored criteria poore karte hain."),
    "elig_not": _t("Based on what you shared, you do not meet the stored criteria for {course}.",
                   "आपकी दी गई जानकारी के अनुसार आप {course} के संग्रहीत मानदंड पूरे नहीं करते।",
                   "Aapki di gayi jaankari ke hisaab se aap {course} ke stored criteria poore nahi karte."),
    "elig_insuf": _t("I can't reach a conclusion for {course} yet because some details are missing.",
                     "कुछ जानकारी कम होने के कारण मैं अभी {course} के बारे में निष्कर्ष नहीं निकाल सकता।",
                     "Kuch jaankari kam hone ki wajah se main abhi {course} ke baare mein nishkarsh nahi nikal sakta."),
    "lbl_met": _t("Met", "पूरा हुआ", "Poora hua"),
    "lbl_unmet": _t("Not met", "पूरा नहीं हुआ", "Poora nahi hua"),
    "lbl_unver": _t("Not yet verified", "अभी सत्यापित नहीं", "Abhi verify nahi hua"),
    "subj_ok": _t("Required subjects present: {s}", "आवश्यक विषय मौजूद: {s}", "Zaroori subjects maujood: {s}"),
    "subj_missing": _t("Missing required subject(s): {s}", "आवश्यक विषय नहीं हैं: {s}", "Zaroori subject(s) nahi hain: {s}"),
    "subj_oneof": _t("At least one of these is needed: {s}", "इनमें से कम से कम एक चाहिए: {s}",
                     "Inmein se kam se kam ek chahiye: {s}"),
    "subj_unknown": _t("Your Class 12 subjects were not provided", "आपके कक्षा 12 के विषय नहीं बताए गए",
                       "Aapke Class 12 subjects nahi bataye gaye"),
    "other_subj": _t("Other subjects may also be accepted, but that list is not stored",
                     "अन्य विषय भी स्वीकार हो सकते हैं, पर उनकी सूची संग्रहीत नहीं है",
                     "Doosre subjects bhi accepted ho sakte hain, par unki list stored nahi hai"),
    "any_stream": _t("Any Class 12 stream is accepted", "कक्षा 12 की कोई भी स्ट्रीम मान्य है",
                     "Class 12 ki koi bhi stream accepted hai"),
    "stream_unver": _t("The accepted streams are to be confirmed by the college",
                       "मान्य स्ट्रीम की पुष्टि कॉलेज द्वारा की जाएगी", "Accepted streams ki confirmation college karega"),
    "pct_ok": _t("Marks {p}% (minimum {m}%)", "अंक {p}% (न्यूनतम {m}%)", "Marks {p}% (minimum {m}%)"),
    "pct_low": _t("Marks {p}% are below the minimum {m}%", "अंक {p}% न्यूनतम {m}% से कम हैं",
                  "Marks {p}% minimum {m}% se kam hain"),
    "pct_unknown": _t("Your percentage was not provided", "आपका प्रतिशत नहीं बताया गया", "Aapka percentage nahi bataya gaya"),
    "pg_need_degree": _t("This is a postgraduate course and needs a bachelor's degree: {d}",
                         "यह स्नातकोत्तर कोर्स है और इसके लिए स्नातक डिग्री चाहिए: {d}",
                         "Yeh postgraduate course hai aur iske liye bachelor's degree chahiye: {d}"),
    "pg_degree_held": _t("You have a bachelor's degree", "आपके पास स्नातक डिग्री है", "Aapke paas bachelor's degree hai"),
    "degree_accepted": _t("Which bachelor's degrees are accepted is to be confirmed by the college",
                          "कौन सी स्नातक डिग्री मान्य है, इसकी पुष्टि कॉलेज करेगा",
                          "Kaun si bachelor's degree accepted hai, iski confirmation college karega"),
    "mca_ok": _t("Your degree ({g}) fits the stored requirement", "आपकी डिग्री ({g}) संग्रहीत शर्त से मेल खाती है",
                 "Aapki degree ({g}) stored requirement se match karti hai"),
    "mca_bad": _t("Stored requirement: {d}. Your degree ({g}) is not listed",
                  "संग्रहीत शर्त: {d}। आपकी डिग्री ({g}) सूची में नहीं है",
                  "Stored requirement: {d}. Aapki degree ({g}) listed nahi hai"),
    "mca_unknown": _t("Which bachelor's degree you hold was not provided",
                      "आपके पास कौन सी स्नातक डिग्री है, यह नहीं बताया गया",
                      "Aapke paas kaun si bachelor's degree hai, yeh nahi bataya gaya"),
    "mca_math": _t("The Mathematics requirement is to be checked for this course",
                   "इस कोर्स के लिए गणित की शर्त की जाँच होनी बाकी है",
                   "Is course ke liye Mathematics requirement check hona baaki hai"),
    "req_missing": _t("The Class 12 subject requirement for this course is not stored",
                      "इस कोर्स के लिए कक्षा 12 के विषयों की शर्त संग्रहीत नहीं है",
                      "Is course ke liye Class 12 subjects ki requirement stored nahi hai"),
    "qual_unknown": _t("Your qualification level was not provided", "आपका योग्यता स्तर नहीं बताया गया",
                       "Aapka qualification level nahi bataya gaya"),
    "qual_ug": _t("Your qualification level doesn't match this undergraduate course's Class 12 entry; the college must confirm",
                  "आपका योग्यता स्तर इस स्नातक कोर्स की कक्षा 12 प्रवेश शर्त से मेल नहीं खाता; कॉलेज की पुष्टि ज़रूरी है",
                  "Aapka qualification level is undergraduate course ki Class 12 entry se match nahi karta; college ki confirmation zaroori hai"),
    "lateral_text": _t(
        "A relevant recognized engineering diploma may qualify for lateral entry into the second year, subject to the applicable rules. Lateral entry is not automatic; confirm with the admissions office.",
        "संबंधित मान्यता प्राप्त इंजीनियरिंग डिप्लोमा से लागू नियमों के अनुसार दूसरे वर्ष में लेटरल एंट्री मिल सकती है। लेटरल एंट्री स्वतः नहीं मिलती; प्रवेश कार्यालय से पुष्टि करें।",
        "Relevant recognized engineering diploma se lagoo niyamon ke anusaar doosre saal mein lateral entry mil sakti hai. Lateral entry apne-aap nahi milti; admissions office se confirm karein."),
    "diploma_lateral": _t("Diploma holders: {t}", "डिप्लोमा धारक: {t}", "Diploma holders: {t}"),
    "diploma_none": _t("No diploma pathway is listed for this course", "इस कोर्स के लिए कोई डिप्लोमा मार्ग सूचीबद्ध नहीं है",
                       "Is course ke liye koi diploma pathway listed nahi hai"),
    "confirm_extra": _t(
        "The programme-specific subject, any entrance test and final eligibility are confirmed by the college. This is not a guarantee of admission.",
        "कार्यक्रम-विशिष्ट विषय, प्रवेश परीक्षा (यदि हो) और अंतिम पात्रता की पुष्टि कॉलेज करता है। यह प्रवेश की गारंटी नहीं है।",
        "Programme-specific subject, entrance test (agar ho) aur final eligibility college confirm karta hai. Yeh admission ki guarantee nahi hai."),
    "confirm_gen": _t(
        "Final eligibility and any entrance test are confirmed by the college. This is not a guarantee of admission.",
        "अंतिम पात्रता और प्रवेश परीक्षा (यदि हो) की पुष्टि कॉलेज करता है। यह प्रवेश की गारंटी नहीं है।",
        "Final eligibility aur entrance test (agar ho) college confirm karta hai. Yeh admission ki guarantee nahi hai."),
    "d_fee": _t("{name}: annual tuition is {annual} (total tuition for {n} years: {total}).",
                "{name}: वार्षिक ट्यूशन फीस {annual} है ({n} वर्ष की कुल ट्यूशन फीस: {total})।",
                "{name}: annual tuition fee {annual} hai ({n} saal ki total tuition fee: {total})."),
    "d_seats": _t("{name} lists {seats} sample seats (an illustrative intake target, not live availability).",
                  "{name} में {seats} नमूना सीटें सूचीबद्ध हैं (यह उदाहरण के लिए क्षमता है, वर्तमान उपलब्धता नहीं)।",
                  "{name} mein {seats} sample seats listed hain (yeh illustrative intake hai, live availability nahi)."),
    "d_duration": _t("{name} is a {n}-year programme ({sem} semesters).", "{name} {n} वर्ष का कोर्स है ({sem} सेमेस्टर)।",
                     "{name} {n} saal ka course hai ({sem} semesters)."),
    "d_elig": _t("Here are the stored eligibility requirements for {name}.", "{name} के लिए संग्रहीत पात्रता शर्तें:",
                 "{name} ke liye stored eligibility requirements:"),
    "d_docs": _t("Here are the documents stored for {name}.", "{name} के लिए संग्रहीत दस्तावेज़:", "{name} ke liye stored documents:"),
    "d_careers": _t("Here are the career and higher-study options stored for {name}.",
                    "{name} के लिए संग्रहीत करियर और उच्च अध्ययन विकल्प:", "{name} ke liye stored career aur higher-study options:"),
    "d_subjects": _t("Here are the major subjects and semester structure stored for {name}.",
                     "{name} के मुख्य विषय और सेमेस्टर संरचना:", "{name} ke major subjects aur semester structure:"),
    "d_dept": _t("{name} is linked to the {dept} department.", "{name} {dept} विभाग से जुड़ा है।",
                 "{name} {dept} department se juda hai."),
    "d_summary": _t("Here are the stored details for {name}.", "{name} की संग्रहीत जानकारी:", "{name} ki stored jaankari:"),
    "fee_excl": _t("Hostel, transport, examination, registration and other charges are excluded; fee increases may apply.",
                   "हॉस्टल, परिवहन, परीक्षा, रजिस्ट्रेशन और अन्य शुल्क शामिल नहीं हैं; फीस बढ़ सकती है।",
                   "Hostel, transport, exam, registration aur doosre charges shamil nahi hain; fees badh sakti hai."),
    "fee_increase": _t("Fee increases may apply.", "फीस बढ़ सकती है।", "Fees badh sakti hai."),
    "excl_amounts": _t("I don't have verified amounts for those charges. Please contact the college admissions office.",
                       "इन शुल्कों की सत्यापित राशि मेरे पास नहीं है। कृपया कॉलेज प्रवेश कार्यालय से संपर्क करें।",
                       "In charges ki verified amounts mere paas nahi hain. Kripya college admissions office se sampark karein."),
    "excl_intro": _t("The tuition figures do not include these charges:", "ट्यूशन फीस में ये शुल्क शामिल नहीं हैं:",
                     "Tuition fees mein ye charges shamil nahi hain:"),
    "excl_items": _t("hostel; transport; examination; registration; other charges", "हॉस्टल; परिवहन; परीक्षा; रजिस्ट्रेशन; अन्य शुल्क",
                     "hostel; transport; exam; registration; doosre charges"),
    "op_lt": _t("below", "से कम", "se kam"),
    "op_gt": _t("above", "से अधिक", "se zyada"),
    "n_stream": _t("Next step: name a course and share your percentage, and I'll check your eligibility.",
                   "अगला कदम: कोई कोर्स और अपना प्रतिशत बताएं, मैं आपकी पात्रता जाँच दूँगा।",
                   "Agla step: koi course aur apna percentage batayein, main aapki eligibility check karunga."),
    "no_action": _t("I can't approve, reject or check applications, and I can't submit registrations for you. Registration approval is handled only by the college.",
                    "मैं आवेदन स्वीकृत, अस्वीकृत या जाँच नहीं कर सकता, और आपकी ओर से रजिस्ट्रेशन जमा नहीं कर सकता। रजिस्ट्रेशन की स्वीकृति केवल कॉलेज द्वारा की जाती है।",
                    "Main applications approve, reject ya check nahi kar sakta, aur aapki taraf se registration submit nahi kar sakta. Registration approval sirf college karta hai."),
    "cmp_intro": _t("Here is a comparison of {names}:", "{names} की तुलना:", "{names} ki comparison:"),
    "cmp_cheapest": _t("Lowest annual tuition: {name} ({fee}).", "सबसे कम वार्षिक ट्यूशन फीस: {name} ({fee})।",
                       "Sabse kam annual tuition: {name} ({fee})."),
    "cmp_need_two": _t("Please name at least two courses to compare.", "तुलना के लिए कृपया कम से कम दो कोर्स बताएं।",
                       "Comparison ke liye kripya kam se kam do courses batayein."),
    "filter_intro": _t("{n} course(s) have {basis} {op} {amount}:", "{n} कोर्स की {basis} {amount} {op}:",
                       "{n} course(s) ki {basis} {amount} {op}:"),
    "basis_annual": _t("annual tuition", "वार्षिक ट्यूशन फीस", "annual tuition fee"),
    "basis_total": _t("total tuition", "कुल ट्यूशन फीस", "total tuition fee"),
    "op_le": _t("up to", "तक", "tak"),
    "op_ge": _t("of at least", "या उससे अधिक", "ya usse zyada"),
    "stream_intro": _t("Based on the subjects you shared ({subs}), these undergraduate courses match the stored subject criteria ({n}):",
                       "आपके बताए विषयों ({subs}) के आधार पर ये स्नातक कोर्स संग्रहीत विषय-मानदंड से मेल खाते हैं ({n}):",
                       "Aapke bataye subjects ({subs}) ke hisaab se ye undergraduate courses stored subject criteria se match karte hain ({n}):"),
    "stream_check": _t("Needs more information: {names}", "अधिक जानकारी चाहिए: {names}", "Aur jaankari chahiye: {names}"),
    "stream_none": _t("No undergraduate course in the database matches those subjects.",
                      "इन विषयों से मेल खाता कोई स्नातक कोर्स डेटाबेस में नहीं मिला।",
                      "In subjects se match karta koi undergraduate course database mein nahi mila."),
    "stream_note": _t("This checks subject criteria only. Entrance tests and final eligibility are confirmed by the college.",
                      "यह केवल विषय-मानदंड जाँचता है। प्रवेश परीक्षा और अंतिम पात्रता की पुष्टि कॉलेज करता है।",
                      "Yeh sirf subject criteria check karta hai. Entrance test aur final eligibility college confirm karta hai."),
    "adm_intro": _t(
        "Registration must be submitted before admission can proceed, and admission is subject to the college's approval process. Here is the stored process:",
        "प्रवेश आगे बढ़ने से पहले रजिस्ट्रेशन जमा करना ज़रूरी है, और प्रवेश कॉलेज की स्वीकृति प्रक्रिया पर निर्भर है। संग्रहीत प्रक्रिया:",
        "Admission aage badhne se pehle registration submit karna zaroori hai, aur admission college ki approval process par nirbhar hai. Stored process:"),
    "adm_where": _t(
        "You can register on the Admissions page of this website. I can't check or confirm the status of a submitted registration.",
        "आप इस वेबसाइट के Admissions पेज पर रजिस्ट्रेशन कर सकते हैं। मैं जमा किए गए रजिस्ट्रेशन की स्थिति नहीं देख या पुष्ट कर सकता।",
        "Aap is website ke Admissions page par registration kar sakte hain. Main submit kiye gaye registration ka status check ya confirm nahi kar sakta."),
    "docs_ug": _t("Documents for undergraduate courses", "स्नातक कोर्स के दस्तावेज़", "Undergraduate courses ke documents"),
    "docs_pg": _t("Documents for postgraduate courses", "स्नातकोत्तर कोर्स के दस्तावेज़", "Postgraduate courses ke documents"),
    "lateral_general": _t("For B.Tech programmes, diploma holders: {t}", "B.Tech कोर्स के लिए, डिप्लोमा धारक: {t}",
                          "B.Tech courses ke liye, diploma holders: {t}"),
    "fac_found": _t("Faculty found ({n}):", "फैकल्टी ({n}):", "Faculty mili ({n}):"),
    "fac_dept_intro": _t("Faculty of the {dept} department ({n}):", "{dept} विभाग की फैकल्टी ({n}):",
                         "{dept} department ki faculty ({n}):"),
    "fac_teaches": _t("Faculty teaching {subj} ({n}):", "{subj} पढ़ाने वाली फैकल्टी ({n}):", "{subj} padhane wali faculty ({n}):"),
    "fac_head": _t("{name} is listed as {post} of the {dept} department.", "{name} {dept} विभाग के {post} के रूप में सूचीबद्ध हैं।",
                   "{name} {dept} department ke {post} ke roop mein listed hain."),
    "fac_no_head": _t("No Head of Department is listed for {dept}.", "{dept} के लिए कोई विभागाध्यक्ष सूचीबद्ध नहीं है।",
                      "{dept} ke liye koi Head of Department listed nahi hai."),
    "fac_none": _t("I couldn't find matching faculty records.", "मेल खाते फैकल्टी रिकॉर्ड नहीं मिले।",
                   "Matching faculty records nahi mile."),
    "fac_unavailable": _t("I couldn't retrieve the faculty records right now, so I can't verify that.",
                          "मैं अभी फैकल्टी रिकॉर्ड प्राप्त नहीं कर सका, इसलिए इसकी पुष्टि नहीं कर सकता।",
                          "Main abhi faculty records nahi nikal saka, isliye iski verification nahi kar sakta."),
    "fac_more": _t("...and {n} more. Open the faculty directory for all profiles.",
                   "...और {n} अन्य। सभी प्रोफ़ाइल के लिए फैकल्टी डायरेक्टरी खोलें।",
                   "...aur {n} aur. Saari profiles ke liye faculty directory kholein."),
    "n_explore": _t("Next step: browse the courses.", "अगला कदम: कोर्स देखें।", "Agla step: courses dekhein."),
    "n_course": _t("Next step: open the Courses page and select this course to see its full details.",
                   "अगला कदम: पूरी जानकारी के लिए Courses पेज खोलकर यह कोर्स चुनें।",
                   "Agla step: poori jaankari ke liye Courses page kholkar yeh course chunein."),
    "n_elig": _t("Next step: tell me your Class 12 subjects and percentage and I'll check eligibility.",
                 "अगला कदम: अपने कक्षा 12 के विषय और प्रतिशत बताएं, मैं पात्रता जाँच दूँगा।",
                 "Agla step: apne Class 12 subjects aur percentage batayein, main eligibility check karunga."),
    "n_apply": _t("Next step: begin your registration.", "अगला कदम: अपना रजिस्ट्रेशन शुरू करें।", "Agla step: apna registration shuru karein."),
    "n_compare": _t("Next step: ask me to compare any two of these courses.", "अगला कदम: इनमें से किन्हीं दो कोर्स की तुलना के लिए पूछें।",
                    "Agla step: inmein se kisi do courses ki comparison ke liye poochhein."),
    "n_contact": _t("Next step: contact the college admissions office.", "अगला कदम: कॉलेज प्रवेश कार्यालय से संपर्क करें।",
                    "Agla step: college admissions office se sampark karein."),
    "n_faculty": _t("Next step: open the faculty directory for full profiles.", "अगला कदम: पूरी प्रोफ़ाइल के लिए फैकल्टी डायरेक्टरी खोलें।",
                    "Agla step: poori profiles ke liye faculty directory kholein."),
}

LBL = {
    "en": dict(duration="Duration", annual="Annual tuition", total="Total tuition ({n} years)", seats="Seats (sample intake)",
               minmarks="Minimum marks", class12="Class 12 subjects", degree="Bachelor's degree", dept="Department", docs_label="Documents",
               subjects="Major subjects", careers="Careers", higher="Higher study", mode="Admission mode",
               semesters="Semester structure", years="{n} years", qual="Qualifications", spec="Specialization",
               taught="Subjects taught", exp="Experience", exp_fmt="{t} yrs teaching, {i} yrs industry", email="Official email",
               office="Office", hours="Consultation hours", none="Not listed"),
    "hi": dict(duration="अवधि", annual="वार्षिक ट्यूशन फीस", total="कुल ट्यूशन फीस ({n} वर्ष)", seats="सीटें (नमूना क्षमता)",
               minmarks="न्यूनतम अंक", class12="कक्षा 12 के विषय", degree="स्नातक डिग्री", dept="विभाग", docs_label="दस्तावेज़",
               subjects="मुख्य विषय", careers="करियर", higher="उच्च अध्ययन", mode="प्रवेश का आधार",
               semesters="सेमेस्टर संरचना", years="{n} वर्ष", qual="योग्यताएँ", spec="विशेषज्ञता",
               taught="पढ़ाए जाने वाले विषय", exp="अनुभव", exp_fmt="{t} वर्ष शिक्षण, {i} वर्ष उद्योग", email="आधिकारिक ईमेल",
               office="कार्यालय", hours="परामर्श समय", none="सूचीबद्ध नहीं"),
    "hn": dict(duration="Duration", annual="Annual tuition fee", total="Total tuition ({n} saal)", seats="Seats (sample intake)",
               minmarks="Minimum marks", class12="Class 12 subjects", degree="Bachelor's degree", dept="Department", docs_label="Documents",
               subjects="Major subjects", careers="Careers", higher="Higher study", mode="Admission ka aadhaar",
               semesters="Semester structure", years="{n} saal", qual="Qualifications", spec="Specialization",
               taught="Padhaaye jaane wale subjects", exp="Experience", exp_fmt="{t} saal teaching, {i} saal industry",
               email="Official email", office="Office", hours="Consultation hours", none="Listed nahi"),
}

# (button label, page) for each destination that exists on the website
LINKS = {
    "explore": ("views/courses.py", _t("Explore courses", "कोर्स देखें", "Courses dekhein")),
    "apply": ("views/admissions.py", _t("Begin registration", "रजिस्ट्रेशन शुरू करें", "Registration shuru karein")),
    "faculty": ("views/faculty.py", _t("Open faculty directory", "फैकल्टी डायरेक्टरी खोलें", "Faculty directory kholein")),
    "contact": ("views/contact.py", _t("Contact the college", "कॉलेज से संपर्क करें", "College se sampark karein")),
}


def T(lang: str, key: str, **kw) -> str:
    return S[key][lang].format(**kw) if kw else S[key][lang]


def lb(lang: str, key: str, **kw) -> str:
    return LBL[lang][key].format(**kw) if kw else LBL[lang][key]


def _link(lang: str, key: str):
    page, labels = LINKS[key]
    return (labels[lang], page)


# ============================================================ text normalising
_DEVA = [
    (r"बी\s*\.?\s*टेक", "btech"), (r"बी\s*\.?\s*एससी|बीएससी", "bsc"), (r"बी\s*\.?\s*कॉम|बीकॉम", "bcom"),
    (r"बीसीए", "bca"), (r"एमसीए", "mca"), (r"बीबीए", "bba"), (r"एमबीए", "mba"), (r"सीएसई", "cse"),
    (r"कंप्यूटर साइंस|कम्प्यूटर साइंस", "computer science"), (r"फिजिक्स|भौतिक विज्ञान|भौतिकी", "physics"),
    (r"केमिस्ट्री|रसायन विज्ञान|रसायन", "chemistry"), (r"मैथ्स|मैथमेटिक्स|गणित", "mathematics"),
    (r"बायोलॉजी|जीव विज्ञान", "biology"), (r"बायोटेक्नोलॉजी", "biotechnology"), (r"डेटा साइंस", "data science"),
    (r"मैकेनिकल", "mechanical"), (r"सिविल", "civil"), (r"इलेक्ट्रिकल", "electrical"),
    (r"इलेक्ट्रॉनिक्स", "electronics"), (r"रोबोटिक्स", "robotics"),
]


def norm(text: str) -> str:
    s = text.lower().replace("&", " and ").replace("₹", " ₹ ").replace("'", "").replace("’", "")
    s = re.sub(r"(?<=\d),(?=\d)", "", s)
    for pat, rep in _DEVA:
        s = re.sub(pat, f" {rep} ", s)
    s = re.sub(r"bachelor of technology|bachelor of engineering", "btech", s)
    s = re.sub(r"bachelors? of science|bachelor of sciences", "bsc", s)
    s = re.sub(r"master of computer applications?", "mca", s)
    s = re.sub(r"master of business administration", "mba", s)
    s = re.sub(r"\bb\s*\.?\s*tech\b", "btech", s)
    s = re.sub(r"\bb\s*\.?\s*sc\b", "bsc", s)
    s = re.sub(r"\bb\s*\.?\s*com\b", "bcom", s)
    s = re.sub(r"\bb\s*\.\s*c\s*\.\s*a\b", "bca", s)
    s = re.sub(r"\bm\s*\.\s*c\s*\.\s*a\b", "mca", s)
    s = re.sub(r"\bm\s*\.\s*b\s*\.\s*a\b", "mba", s)
    s = re.sub(r"[^\w\s.%₹\u0900-\u097F]", " ", s)
    s = re.sub(r"(?<!\d)\.|\.(?!\d)", " ", s)
    return re.sub(r"\s+", " ", s).strip()


# ================================================================= language
_HN = re.compile(r"\b(kya|kitna|kitni|kitne|hai|hain|ki|ka|ke|mujhe|batao|bataiye|dikhao|dikhaiye|chahiye|kaunsa|kaunse|kaun|"
                 r"kaise|nahi|sakta|sakti|sakte|mein|paas|maine|aur|liye|saal|karna|karein|mera|meri|mere|tak|kam|zyada)\b")
_EN = {"the", "is", "are", "what", "which", "how", "can", "do", "does", "for", "of", "show", "compare", "list", "my", "am",
       "with", "available", "tell", "give", "please", "need", "want", "who", "where", "when", "under", "below", "within",
       "i", "me", "and", "to", "a", "an", "in", "on", "it", "about", "hi", "hello"}


def detect_lang(raw: str, prev: str = "en") -> str:
    if re.search(r"[\u0900-\u097F]", raw):
        return "hi"
    low = raw.lower()
    if re.fullmatch(r"\s*(namaste|namaskar)[\s!.]*", low):
        return "hn"
    if _HN.search(low):
        return "hn"
    if any(w in _EN for w in re.findall(r"[a-z']+", low)):
        return "en"
    return prev


# ============================================================ course matching
BY_ID: dict[str, dict] = {}
_ALIASES: dict[str, list[str]] = {}
_INDEX = {"sig": None}
_BARE = {"physics", "chemistry", "mathematics", "maths", "math", "biology", "commerce", "computer science"}


def _alias(ids, *phrases):
    ids = [ids] if isinstance(ids, str) else list(ids)
    for p in phrases:
        cur = _ALIASES.setdefault(p, [])
        cur += [i for i in ids if i not in cur]


# Abbreviations and synonyms that cannot be derived from a course name (ids that are not in the catalogue are skipped).
_MANUAL = [
    (('btech-cse',), ('btech cse', 'cse', 'computer science and engineering', 'computer science engineering', 'btech computer science', 'btech computer science and engineering')),
    (('bsc-cs',), ('bsc computer science', 'bsc cs')),
    (('btech-cse', 'bsc-cs'), ('computer science',)),
    (('btech-it',), ('btech it', 'btech information technology', 'information technology')),
    (('btech-mech',), ('mechanical', 'mechanical engineering', 'btech mechanical', 'mech')),
    (('btech-civil',), ('civil', 'civil engineering', 'btech civil')),
    (('btech-eee',), ('electrical', 'electrical engineering', 'eee', 'electrical and electronics', 'btech electrical', 'btech eee')),
    (('btech-ece',), ('ece', 'electronics and communication', 'electronics communication', 'btech ece', 'electronics')),
    (('btech-chem',), ('chemical engineering', 'btech chemical', 'chemical')),
    (('bsc-chem',), ('bsc chemistry', 'chemistry')),
    (('btech-engphy',), ('engineering physics', 'btech engineering physics', 'btech physics')),
    (('bsc-phy',), ('bsc physics',)),
    (('bsc-phy', 'btech-engphy'), ('physics',)),
    (('btech-aero',), ('aeronautical', 'aeronautical engineering', 'btech aeronautical')),
    (('btech-aerospace',), ('aerospace', 'aerospace engineering', 'btech aerospace')),
    (('btech-aiml',), ('aiml', 'ai ml', 'ai and ml', 'ai and machine learning', 'artificial intelligence and machine learning', 'machine learning', 'artificial intelligence', 'btech aiml', 'btech ai ml')),
    (('btech-biotech',), ('biotechnology engineering', 'btech biotechnology', 'btech biotech')),
    (('bsc-biotech',), ('bsc biotechnology', 'bsc biotech')),
    (('bsc-biotech', 'btech-biotech'), ('biotechnology', 'biotech')),
    (('btech-robotics',), ('robotics', 'robotics and automation', 'robotics and automation engineering', 'btech robotics')),
    (('btech-ds',), ('btech data science', 'btech ds')),
    (('bsc-ds',), ('bsc data science', 'bsc ds')),
    (('btech-ds', 'bsc-ds'), ('data science',)),
    (('bca',), ('bca',)),
    (('mca',), ('mca',)),
    (('bba',), ('bba',)),
    (('mba',), ('mba',)),
    (('bcom',), ('bcom', 'commerce')),
    (('bsc-math',), ('bsc mathematics', 'bsc maths', 'mathematics', 'maths', 'math')),
    (('bsc-bio',), ('bsc biology', 'biology')),
    (('bsc-bot',), ('bsc botany', 'botany')),
    (('bsc-zoo',), ('bsc zoology', 'zoology')),
    (('bsc-stat',), ('bsc statistics', 'statistics')),
    (('bsc-micro',), ('bsc microbiology', 'microbiology')),
    (('bsc-env',), ('bsc environmental science', 'environmental science', 'environmental')),
]
_DEGREE_PREFIXES = ("btech", "bsc", "bca", "mca", "bba", "bcom", "mba")


def _auto_aliases() -> None:
    """Every course can be found by its full name, and by its name without the degree (a 'stem'). A stem shared by
    several courses, or contained in another course's stem ('physics' / 'engineering physics'), is ambiguous."""
    stems: dict[str, list[str]] = {}
    for c in COURSES:
        full = norm(c["name"])
        _alias(c["id"], full)
        first, _, rest = full.partition(" ")
        if first in _DEGREE_PREFIXES and rest:
            stems.setdefault(rest, []).append(c["id"])
    for stem, ids in stems.items():
        group = list(ids)
        for other, other_ids in stems.items():
            if other != stem and re.search(rf"(?<![a-z0-9]){re.escape(stem)}(?![a-z0-9])", other):
                group += [i for i in other_ids if i not in group]
        _alias(group, stem)


def _rebuild_index() -> None:
    """Called at the start of every reply, so new, renamed, changed or deleted courses are picked up at once."""
    BY_ID.clear()
    BY_ID.update({c["id"]: c for c in COURSES})
    signature = tuple((c["id"], c["name"]) for c in COURSES)
    if signature == _INDEX["sig"]:
        return
    _ALIASES.clear()
    for ids, phrases in _MANUAL:
        present = [i for i in ids if i in BY_ID]
        if present:
            _alias(present, *phrases)
    _auto_aliases()
    _INDEX["sig"] = signature


def _groups() -> list[str]:
    return list(GROUPS) + [g for g in dict.fromkeys(c["group"] for c in COURSES) if g not in GROUPS]


_OPTION_WORDS = [(r"\b(first|1st|1|one|pehla|pehle)\b|पहला|पहले", 0), (r"\b(second|2nd|2|two|doosra|dusra|doosre)\b|दूसरा|दूसरे", 1)]


def find_courses(n: str, raw: str, ctx: bool):
    """-> (resolved ids, ambiguous [(phrase, ids)], spans)"""
    hits = []
    for phrase, ids in _ALIASES.items():
        if ctx and phrase in _BARE:
            continue
        for m in re.finditer(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", n):
            hits.append((m.start(), m.end(), phrase, ids))
    if re.search(r"\bIT\b", raw):
        hits.append((-1, -1, "it", ["btech-it"]))
    keep = [h for h in hits if not any(o is not h and o[0] <= h[0] and h[1] <= o[1] and (o[1] - o[0]) > (h[1] - h[0]) for o in hits)]
    keep.sort(key=lambda h: h[0])
    want = "btech" if re.search(r"\b(btech|engineering)\b", n) else "bsc" if re.search(r"\bbsc\b", n) else None
    resolved, ambiguous = [], []
    for _, _, phrase, ids in keep:
        if len(ids) == 1:
            if ids[0] not in resolved:
                resolved.append(ids[0])
            continue
        narrowed = [i for i in ids if want and i.startswith(want)]
        if len(narrowed) == 1:
            if narrowed[0] not in resolved:
                resolved.append(narrowed[0])
        elif not any(set(ids) & set(a[1]) == set(ids) for a in ambiguous):
            ambiguous.append((phrase, ids))
    ambiguous = [a for a in ambiguous if not (set(a[1]) & set(resolved))]
    return resolved, ambiguous, [(h[0], h[1]) for h in keep if h[0] >= 0]


def _mask(n: str, spans) -> str:
    chars = list(n)
    for a, b in spans:
        for i in range(a, b):
            chars[i] = " "
    return "".join(chars)


# ================================================================== profile
_CTX = re.compile(r"\b(pcm|pcb|pcmb|pcmc)\b|\b(i have|i am|i studied|i took|i scored|i got|my subjects|my stream|my marks|"
                  r"my percentage|mere paas|maine|mera|meri|mere)\b|class 12|12th|12 th|xii|stream|%|percent|percentage|marks|"
                  r"\bwith (commerce|arts|humanities)\b|\b(commerce|arts|humanities) (background|student)\b|"
                  r"प्रतिशत|मेरे पास|मैंने|बारहवीं|12वीं")
_SUBJ = {"physics": r"\bphysics\b", "chemistry": r"\bchemistry\b", "mathematics": r"\b(mathematics|maths|math)\b",
         "biology": r"\bbiology\b", "computer science": r"\bcomputer science\b",
         "technical vocational subject": r"\bvocational\b"}
_DEG_PAT = re.compile(r"\b(?:i have|i did|i completed|i finished|i passed|i hold|i am a|completed|maine)\s+(?:a\s+|my\s+)?"
                      r"(?:bachelor(?:s)? (?:degree )?(?:in )?)?(bca|bsc computer science|bsc|bcom|btech cse|btech it|btech computer science|btech information technology|btech|bba|graduation|graduate)\b")
_CS_DEGREES = ("bca", "bsc computer science", "btech cse", "btech it", "btech computer science", "btech information technology")


def parse_profile(n: str, raw: str) -> dict:
    p: dict = {}
    subs = set()
    if re.search(r"\bpcmb\b", n):
        subs |= {"physics", "chemistry", "mathematics", "biology"}
    if re.search(r"\bpcm\b", n):
        subs |= {"physics", "chemistry", "mathematics"}
    if re.search(r"\bpcb\b", n):
        subs |= {"physics", "chemistry", "biology"}
    for name, pat in _SUBJ.items():
        if re.search(pat, n):
            subs.add(name)
    if subs:
        p["subjects"] = subs
    st = (re.search(r"\b(science|commerce|arts|humanities) (?:stream|background|student)\b", n)
          or re.search(r"\bstream (?:is |:)?(science|commerce|arts|humanities)\b", n)
          or re.search(r"\bwith (commerce|arts|humanities)\b", n))
    if st:
        p["stream"] = st.group(1)
    m = (re.search(r"(\d{2,3}(?:\.\d+)?)\s*(?:%|percent|percentage|pratishat|प्रतिशत)", n)
         or re.search(r"\b(?:marks?|scored|score|got|aaye|mile)\D{0,12}(\d{2,3}(?:\.\d+)?)\b", n))
    if m and 0 < float(m.group(1)) <= 100:
        p["percent"] = float(m.group(1))
    low = raw.lower()
    if re.search(r"class\s*12|12th|12 th|\bxii\b|twelfth|intermediate|\bhsc\b|plus two|10\s*\+\s*2|12वीं|बारहवीं", low):
        p["qualification"] = "class12"
    if re.search(r"स्नातक डिग्री|ग्रेजुएट|graduation (kiya|complete|pass)", low):
        p["qualification"] = "bachelors"
    if re.search(r"\b(i have|i hold|i completed|i did|i finished|i am a|i passed)\b[^.?!]{0,30}\b(bachelors?|degree|graduate|graduation)\b", n):
        p["qualification"] = "bachelors"
    d = _DEG_PAT.search(norm(raw))
    if d:
        p["qualification"] = "bachelors"
        p["degree_name"] = d.group(1)
    if re.search(r"\bdiploma\b", n) and re.search(r"\b(i have|i am|my|holder|maine|mere paas)\b|\bdiploma holder", n):
        p["qualification"] = "diploma"
    return p


def parse_amount(n: str):
    s = re.sub(r"\d+(?:\.\d+)?\s*(?:%|percent|percentage|प्रतिशत)", " ", n)
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:lakh|lakhs|lac|lacs|लाख)", s)
    if m:
        return int(float(m.group(1)) * 100000)
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:k|thousand|hazaar|hazar|हज़ार|हजार)\b", s)
    if m:
        return int(float(m.group(1)) * 1000)
    m = re.search(r"(?:₹|rs\.?|inr)\s*(\d{4,9})", s) or re.search(r"\b(\d{5,9})\b", s)
    return int(m.group(1)) if m else None


# =========================================================== intent patterns
R = {k: re.compile(v) for k, v in {
    "fee": r"\b(fees?|cost|costs|tuition|price|charges?|shulk|kharch\w*)\b|फीस|शुल्क|खर्च|ट्यूशन",
    "seats": r"\b(seats?|intake|capacity|vacanc\w+)\b|सीट",
    "duration": r"\b(duration|how long|semesters?|kitne saal|kitne sal|kitne varsh)\b|अवधि|कितने साल|कितने वर्ष|सेमेस्टर",
    "elig": r"\b(eligib\w*|qualif\w*|criteria|yogya\w*|patra\w*|can i (?:apply|join|take|get|study|do)|am i|do i (?:qualify|meet)|"
            r"le sakta|le sakti|le sakte)\b|योग्यता|पात्र|आवेदन कर सक|ले सकता|ले सकती",
    "docs": r"\b(documents?|docs|kagaz\w*|dastavez\w*)\b|दस्तावेज|कागज",
    "careers": r"\b(careers?|jobs?|naukri|scope)\b|करियर|नौकरी",
    "subjects": r"\b(syllabus|curriculum|major subjects|what will i study)\b|पाठ्यक्रम|सिलेबस|मुख्य विषय",
    "dept": r"\b(department|dept)\b|विभाग",
    "faculty": r"\b(faculty|faculties|professors?|teachers?|lecturers?|hod|head of|dean|staff|teaches|teach|taught by|shikshak|adhyapak|"
               r"padhata|padhate|padhati)\b|शिक्षक|अध्यापक|प्रोफेसर|फैकल्टी|एचओडी|विभागाध्यक्ष|पढ़ाते|पढ़ाता",
    "compare": r"\b(compare|comparison|versus|vs|difference|tulna)\b|तुलना|बनाम",
    "admission": r"\b(regist\w*|admissions?|apply|enrol\w*|pravesh|rajistration)\b|रजिस्ट्रेशन|पंजीकरण|प्रवेश|एडमिशन|आवेदन",
    "exclusion": r"\b(exclud\w*|additional (?:fees?|charges?)|extra (?:fees?|charges?)|other charges|hidden)\b|अतिरिक्त शुल्क|अन्य शुल्क",
    "action": r"\b(approve|reject|accept my|confirm my|status of my|submit my|my application status|book my seat|reserve)\b|स्वीकृत करो|मेरा आवेदन",
    "unstored": r"\b(deadlines?|last date|due date|scholarships?|placements?|packages?|salary|salaries|payment|hostel|transport)\b|"
                r"अंतिम तिथि|छात्रवृत्ति|प्लेसमेंट|वेतन|हॉस्टल|भुगतान",
    "advice": r"\b(visa|immigration|legal|lawyer|loan|emi)\b|वीज़ा|वीजा|लोन",
    "listing": r"\b(list|available|offer|offered|courses|programmes?|programs?|degrees?|options?|kaun ?se|kaunsa|kaunse)\b|कौन|कोर्स",
    "budget": r"\b(budget|under|below|within|less than|upto|up to|at most|above|more than|over|cheaper|affordable|se kam|tak)\b|"
              r"बजट|से कम|तक|से ज़्यादा|से ज्यादा",
    "above": r"\b(above|more than|over|at least|zyada)\b|से ज़्यादा|से ज्यादा|से अधिक",
    "total": r"\b(total|overall|full course|entire|kul|poore)\b|कुल|पूरे",
    "personal": r"\b(am i|can i|do i|i have|i am|my|kya main|main|mujhe|mere|mera|meri|maine)\b|मैं|मुझे|मेरे|मेरा",
    "lateral": r"\b(lateral|diploma)\b|लेटरल|डिप्लोमा",
    "listwords": r"\b(which|what|courses|consider|options|kaun ?se|kaunsa|kaunse|list|show|dikhao|batao)\b|कौन|कोर्स|दिखाओ|बताओ",
}.items()}
_GREET = re.compile(r"^(hi+|hello|hey|namaste|namaskar|hola)$|^(नमस्ते|नमस्कार)$")
_SENSITIVE = re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b|\b[A-Z]{5}\d{4}[A-Z]\b|\b(aadhaar|aadhar|pan card|password|otp|cvv|"
                        r"account number|card number|ifsc)\b|आधार|पासवर्ड", re.I)
_STOP = set("a an the is are was be to of for in on at and or with about me my i you your it this that these those what which who how "
            "can do does please tell give show want need know kya hai hain ki ka ke ko se mein liye batao bataiye dikhao course "
            "courses fee fees cost seats seat duration eligible eligibility documents required details information its their "
            "also more then other career careers job jobs syllabus curriculum subjects department admission available offer "
            "offered list programme programmes program programs degree degrees options option have there any show".split())
ASPECT_ORDER = ["fee", "seats", "duration", "elig", "docs", "careers", "subjects", "dept"]


# ============================================================== eligibility
def evaluate(c: dict, p: dict, need_pct: bool = True):
    """-> (verdict, met, unmet, unverified) with items as (message key, params)."""
    met, unmet, unver = [], [], []
    qual, subjects, pct = p.get("qualification"), p.get("subjects") or set(), p.get("percent")
    rule = c.get("req12")
    if c["level"] == "Postgraduate":
        if qual in ("class12", "diploma"):
            unmet.append(("pg_need_degree", {"d": c["degree"] or "-"}))
        elif qual == "bachelors":
            met.append(("pg_degree_held", {}))
            if c["id"] == "mca":
                g = p.get("degree_name")
                if not g:
                    unver.append(("mca_unknown", {}))
                elif g in _CS_DEGREES or "computer" in g:
                    met.append(("mca_ok", {"g": _deg_label(g)}))
                    unver.append(("mca_math", {}))
                else:
                    unmet.append(("mca_bad", {"d": c["degree"] or "-", "g": _deg_label(g)}))
            else:
                unver.append(("degree_accepted", {}))
        else:
            unver.append(("qual_unknown", {}))
    else:
        if qual == "diploma":
            unver.append(("diploma_lateral", {}) if c["name"].startswith("B.Tech") else ("diploma_none", {}))
        elif qual == "bachelors":
            unver.append(("qual_ug", {}))
        if qual in (None, "class12"):
            if rule is None:
                unver.append(("req_missing", {}))
            elif rule.get("any_stream"):
                met.append(("any_stream", {}))
            elif rule.get("unverified"):
                unver.append(("stream_unver", {}))
            elif not subjects:
                unver.append(("subj_unknown", {}))
            else:
                miss = [s for s in rule.get("all", []) if s not in subjects]
                bad_groups = [g for g in rule.get("one_of", []) if not any(s in subjects for s in g)]
                if not miss and not bad_groups:
                    need = list(rule.get("all", [])) + [next(s for s in g if s in subjects) for g in rule.get("one_of", [])]
                    met.append(("subj_ok", {"s": ", ".join(x.title() for x in need)}))
                else:
                    target = unver if rule.get("other_unverified") else unmet
                    if miss:
                        target.append(("subj_missing", {"s": ", ".join(x.title() for x in miss)}))
                    for g in bad_groups:
                        target.append(("subj_oneof", {"s": " / ".join(x.title() for x in g)}))
                    if rule.get("other_unverified"):
                        unver.append(("other_subj", {}))
    if pct is not None:
        (met if pct >= c["min_pct"] else unmet).append(
            ("pct_ok" if pct >= c["min_pct"] else "pct_low", {"p": f"{pct:g}", "m": c["min_pct"]}))
    elif need_pct:
        unver.append(("pct_unknown", {}))
    verdict = "not_meet" if unmet else "insufficient" if unver else "meets"
    return verdict, met, unmet, unver


def _subs(items) -> str:
    return ", ".join(sorted(x.title() for x in items))


def _deg_label(g: str) -> str:
    caps = {"bca", "bcom", "bba", "bsc", "btech", "cse", "it"}
    return " ".join(w.upper() if w in caps else w.title() for w in g.split())


def _crit(lang, items):
    out = []
    for key, kw in items:
        if key == "diploma_lateral":
            kw = {"t": T(lang, "lateral_text")}
        out.append(T(lang, key, **kw))
    return out


# =========================================================== reply builders
def _notice_on() -> bool:
    """The administrator can switch the 'illustrative prototype data' note off once all data is verified."""
    return COLLEGE.get("show_prototype_notice", True) is not False


def _compose(lang, direct, bullets=(), prototype=False, extra=None, next_text=None, link=None):
    parts = [direct]
    if bullets:
        parts.append("\n".join(f"- {b}" for b in bullets))
    if extra:
        parts.append(extra)
    if prototype and _notice_on():
        parts.append(T(lang, "disclaimer"))
    if next_text:
        parts.append(next_text)
    return Reply("\n\n".join(parts), link, lang)


def _entry_line(lang, c):
    if c["class12"]:
        return f"{lb(lang, 'class12')}: {c['class12']}"
    if c["degree"]:
        return f"{lb(lang, 'degree')}: {c['degree']}"
    return f"{lb(lang, 'class12')}: {lb(lang, 'none')}"


def _years(lang, c):
    return lb(lang, "years", n=c["years"])


def _line(lang, c):
    return f"{c['name']} — {_years(lang, c)}, {lb(lang, 'annual')}: {format_inr(c['tuition'])}"


def not_verified(lang, link="contact"):
    return Reply(T(lang, "not_verified") + "\n\n" + T(lang, "n_contact"), _link(lang, link), lang)


def r_course_details(lang, c, aspects, directory):
    name = c["name"]
    aspects = [a for a in ASPECT_ORDER if a in aspects]
    b = []
    for a in aspects or ["summary"]:
        if a in ("fee", "summary"):
            b += [f"{lb(lang, 'annual')}: {format_inr(c['tuition'])}",
                  f"{lb(lang, 'total', n=c['years'])}: {format_inr(c['tuition'] * c['years'])}"]
            if a == "fee":
                b.append(T(lang, "fee_excl"))
        if a in ("seats", "summary"):
            b.append(f"{lb(lang, 'seats')}: {c['seats']}")
        if a in ("duration", "summary"):
            b.append(f"{lb(lang, 'duration')}: {_years(lang, c)} ({c['years'] * 2} semesters)")
        if a == "summary":
            b.append(f"{lb(lang, 'minmarks')}: {c['min_pct']}%")
        if a == "elig":
            b.append(_entry_line(lang, c))
            b.append(f"{lb(lang, 'minmarks')}: {c['min_pct']}%")
            b.append(T(lang, "diploma_lateral", t=T(lang, "lateral_text")) if c["name"].startswith("B.Tech") else T(lang, "diploma_none"))
            b.append(f"{lb(lang, 'mode')}: {c['admission_mode']}")
        if a == "docs":
            b += list(c["documents"]) or [f"{lb(lang, 'docs_label')}: {lb(lang, 'none')}"]
        if a == "careers":
            b += [f"{lb(lang, 'careers')}: {'; '.join(c['careers']) or lb(lang, 'none')}", f"{lb(lang, 'higher')}: {'; '.join(c['higher_studies']) or lb(lang, 'none')}"]
        if a == "subjects":
            b += [f"{lb(lang, 'subjects')}: {', '.join(c['subjects']) or lb(lang, 'none')}", f"{lb(lang, 'semesters')}: {c['semesters'] or lb(lang, 'none')}"]
        if a == "dept":
            dept = next((d for d in (directory or {}).get("departments", []) if c["id"] in d["course_ids"]), None)
            b.append(f"{lb(lang, 'dept')}: {dept['name']}" if dept else f"{lb(lang, 'dept')}: {lb(lang, 'none')}")
    first = aspects[0] if aspects else "summary"
    direct = {
        "fee": lambda: T(lang, "d_fee", name=name, annual=format_inr(c["tuition"]), n=c["years"], total=format_inr(c["tuition"] * c["years"])),
        "seats": lambda: T(lang, "d_seats", name=name, seats=c["seats"]),
        "duration": lambda: T(lang, "d_duration", name=name, n=c["years"], sem=c["years"] * 2),
        "elig": lambda: T(lang, "d_elig", name=name), "docs": lambda: T(lang, "d_docs", name=name),
        "careers": lambda: T(lang, "d_careers", name=name), "subjects": lambda: T(lang, "d_subjects", name=name),
        "dept": lambda: T(lang, "d_dept", name=name, dept=(next((d["name"] for d in (directory or {}).get("departments", [])
                                                               if c["id"] in d["course_ids"]), lb(lang, "none")))),
        "summary": lambda: T(lang, "d_summary", name=name),
    }[first]()
    if first == "dept" and len(aspects) == 1:
        b = [x for x in b if not x.startswith(lb(lang, "dept"))] or []
    nxt = T(lang, "n_elig") if "elig" in aspects else T(lang, "n_course")
    return _compose(lang, direct, b, True, next_text=nxt, link=_link(lang, "explore"))


def r_compare(lang, courses):
    if len(courses) < 2:
        return Reply(T(lang, "cmp_need_two"), None, lang)
    b = []
    for c in courses:
        sub = [f"{lb(lang, 'duration')}: {_years(lang, c)}", f"{lb(lang, 'annual')}: {format_inr(c['tuition'])}",
               f"{lb(lang, 'total', n=c['years'])}: {format_inr(c['tuition'] * c['years'])}",
               f"{lb(lang, 'seats')}: {c['seats']}", f"{lb(lang, 'minmarks')}: {c['min_pct']}%",
               _entry_line(lang, c)]
        b.append(f"**{c['name']}**\n" + "\n".join(f"  - {s}" for s in sub))
    extra = None
    fees = {c["tuition"] for c in courses}
    if len(fees) > 1:
        low = min(courses, key=lambda c: c["tuition"])
        extra = T(lang, "cmp_cheapest", name=low["name"], fee=format_inr(low["tuition"]))
    return _compose(lang, T(lang, "cmp_intro", names=" / ".join(c["name"] for c in courses)), b, True, extra,
                    T(lang, "n_course"), _link(lang, "explore"))


def r_list(lang, courses, grouped):
    if grouped:
        b = []
        for g in _groups():
            names = [c["name"] for c in courses if c["group"] == g]
            if names:
                b.append(f"**{g}** ({len(names)}): " + ", ".join(names))
        return _compose(lang, T(lang, "all_courses", n=len(courses)), b, False, None, T(lang, "n_compare"), _link(lang, "explore"))
    if not courses:
        return _compose(lang, T(lang, "no_match"), [], False, None, T(lang, "n_explore"), _link(lang, "explore"))
    return _compose(lang, T(lang, "found_courses", n=len(courses)), [_line(lang, c) for c in courses], True, None,
                    T(lang, "n_compare"), _link(lang, "explore"))


def r_filter(lang, courses, amount, total, op_key):
    basis = T(lang, "basis_total" if total else "basis_annual")
    op = T(lang, op_key)
    if not courses:
        return _compose(lang, T(lang, "no_match"), [], False, None, T(lang, "n_explore"), _link(lang, "explore"))
    b = [f"{c['name']} — {lb(lang, 'total', n=c['years']) if total else lb(lang, 'annual')}: "
         f"{format_inr(c['tuition'] * c['years'] if total else c['tuition'])}" for c in courses]
    return _compose(lang, T(lang, "filter_intro", n=len(courses), basis=basis, op=op, amount=format_inr(amount)), b, True, None,
                    T(lang, "n_compare"), _link(lang, "explore"))


def r_eligibility(lang, c, profile):
    verdict, met, unmet, unver = evaluate(c, profile)
    key = {"meets": "elig_meets", "not_meet": "elig_not", "insufficient": "elig_insuf"}[verdict]
    b = []
    for label, items in (("lbl_met", met), ("lbl_unmet", unmet), ("lbl_unver", unver)):
        for line in _crit(lang, items):
            b.append(f"**{T(lang, label)}:** {line}")
    caveat = T(lang, "confirm_extra" if c["name"].startswith("B.Tech") else "confirm_gen")
    missing = []
    if any(k in ("subj_unknown",) for k, _ in unver):
        missing.append(T(lang, "m_subjects"))
    if any(k == "pct_unknown" for k, _ in unver):
        missing.append(T(lang, "m_percent"))
    if any(k == "qual_unknown" for k, _ in unver):
        missing.append(T(lang, "m_qual"))
    if any(k == "mca_unknown" for k, _ in unver):
        missing.append(T(lang, "m_degree"))
    ask = T(lang, "ask_profile", missing=T(lang, "and").join(missing)) if missing else None
    nxt = T(lang, "n_apply") if verdict == "meets" else T(lang, "n_contact")
    link = _link(lang, "apply" if verdict == "meets" else "contact")
    return _compose(lang, T(lang, key, course=c["name"]), b, True, caveat + (("\n\n" + ask) if ask else ""), nxt, link), missing


def r_stream(lang, profile):
    subs = profile.get("subjects") or set()
    ok, check = [], []
    stream_only = not subs
    for c in COURSES:
        if c["level"] != "Undergraduate":
            continue
        verdict, _, unmet, unver = evaluate(c, {**profile, "qualification": "class12"}, need_pct=False)
        if verdict == "meets":
            ok.append(c)
        elif verdict == "insufficient" and not unmet:
            check.append(c)
    if not ok and not check:
        return _compose(lang, T(lang, "stream_none"), [], True, None, T(lang, "n_explore"), _link(lang, "explore"))
    b = [c["name"] for c in ok]
    if check and not stream_only:
        b.append(T(lang, "stream_check", names=", ".join(c["name"] for c in check)))
    label = _subs(subs) if subs else (profile.get("stream") or "").title()
    extra = T(lang, "stream_note")
    if stream_only:
        extra += "\n\n" + T(lang, "ask_profile", missing=T(lang, "m_subjects"))
    return _compose(lang, T(lang, "stream_intro", subs=label, n=len(ok)), b, True, extra,
                    T(lang, "n_stream"), _link(lang, "explore"))


def r_admission(lang, c, want_docs):
    steps = "\n".join(PROCEDURE_LINES())
    if want_docs and c is None:
        docs = (f"**{T(lang, 'docs_ug')}:**\n" + "\n".join(f"- {d}" for d in DOCS_UG) +
                f"\n\n**{T(lang, 'docs_pg')}:**\n" + "\n".join(f"- {d}" for d in DOCS_PG))
        return _compose(lang, T(lang, "adm_intro"), [], True, steps + "\n\n" + docs, T(lang, "n_apply"), _link(lang, "apply"))
    if want_docs and c is not None:
        return _compose(lang, T(lang, "d_docs", name=c["name"]), list(c["documents"]), True, None, T(lang, "n_apply"), _link(lang, "apply"))
    return _compose(lang, T(lang, "adm_where"), [], True, steps, T(lang, "n_apply"), _link(lang, "apply"))


def PROCEDURE_LINES():
    return [f"{i}. {s}" for i, s in enumerate(PROCEDURE, start=1)]


def r_lateral(lang):
    return _compose(lang, T(lang, "lateral_general", t=T(lang, "lateral_text")), [], True, None, T(lang, "n_contact"), _link(lang, "contact"))


def _fac_bullet(lang, f, contact=False):
    head = f"**{f['name']}** — {f['designation']}" + (f" · {f['post']}" if f["post"] else "")
    sub = [f"{lb(lang, 'dept')}: {f['department']}", f"{lb(lang, 'qual')}: {f['qualifications'] or lb(lang, 'none')}",
           f"{lb(lang, 'spec')}: {f['specialization'] or lb(lang, 'none')}",
           f"{lb(lang, 'taught')}: {', '.join(f['subjects']) or lb(lang, 'none')}",
           f"{lb(lang, 'exp')}: " + (lb(lang, "exp_fmt", t=f["teaching_years"], i=f["industry_years"])
                                     if f["teaching_years"] is not None else lb(lang, "none"))]
    if contact:
        sub += [f"{lb(lang, 'email')}: {f['email'] or lb(lang, 'none')}", f"{lb(lang, 'office')}: {f['office'] or lb(lang, 'none')}",
                f"{lb(lang, 'hours')}: {f['consultation_hours'] or lb(lang, 'none')}"]
    return head + "\n" + "\n".join(f"  - {s}" for s in sub)


def r_faculty(lang, people, intro, contact=False):
    if not people:
        return Reply(T(lang, "fac_none") + "\n\n" + T(lang, "n_contact"), _link(lang, "contact"), lang)
    shown = people[:6]
    extra = T(lang, "fac_more", n=len(people) - 6) if len(people) > 6 else None
    return _compose(lang, intro, [_fac_bullet(lang, f, contact) for f in shown], True, extra, T(lang, "n_faculty"), _link(lang, "faculty"))


# ============================================================ keyword filters
def course_filter(n: str):
    pool, used = list(COURSES), False
    def keep(pred):
        nonlocal pool, used
        pool, used = [c for c in pool if pred(c)], True
    if re.search(r"\bbsc\b", n):
        keep(lambda c: c["group"].startswith("B.Sc."))
    if re.search(r"\bbtech\b", n):
        keep(lambda c: c["group"].startswith("B.Tech."))
    if re.search(r"\bcore\b", n):
        keep(lambda c: "Core" in c["group"])
    if re.search(r"\bapplied\b", n):
        keep(lambda c: "Applied" in c["group"])
    if re.search(r"\bspeciali[sz]ed\b", n):
        keep(lambda c: "Specialized" in c["group"])
    if re.search(r"\bengineering\b", n) and not re.search(r"\bbtech\b", n):
        keep(lambda c: c["category"] == "Engineering")
    if re.search(r"\bcomputer\b|\bcomputing\b", n):
        keep(lambda c: any(k in c["name"].lower() for k in ("computer", "information technology", "artificial intelligence", "data science", "bca", "mca")))
    if re.search(r"\b(management|business)\b", n):
        keep(lambda c: c["category"] == "Management & Commerce")
    if re.search(r"\b(pg|postgraduate|masters?)\b", n):
        keep(lambda c: c["level"] == "Postgraduate")
    if re.search(r"\b(ug|undergraduate)\b", n):
        keep(lambda c: c["level"] == "Undergraduate")
    return pool, used


def _closest(n: str):
    cand = " ".join(w for w in n.split() if w not in _STOP)
    if not cand:
        return None, []
    scored = sorted(((SequenceMatcher(None, cand, norm(c["name"])).ratio(), c) for c in COURSES), key=lambda x: -x[0])
    return cand, [c for r, c in scored[:3] if r >= 0.45]


# ============================================================== main entry
def new_state() -> dict:
    return {"lang": "en", "profile": {}, "pending": None, "last_course": None}


def _pick_option(n, raw, options):
    if len(n.split()) <= 4:
        for pat, idx in _OPTION_WORDS:
            if re.search(pat, n) and idx < len(options):
                return options[idx]
    want = "btech" if re.search(r"\b(btech|engineering)\b", n) else "bsc" if re.search(r"\bbsc\b", n) else None
    if want:
        narrowed = [i for i in options if i.startswith(want)]
        if len(narrowed) == 1:
            return narrowed[0]
    res, _, _ = find_courses(n, raw, False)
    res = [i for i in res if i in options]
    return res[0] if len(res) == 1 else None


def respond(message: str, state: dict, directory: dict | None = None, _forced: list[str] | None = None) -> Reply:
    _rebuild_index()
    raw = message.strip()
    lang = detect_lang(raw, state.get("lang", "en"))
    state["lang"] = lang
    if _SENSITIVE.search(raw):
        return Reply(T(lang, "privacy"), None, lang, redact=True)
    n = norm(raw)
    if _GREET.match(n):
        return Reply(T(lang, "greet"), _link(lang, "explore"), lang)

    # ---- answer to an earlier "which one do you mean?"
    pend = state.get("pending")
    if pend and pend["type"] == "clarify" and _forced is None:
        choice = _pick_option(n, raw, pend["options"])
        if choice:
            state["pending"] = None
            return respond(pend["message"], state, directory, _forced=pend["resolved"] + [choice])

    ctx = bool(_CTX.search(n))
    resolved, ambiguous, spans = find_courses(n, raw, ctx)
    if _forced is not None:
        resolved, ambiguous = list(dict.fromkeys(_forced)), []
    prof_now = parse_profile(_mask(n, spans), raw) if (ctx or state.get("pending") or _DEG_PAT.search(n)) else {}
    if prof_now.get("degree_name") and _forced is None:   # "I completed BCA": the degree held is not the course asked about
        held = _ALIASES.get(prof_now["degree_name"], [])
        resolved = [i for i in resolved if not (len(held) == 1 and i == held[0])]
    prof = state["profile"]
    prof.update(prof_now)

    if R["exclusion"].search(n):
        items = [f"- {x.strip()}" for x in T(lang, "excl_items").split(";")]
        return Reply(T(lang, "excl_intro") + "\n\n" + "\n".join(items) + "\n\n" + T(lang, "fee_increase")
                     + "\n\n" + T(lang, "excl_amounts") + ("\n\n" + T(lang, "disclaimer") if _notice_on() else "") + "\n\n" + T(lang, "n_contact"),
                     _link(lang, "contact"), lang)
    if R["action"].search(n):
        return Reply(T(lang, "no_action") + "\n\n" + T(lang, "n_apply"), _link(lang, "apply"), lang)
    if R["advice"].search(n):
        return Reply(T(lang, "cannot_advise") + "\n\n" + T(lang, "n_contact"), _link(lang, "contact"), lang)
    if R["unstored"].search(n):
        return not_verified(lang)

    # ---- faculty
    people = None
    if directory is not None:
        people = directory["faculty"]
    names = []
    if people:
        for f in people:
            toks = [t for t in norm(f["name"]).split() if t not in ("dr", "mr", "ms", "prof") and len(t) >= 3]
            if any(re.search(rf"(?<![a-z0-9]){re.escape(t)}(?![a-z0-9])", n) for t in toks):
                names.append(f)
    if R["faculty"].search(n) or names:
        if directory is None:
            return Reply(T(lang, "fac_unavailable") + "\n\n" + T(lang, "n_contact"), _link(lang, "contact"), lang)
        contact = bool(re.search(r"\b(email|mail|contact|phone|office|hours|consultation)\b", n))
        if names:
            return r_faculty(lang, names, T(lang, "fac_found", n=len(names)), contact or len(names) == 1)
        subj_hit = None
        for s in sorted({s for f in people for s in f["subjects"]}, key=len, reverse=True):
            if re.search(rf"(?<![a-z0-9]){re.escape(norm(s))}(?![a-z0-9])", n):
                subj_hit = s
                break
        if subj_hit:
            hit = [f for f in people if subj_hit in f["subjects"]]
            return r_faculty(lang, hit, T(lang, "fac_teaches", subj=subj_hit, n=len(hit)))
        cand_ids = set(resolved) | {i for _, ids in ambiguous for i in ids}
        depts = [d for d in directory["departments"] if cand_ids & set(d["course_ids"])]
        if not depts:
            for d in sorted(directory["departments"], key=lambda d: -len(d["name"])):
                if re.search(rf"(?<![a-z0-9]){re.escape(norm(d['name']))}(?![a-z0-9])", n):
                    depts = [d]
                    break
        if len(depts) == 1:
            d = depts[0]
            members = [f for f in people if f["department"] == d["name"]]
            if re.search(r"\b(hod|head of)\b|एचओडी|विभागाध्यक्ष|\bdean\b", n):
                heads = [f for f in members if f["post"]]
                if heads:
                    f = heads[0]
                    return _compose(lang, T(lang, "fac_head", name=f["name"], post=f["post"], dept=d["name"]),
                                    [_fac_bullet(lang, f, contact)], True, None, T(lang, "n_faculty"), _link(lang, "faculty"))
                return Reply(T(lang, "fac_no_head", dept=d["name"]) + "\n\n" + T(lang, "n_contact"), _link(lang, "contact"), lang)
            return r_faculty(lang, members, T(lang, "fac_dept_intro", dept=d["name"], n=len(members)), contact)
        return Reply(T(lang, "ask_dept"), None, lang)

    # ---- diploma / lateral entry without a named course
    if R["lateral"].search(n) and not resolved and not ambiguous and not prof_now.get("subjects"):
        return r_lateral(lang)

    # ---- ambiguous course name: ask one short question
    needs_course = any(R[k].search(n) for k in ("fee", "seats", "duration", "elig", "docs", "careers", "subjects", "dept", "compare", "admission"))
    if ambiguous and not resolved and needs_course:
        phrase, ids = ambiguous[0]
        state["pending"] = {"type": "clarify", "options": ids, "message": raw, "resolved": []}
        opts = " / ".join(BY_ID[i]["name"] for i in ids)
        return Reply(f"{T(lang, 'which_one')} {opts}", None, lang)
    if ambiguous and resolved and R["compare"].search(n):
        phrase, ids = ambiguous[0]
        state["pending"] = {"type": "clarify", "options": ids, "message": raw, "resolved": list(resolved)}
        return Reply(f"{T(lang, 'which_one')} " + " / ".join(BY_ID[i]["name"] for i in ids), None, lang)

    # ---- compare
    if R["compare"].search(n):
        return r_compare(lang, [BY_ID[i] for i in resolved])

    # ---- eligibility
    elig_q = bool(R["elig"].search(n))
    pending_elig = pend if (pend and pend["type"] == "elig") else None
    if resolved and (elig_q or (pending_elig and prof_now and not R["fee"].search(n))) or (not resolved and pending_elig and prof_now):
        c = BY_ID[resolved[0] if resolved else pending_elig["course"]]
        personal = bool(R["personal"].search(n)) or bool(prof_now) or bool(pending_elig)
        if personal and (prof.get("subjects") or prof.get("percent") is not None or prof.get("qualification")):
            reply, missing = r_eligibility(lang, c, prof)
            state["pending"] = {"type": "elig", "course": c["id"]} if missing else None
            state["last_course"] = c["id"]
            return reply
        if personal:
            state["pending"] = {"type": "elig", "course": c["id"]}
        state["last_course"] = c["id"]
        reply = r_course_details(lang, c, ["elig"], directory)
        if personal:
            reply.text += "\n\n" + T(lang, "ask_profile", missing=T(lang, "and").join([T(lang, "m_subjects"), T(lang, "m_percent")]))
        return reply
    if elig_q and not resolved:
        if (prof.get("subjects") or prof.get("stream")) and (R["personal"].search(n) or prof_now):
            return r_stream(lang, prof)
        if prof_now.get("subjects") or prof_now.get("stream"):
            return r_stream(lang, prof)
        return Reply(T(lang, "ask_course") + " " + T(lang, "ask_profile", missing=T(lang, "m_subjects")), None, lang)
    if not resolved and (prof_now.get("subjects") or prof_now.get("stream")) and R["listwords"].search(n):
        return r_stream(lang, prof)

    # ---- budget filter (no specific course)
    amount = parse_amount(re.sub(r"\d+(?:\.\d+)?\s*(?:%|percent|percentage|प्रतिशत)", " ", n))
    if not resolved and R["budget"].search(n) and (amount or re.search(r"\bmy budget\b|apne budget|मेरे बजट|\bmera budget\b", n)):
        if not amount:
            return Reply(T(lang, "ask_budget"), None, lang)
        pool, _ = course_filter(n)
        total = bool(R["total"].search(n))
        def val(c): return c["tuition"] * (c["years"] if total else 1)
        if re.search(r"\b(at least)\b", n):
            op_key, ok = "op_ge", lambda v: v >= amount
        elif R["above"].search(n):
            op_key, ok = "op_gt", lambda v: v > amount
        elif re.search(r"\b(less than|under|below)\b|से कम|\bse kam\b", n):
            op_key, ok = "op_lt", lambda v: v < amount
        else:
            op_key, ok = "op_le", lambda v: v <= amount
        return r_filter(lang, [c for c in pool if ok(val(c))], amount, total, op_key)

    # ---- admission / registration / documents
    wants_docs = bool(R["docs"].search(n))
    aspects = [k for k in ASPECT_ORDER if R[k].search(n)]
    if R["admission"].search(n) and not (resolved and aspects):
        return r_admission(lang, BY_ID[resolved[0]] if resolved else None, wants_docs)
    if wants_docs and not resolved:
        return r_admission(lang, None, True)

    # ---- course aspects (fee, seats, duration, ...)
    if not resolved and not ambiguous and aspects and state.get("last_course") and not _closest(n)[0]:
        resolved = [state["last_course"]]
    if resolved:
        c = BY_ID[resolved[0]]
        state["last_course"] = c["id"]
        return r_course_details(lang, c, aspects, directory)

    # ---- discovery / listing
    pool, used = course_filter(n)
    if used and (R["listing"].search(n) or R["listwords"].search(n)):
        return r_list(lang, pool, False)
    if R["listing"].search(n) and not aspects:
        cand, close = _closest(n)
        if not cand:
            return r_list(lang, list(COURSES), True)
        if close:
            return _compose(lang, T(lang, "closest"), [_line(lang, c) for c in close], True, None, T(lang, "n_course"), _link(lang, "explore"))
        return not_verified(lang)

    # ---- the question mentions a course aspect but the course is unknown
    if aspects:
        cand, close = _closest(n)
        if close:
            return _compose(lang, T(lang, "closest"), [_line(lang, c) for c in close], True, None, T(lang, "n_course"), _link(lang, "explore"))
        if not cand:
            return Reply(T(lang, "ask_course"), None, lang)
    return not_verified(lang)


_rebuild_index()
