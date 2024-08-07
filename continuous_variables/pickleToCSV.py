import pandas as pd
import numpy as np
from collections import defaultdict
import csv


def flatten_data(subject_id, data, indexToCode, idToLabel, d_icd_diagnoses, d_icd_procedures):
    '''Function to flatten data such that each row consists of one visit per subject
    '''
    flattened = []
    visit_number = 1
    
    # Ensure ICD9_CODE in both dataframes is string type
    d_icd_procedures['ICD9_CODE'] = d_icd_procedures['ICD9_CODE'].astype(str)
    d_icd_diagnoses['ICD9_CODE'] = d_icd_diagnoses['ICD9_CODE'].astype(str)
    
    for i, visit in enumerate(data['visits']):
        diagnosis_codes, lab_names, lab_values, time_since_last = visit
        if i == 0:
            age = time_since_last[0]
            time_since_last = np.nan
        else:
            time_since_last = time_since_last[0]

        # Convert the diagnosis codes to true medical codes
        all_codes = [indexToCode[code] if code in indexToCode else code for code in diagnosis_codes]

        # Process labels
        medication_labels = []
        diagnosis_labels = []
        procedure_labels = []
        
        for code in all_codes:
            code_str = str(code)  # Convert all codes to string for consistency
            
            # Check diagnoses first (to catch E-codes and other alphanumeric codes)
            matching_diag = d_icd_diagnoses[d_icd_diagnoses['ICD9_CODE'] == code_str]
            if not matching_diag.empty:
                diagnosis_labels.append(matching_diag['SHORT_TITLE'].iloc[0])
                continue
            
            # If not in diagnoses, check procedures
            matching_proc = d_icd_procedures[d_icd_procedures['ICD9_CODE'] == code_str]
            if not matching_proc.empty:
                procedure_labels.append(matching_proc['SHORT_TITLE'].iloc[0])
                continue
            
            # If it's a numeric string, try to match without leading zeros
            if code_str.replace(".", "").isdigit():
                code_int = str(int(float(code_str)))  # Remove leading zeros
                matching_diag = d_icd_diagnoses[d_icd_diagnoses['ICD9_CODE'] == code_int]
                if not matching_diag.empty:
                    diagnosis_labels.append(matching_diag['SHORT_TITLE'].iloc[0])
                else:
                    matching_proc = d_icd_procedures[d_icd_procedures['ICD9_CODE'] == code_int]
                    if not matching_proc.empty:
                        procedure_labels.append(matching_proc['SHORT_TITLE'].iloc[0])
            else:
                # If it's not a numeric code and not found in diagnoses or procedures, assume it's a medication
                medication_labels.append(code_str)

        row = defaultdict(str)
        row['Visit Number'] = visit_number
        row['Age'] = age
        row['Time Since Last Visit'] = time_since_last
        row['Medication Labels'] = ', '.join(medication_labels)
        row['Diagnosis Labels'] = ', '.join(diagnosis_labels)
        row['Procedure Labels'] = ', '.join(procedure_labels)
        row['Subject ID'] = subject_id
        for name, value in zip(lab_names, lab_values):
            row[name] = value

        for i, label in enumerate(data['labels']):
            label_name = None
            if i in idToLabel:
                label_name = idToLabel[i]
            row[label_name] = label

        flattened.append(row)
        visit_number += 1
    return flattened


def write_to_csv(data, output_file):
    '''Function to update column names and save each row to .csv
    '''
    fieldnames = set()
    for subject_data in data:
        for row in subject_data:
            fieldnames.update(row.keys())
    fieldnames = {str(item) for item in fieldnames}
    fieldnames = sorted(list(fieldnames))

    with open(output_file, 'w', newline = '') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames = fieldnames)
        writer.writeheader()
        for subject_data in data:
            for row in subject_data:
                writer.writerow((row))

def main():
    path_to_pkl = "./continuous_variables/results/datasets/haloDataset_convertedv3.pkl" #path to file generated after running discretized_convert.py
    subjects_data = pd.read_pickle(path_to_pkl)
    indexToCode = pd.read_pickle("./continuous_variables/data/indexToCode.pkl") #path to indexToCode file generated by genDatasetContinuous.py
    idToLabel = pd.read_pickle('./continuous_variables/data/idToLabel.pkl') #path to idToLabel file generated by genDatasetContinuous.py
    d_icd_diagnoses = pd.read_csv('./continuous_variables/data/D_ICD_DIAGNOSES.csv') #path to ICD9 diagnoses codes (to be downloaded and extracted for MIMIC-III from physionet)
    d_icd_procedures = pd.read_csv('./continuous_variables/data/D_ICD_PROCEDURES.csv') #path to ICD9 procedure codes (to be downloaded and extracted for MIMIC-III from physionet)

    all_subjects_data = []
    for subject_id, subject_data in enumerate(subjects_data, start = 1): #Assign subject IDs starting with 1
        flattened_data = flatten_data(subject_id, subject_data, indexToCode, idToLabel, d_icd_diagnoses, d_icd_procedures)
        all_subjects_data.append(flattened_data)

    write_to_csv(all_subjects_data, './continuous_variables/results/datasets/haloDataset_convertedv3.csv') #path to save final .csv

main()
