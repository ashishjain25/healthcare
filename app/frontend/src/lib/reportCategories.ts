export interface CategoryOption {
  value: string;
  label: string;
}

export interface CategoryGroup {
  group: string;
  options: CategoryOption[];
}

export const OTHER_CATEGORY = "__other__";

// Every category a report can be filed under, grouped only for readability
// in the dropdown — picking a category is independent of the selected
// Report type (a doctor can log a "Cardiology Consultation" physician note
// alongside a "lab" report_type, etc.). Intentionally broader than what
// scripts/seed_data.py happens to seed — a real user can file a report
// under any of these, not just categories that already have reports.
export const REPORT_CATEGORY_GROUPS: CategoryGroup[] = [
  {
    group: "Lab",
    options: [
      { value: "cbc", label: "CBC (Complete Blood Count)" },
      { value: "lft", label: "LFT (Liver Function Test)" },
      { value: "kft", label: "KFT (Kidney Function Test)" },
      { value: "thyroid", label: "Thyroid Panel" },
      { value: "blood_sugar", label: "Blood Sugar / Glucose" },
      { value: "hba1c", label: "HbA1c" },
      { value: "lipid_profile", label: "Lipid Profile" },
      { value: "urinalysis", label: "Urinalysis" },
      { value: "vitamin_d", label: "Vitamin D" },
      { value: "vitamin_b12", label: "Vitamin B12" },
      { value: "electrolyte_panel", label: "Electrolyte Panel" },
      { value: "coagulation_profile", label: "Coagulation Profile" },
      { value: "bmi", label: "BMI Report" },
      { value: "heart_disease", label: "Heart Disease Panel" },
    ],
  },
  {
    group: "Radiology & imaging",
    options: [
      { value: "chest_xray", label: "Chest X-Ray" },
      { value: "ct_brain", label: "CT Brain Scan" },
      { value: "ct_chest", label: "CT Chest" },
      { value: "ct_abdomen", label: "CT Abdomen" },
      { value: "mri_spine", label: "MRI Spine" },
      { value: "mri_brain", label: "MRI Brain" },
      { value: "mri_knee", label: "MRI Knee" },
      { value: "ultrasound_abdomen", label: "Ultrasound Abdomen" },
      { value: "prostate_ultrasound", label: "Prostate Ultrasound" },
      { value: "mammography", label: "Mammography" },
      { value: "bone_density_scan", label: "Bone Density Scan (DEXA)" },
      { value: "ecg", label: "ECG / EKG" },
      { value: "echocardiogram", label: "Echocardiogram" },
    ],
  },
  {
    group: "Physician note",
    options: [
      { value: "asthma", label: "Asthma" },
      { value: "allergy_review", label: "Allergy Review" },
      { value: "diabetes_followup", label: "Diabetes Follow-up" },
      { value: "hypertension_followup", label: "Hypertension Follow-up" },
      { value: "general_consultation", label: "General Consultation" },
      { value: "cardiology_consultation", label: "Cardiology Consultation" },
    ],
  },
  {
    group: "Discharge",
    options: [{ value: "discharge_summary", label: "Discharge Summary" }],
  },
];
