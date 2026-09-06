"""
MODULE 3 -- DISEASE KNOWLEDGE BASE

A small, hand-curated set of ~10 diseases used as the "verified" source
the RAG layer retrieves from. In a production system this content would
come from official sources (WHO, MoHFW, state health department) and be
reviewed by clinicians. For the prototype, general public-health facts
are summarized here with a `source` field naming the type of authority
a real deployment would cite.

Each entry stores the structured fields called for in the blueprint:
overview, symptoms, warning_signs, transmission, prevention, myths_facts,
when_to_seek_care, source, last_updated.
"""

DISEASES = {
    "dengue": {
        "name": "Dengue",
        "overview": "Dengue is a mosquito-borne viral infection common in tropical and "
                    "subtropical regions, spread mainly by Aedes aegypti mosquitoes that "
                    "bite during the day.",
        "symptoms": ["High fever", "Severe headache", "Pain behind the eyes",
                     "Muscle and joint pain", "Nausea", "Vomiting", "Skin rash"],
        "warning_signs": ["Severe abdominal pain", "Persistent vomiting",
                           "Bleeding gums or nose", "Blood in vomit or stool",
                           "Extreme fatigue or restlessness", "Difficulty breathing"],
        "transmission": "Spread through the bite of an infected Aedes mosquito. It does not "
                         "spread directly from person to person.",
        "prevention": ["Remove stagnant water around the home", "Use mosquito repellents",
                        "Sleep under mosquito nets", "Wear long sleeves/pants in mosquito-prone areas"],
        "myths_facts": [
            {"myth": "Dengue always causes a visible rash.",
             "fact": "Many dengue cases have no rash at all; fever and body pain are more common."},
            {"myth": "You can only get dengue once in your life.",
             "fact": "You can be infected multiple times, and a second infection can be more severe."},
        ],
        "when_to_seek_care": "Seek medical attention promptly if fever is accompanied by warning "
                              "signs such as bleeding, severe abdominal pain, or persistent vomiting.",
        "source": "General public-health guidance (WHO/NVBDCP-style disease fact sheets)",
        "last_updated": "2026",
    },
    "malaria": {
        "name": "Malaria",
        "overview": "Malaria is a life-threatening disease caused by Plasmodium parasites, "
                     "transmitted through the bite of infected female Anopheles mosquitoes.",
        "symptoms": ["Fever with chills", "Sweating", "Headache", "Nausea and vomiting",
                     "Muscle pain", "Fatigue"],
        "warning_signs": ["Confusion or altered consciousness", "Repeated seizures",
                           "Difficulty breathing", "Very high fever", "Dark or bloody urine"],
        "transmission": "Spread by the bite of an infected Anopheles mosquito, mostly active "
                         "between dusk and dawn.",
        "prevention": ["Use insecticide-treated bed nets", "Indoor residual spraying",
                        "Avoid standing water near homes", "Take prophylactic medication if "
                        "advised before travel to endemic areas"],
        "myths_facts": [
            {"myth": "Malaria spreads through dirty water or food.",
             "fact": "Malaria spreads only through mosquito bites, not through water or food."},
            {"myth": "Malaria is not serious and needs no treatment.",
             "fact": "Untreated malaria, especially P. falciparum, can be fatal within days."},
        ],
        "when_to_seek_care": "Any fever in a malaria-endemic area should be tested promptly; "
                              "seek urgent care if confusion, breathlessness, or repeated "
                              "vomiting occurs.",
        "source": "General public-health guidance (WHO/NVBDCP-style disease fact sheets)",
        "last_updated": "2026",
    },
    "tuberculosis": {
        "name": "Tuberculosis (TB)",
        "overview": "TB is a bacterial infection caused by Mycobacterium tuberculosis that "
                     "most often affects the lungs and spreads through the air.",
        "symptoms": ["Persistent cough lasting more than 2-3 weeks", "Coughing up blood or sputum",
                     "Chest pain", "Unexplained weight loss", "Night sweats", "Fever", "Fatigue"],
        "warning_signs": ["Coughing up blood", "Severe difficulty breathing",
                           "Rapid, unexplained weight loss"],
        "transmission": "Spreads through the air when a person with active pulmonary TB coughs, "
                         "sneezes, or speaks, releasing droplets containing the bacteria.",
        "prevention": ["BCG vaccination in infants (per national guidelines)",
                        "Good ventilation in living/working spaces",
                        "Prompt treatment of active cases to reduce spread",
                        "Covering mouth while coughing"],
        "myths_facts": [
            {"myth": "TB is hereditary and passed through genes.",
             "fact": "TB is an infectious bacterial disease, not a genetic condition."},
            {"myth": "TB is always fatal.",
             "fact": "TB is curable with a full course of prescribed antibiotics."},
        ],
        "when_to_seek_care": "See a doctor if a cough persists beyond 2-3 weeks, especially with "
                              "blood, weight loss, or night sweats.",
        "source": "General public-health guidance (WHO/National TB Elimination Programme-style facts)",
        "last_updated": "2026",
    },
    "covid19": {
        "name": "COVID-19",
        "overview": "COVID-19 is a respiratory illness caused by the SARS-CoV-2 virus, spreading "
                     "mainly through respiratory droplets and close contact.",
        "symptoms": ["Fever", "Dry cough", "Fatigue", "Loss of taste or smell",
                     "Sore throat", "Body aches", "Headache"],
        "warning_signs": ["Difficulty breathing or shortness of breath", "Persistent chest pain",
                           "Bluish lips or face", "Confusion or inability to stay awake"],
        "transmission": "Spreads mainly through respiratory droplets and aerosols released when "
                         "an infected person coughs, sneezes, talks, or breathes, and via close contact.",
        "prevention": ["Vaccination as per current national guidance", "Hand hygiene",
                        "Wearing masks in crowded/high-risk indoor settings",
                        "Ventilating indoor spaces", "Isolating when symptomatic"],
        "myths_facts": [
            {"myth": "Drinking alcohol or hot water kills the coronavirus in the body.",
             "fact": "There is no evidence that alcohol consumption or hot water prevents or "
                     "cures COVID-19; vaccination and standard precautions are effective measures."},
            {"myth": "Only elderly people can get seriously ill from COVID-19.",
             "fact": "People of any age can develop severe illness, though risk is higher in "
                     "older adults and those with underlying conditions."},
        ],
        "when_to_seek_care": "Seek urgent care for breathing difficulty, persistent chest pain, "
                              "confusion, or bluish lips/face.",
        "source": "General public-health guidance (WHO/MoHFW-style advisories)",
        "last_updated": "2026",
    },
    "cholera": {
        "name": "Cholera",
        "overview": "Cholera is an acute diarrheal illness caused by ingesting food or water "
                     "contaminated with the bacterium Vibrio cholerae.",
        "symptoms": ["Sudden, watery diarrhea", "Vomiting", "Rapid dehydration", "Muscle cramps"],
        "warning_signs": ["Signs of severe dehydration (sunken eyes, dry mouth, little/no urine)",
                           "Rapid heartbeat", "Extreme thirst", "Lethargy or confusion"],
        "transmission": "Spreads through contaminated drinking water or food, often linked to "
                         "poor sanitation infrastructure.",
        "prevention": ["Drink safe/boiled or treated water", "Practice good hand hygiene",
                        "Proper sanitation and safe food handling", "Cholera vaccination where advised"],
        "myths_facts": [
            {"myth": "Cholera spreads through the air like a cold.",
             "fact": "Cholera spreads through contaminated water or food, not through the air."},
        ],
        "when_to_seek_care": "Seek care immediately for profuse watery diarrhea with signs of "
                              "dehydration; oral/IV rehydration is time-critical.",
        "source": "General public-health guidance (WHO-style disease fact sheets)",
        "last_updated": "2026",
    },
    "typhoid": {
        "name": "Typhoid Fever",
        "overview": "Typhoid is a bacterial infection caused by Salmonella Typhi, spread through "
                     "contaminated food and water.",
        "symptoms": ["Sustained high fever", "Weakness", "Stomach pain", "Headache",
                     "Loss of appetite", "Constipation or diarrhea"],
        "warning_signs": ["Severe abdominal pain and swelling", "Confusion",
                           "Blood in stool", "Signs of intestinal bleeding"],
        "transmission": "Spreads via food or water contaminated with the feces of an infected "
                         "person, or through poor hand hygiene during food preparation.",
        "prevention": ["Drink safe water", "Typhoid vaccination where recommended",
                        "Good hand hygiene", "Proper food handling and sanitation"],
        "myths_facts": [
            {"myth": "Typhoid always causes a visible skin rash that's easy to spot.",
             "fact": "A rash can occur but is often subtle or absent; sustained fever is the "
                     "more consistent sign."},
        ],
        "when_to_seek_care": "See a doctor for fever lasting several days, especially with "
                              "severe abdominal pain or suspected bleeding.",
        "source": "General public-health guidance (WHO-style disease fact sheets)",
        "last_updated": "2026",
    },
    "influenza": {
        "name": "Influenza (Flu)",
        "overview": "Influenza is a contagious respiratory illness caused by influenza viruses, "
                     "circulating seasonally in most regions.",
        "symptoms": ["Fever", "Chills", "Cough", "Sore throat", "Runny or stuffy nose",
                     "Muscle aches", "Fatigue"],
        "warning_signs": ["Difficulty breathing", "Persistent chest pain or pressure",
                           "Severe or persistent vomiting", "Symptoms that improve then return worse"],
        "transmission": "Spreads through respiratory droplets from coughing, sneezing, or "
                         "talking, and via contaminated surfaces.",
        "prevention": ["Annual flu vaccination where recommended", "Hand hygiene",
                        "Covering coughs and sneezes", "Staying home when symptomatic"],
        "myths_facts": [
            {"myth": "The flu is just a bad cold and never dangerous.",
             "fact": "Influenza can lead to serious complications, especially in young children, "
                     "older adults, and people with chronic conditions."},
        ],
        "when_to_seek_care": "Seek care for breathing difficulty, chest pain, or symptoms that "
                              "worsen after initially improving.",
        "source": "General public-health guidance (WHO-style disease fact sheets)",
        "last_updated": "2026",
    },
    "japanese_encephalitis": {
        "name": "Japanese Encephalitis",
        "overview": "Japanese encephalitis (JE) is a viral brain infection spread by Culex "
                     "mosquitoes, most common in rural, rice-farming and pig-rearing regions.",
        "symptoms": ["Fever", "Headache", "Vomiting", "Confusion", "Neck stiffness"],
        "warning_signs": ["Seizures", "Severe confusion or reduced consciousness",
                           "Difficulty moving limbs", "High fever with stiff neck"],
        "transmission": "Spreads through the bite of infected Culex mosquitoes, which typically "
                         "breed in flooded rice fields and stagnant water.",
        "prevention": ["JE vaccination as per national immunization schedule",
                        "Mosquito nets and repellents", "Reducing stagnant water near homes"],
        "myths_facts": [
            {"myth": "JE spreads directly from person to person.",
             "fact": "JE spreads only via mosquito bites, not from person to person."},
        ],
        "when_to_seek_care": "Seek emergency care immediately for fever with confusion, seizures, "
                              "or neck stiffness.",
        "source": "General public-health guidance (WHO-style disease fact sheets)",
        "last_updated": "2026",
    },
    "hepatitis": {
        "name": "Hepatitis (A/E, common food/water-borne types)",
        "overview": "Viral hepatitis refers to inflammation of the liver caused by hepatitis "
                     "viruses (A-E); hepatitis A and E commonly spread via contaminated food and water.",
        "symptoms": ["Fatigue", "Nausea", "Abdominal discomfort", "Loss of appetite",
                     "Yellowing of skin/eyes (jaundice)", "Dark urine"],
        "warning_signs": ["Severe abdominal pain", "Persistent vomiting", "Confusion",
                           "Marked yellowing of skin/eyes", "Easy bruising or bleeding"],
        "transmission": "Hepatitis A/E spread through contaminated food or water; other types "
                         "(B, C) spread through blood or body fluids.",
        "prevention": ["Safe drinking water and food hygiene", "Hepatitis A/B vaccination where "
                        "available", "Avoiding sharing needles/razors", "Safe medical/blood practices"],
        "myths_facts": [
            {"myth": "All types of hepatitis spread the same way.",
             "fact": "Transmission differs by type: A and E mainly through contaminated food/"
                     "water, B and C mainly through blood and body fluids."},
        ],
        "when_to_seek_care": "See a doctor for persistent jaundice, severe abdominal pain, or "
                              "confusion.",
        "source": "General public-health guidance (WHO-style disease fact sheets)",
        "last_updated": "2026",
    },
    "chikungunya": {
        "name": "Chikungunya",
        "overview": "Chikungunya is a mosquito-borne viral illness transmitted by Aedes "
                     "mosquitoes, characterized by fever and severe joint pain.",
        "symptoms": ["Sudden high fever", "Severe joint pain", "Muscle pain", "Headache",
                     "Rash", "Joint swelling"],
        "warning_signs": ["Severe, disabling joint pain lasting weeks",
                           "Signs of dehydration", "High persistent fever"],
        "transmission": "Spread through the bite of infected Aedes mosquitoes, the same species "
                         "that spreads dengue.",
        "prevention": ["Eliminate mosquito breeding sites", "Use repellents and nets",
                        "Wear protective clothing in mosquito-prone areas"],
        "myths_facts": [
            {"myth": "Joint pain from chikungunya always goes away within a few days.",
             "fact": "Joint pain can persist for weeks to months in some people after the "
                     "initial infection clears."},
        ],
        "when_to_seek_care": "See a doctor if fever is high/persistent or joint pain is severe "
                              "and disabling.",
        "source": "General public-health guidance (WHO-style disease fact sheets)",
        "last_updated": "2026",
    },
}


def iter_chunks():
    """
    Yield (disease_key, field_name, text) chunks used to build the
    RAG retrieval index. Keeping fields as separate chunks means the
    retriever can pull just the relevant slice of a disease's info
    (e.g. only "prevention") instead of the whole entry.
    """
    for key, d in DISEASES.items():
        yield key, "overview", f"{d['name']} overview: {d['overview']}"
        yield key, "symptoms", f"{d['name']} symptoms: " + "; ".join(d["symptoms"])
        yield key, "warning_signs", f"{d['name']} warning signs: " + "; ".join(d["warning_signs"])
        yield key, "transmission", f"{d['name']} transmission: {d['transmission']}"
        yield key, "prevention", f"{d['name']} prevention: " + "; ".join(d["prevention"])
        for mf in d["myths_facts"]:
            yield key, "myths_facts", f"{d['name']} myth: {mf['myth']} Fact: {mf['fact']}"
        yield key, "when_to_seek_care", f"{d['name']} when to seek care: {d['when_to_seek_care']}"


ALL_MYTHS = [
    (key, mf["myth"], mf["fact"])
    for key, d in DISEASES.items()
    for mf in d["myths_facts"]
]
