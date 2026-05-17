export const PARSER_VERSION = "v6.0.0-alpha";

export const RECORD_STARTERS = [
  "Progress Note",
  "Consult",
  "Admission Note",
  "Discharge Summary",
  "Procedure Note",
  "Operation Note",
  "Imaging Report",
  "Pathology Report",
];

export const NOTE_TITLE_PATTERNS = [
  /progress note/i,
  /consult/i,
  /admission note/i,
  /discharge summary/i,
  /soap/i,
];

export const IMAGING_KEYWORDS = [
  "CT",
  "MRI",
  "PET",
  "X-ray",
  "Ultrasound",
  "초음파",
  "Findings",
  "Impression",
];

export const IMAGING_MODALITY_TITLES = [
  "CT",
  "MRI",
  "PET",
  "X-ray",
  "Ultrasound",
  "초음파",
];

export const PATHOLOGY_KEYWORDS = [
  "Pathology",
  "Biopsy",
  "Specimen",
  "Diagnosis",
  "Gross",
  "Microscopic",
  "Cytology",
];

export const LAB_SECTION_HINTS = [
  "cbc",
  "chemistry",
  "hematology",
  "electrolyte",
  "liver",
  "renal",
  "thyroid",
  "endocrine",
  "cardiac marker",
  "abga",
  "ua",
  "urinalysis",
];

export const MEDICATION_KEYWORDS = [
  "PO",
  "IV",
  "BID",
  "TID",
  "qd",
  "daily",
  "mg",
  "tab",
  "cap",
  "inj",
];

export const LAB_KEYWORDS_SAFE = [
  "HbA1c",
  "Glucose",
  "Albumin",
  "Protein",
  "Bilirubin",
  "Troponin",
  "D-dimer",
  "Lactate",
  "CRP",
  "ESR",
];

export const LAB_KEYWORDS_STRICT = [
  "BUN",
  "Cr",
  "GFR",
  "Na",
  "K",
  "Cl",
  "Ca",
  "Phos",
  "WBC",
  "Hb",
  "Hgb",
  "Plt",
  "AST",
  "ALT",
  "ALP",
  "BNP",
  "PCT",
  "LDH",
  "PT",
  "aPTT",
  "INR",
  "pH",
  "pCO2",
  "pO2",
  "HCO3",
];

export const SECTION_CANONICAL_MAP: Record<string, string> = {
  Problem: "Problem",
  Plan: "Plan",
  Assessment: "Assessment",
  SOAP: "SOAP",
  주호소: "Chief Complaint",
  현병력: "History of Present Illness",
  과거력: "Past History",
  의뢰내용: "Referral",
  회신내용: "Response",
  Findings: "Findings",
  Impression: "Impression",
  Diagnosis: "Diagnosis",
};
