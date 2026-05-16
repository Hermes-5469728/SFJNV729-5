"""AC Medical Clinical Scoring Engine - 9 validated scores
迁移自: core/scores.py"""
from typing import Tuple

def cha2ds2_vasc(age, sex_female, chf, htn, stroke_tia, vascular_dm, dm) -> Tuple[int, str]:
    score = 0
    if chf: score += 1
    if htn: score += 1
    if age >= 75: score += 2
    elif age >= 65: score += 1
    if dm: score += 1
    if stroke_tia: score += 2
    if vascular_dm: score += 1
    if sex_female: score += 1
    if score == 0: risk = "Low · 0%/yr · No anticoagulation"
    elif score == 1: risk = "Low-Moderate · ~1.3%/yr · Consider OAC"
    elif score >= 2: risk = "High · >=2.2%/yr · OAC recommended (DOAC preferred)"
    return score, risk

def has_bled(htn, renal, liver, stroke, bleed, inr, age65, alc, asa_nsaid) -> Tuple[int, str]:
    score = sum([htn, renal, liver, stroke, bleed, inr, age65, alc, asa_nsaid])
    if score >= 3: risk = "High (>=3.7%/yr) · Reassess OAC"
    elif score == 2: risk = "Moderate (~2%/yr) · Caution"
    else: risk = "Low (<2%/yr)"
    return score, risk

def wells_dvt(cancer, bed, calf, collat, leg, pit, prev, alt_likely) -> Tuple[int, str]:
    score = cancer + bed + calf + collat + leg + pit + prev
    if not alt_likely: score -= 2
    if score <= 0: risk = "Low (~3%) · D-dimer"
    elif score <= 2: risk = "Moderate (~17%) · D-dimer + US"
    else: risk = "High (~75%) · US immediately"
    return score, risk

def wells_pe(dvt, pe1, hr100, immob, prev, hemoptysis, cancer) -> Tuple[float, str]:
    score = dvt*3 + pe1*3 + hr100*1.5 + immob*1.5 + prev*1.5 + hemoptysis + cancer
    risk = "PE unlikely · D-dimer" if score <= 4 else "PE likely · CTPA"
    return score, risk

def curb65(conf, bun, rr, bp, age65) -> Tuple[int, str]:
    score = sum([conf, bun, rr, bp, age65])
    if score <= 1: risk = "Low (1.5% 30-day mort) · Outpatient"
    elif score == 2: risk = "Moderate (9%) · Short inpatient"
    else: risk = "Severe (22%) · Hospitalize · ICU if 4-5"
    return score, risk

def gcs(eye, verbal, motor) -> Tuple[int, str]:
    score = eye + verbal + motor
    sev = {15: "Normal", 13: "Mild TBI", 9: "Moderate TBI", 3: "Severe · Intubate"}
    for k, v in sorted(sev.items(), reverse=True):
        if score >= k: return score, v
    return score, "Invalid"

def child_pugh(bili, alb, inr_val, ascites, enceph) -> Tuple[int, str]:
    score = 0
    score += 1 if bili < 2 else (2 if bili <= 3 else 3)
    score += 1 if alb > 3.5 else (2 if alb >= 2.8 else 3)
    score += 1 if inr_val < 1.7 else (2 if inr_val <= 2.2 else 3)
    asc_map = {"none": 1, "mild": 2, "moderate-severe": 3}
    enc_map = {"none": 1, "mild-moderate": 2, "severe": 3}
    score += asc_map.get(ascites, 1) + enc_map.get(enceph, 1)
    if score <= 6: grade = "A · Well-compensated · 100% 1-yr"
    elif score <= 9: grade = "B · Significant · 80% 1-yr"
    else: grade = "C · Decompensated · 45% 1-yr"
    return score, grade

def timi_nstemi(age65, cad3, asa7d, angina, st, marker) -> Tuple[int, str]:
    score = sum([age65, cad3, asa7d, angina, st, marker])
    if score <= 1: risk = "Low (<5% 14d) · Discharge"
    elif score <= 3: risk = "Intermediate (8-13%) · Admit"
    else: risk = "High (>20%) · Invasive (within 24h)"
    return score, risk

def abcd2(age60, bp140, clin, dur_min, dm) -> Tuple[int, str]:
    score = age60 + bp140 + dm
    if clin == "unilateral": score += 2
    elif clin == "speech_only": score += 1
    if dur_min >= 60: score += 2
    elif dur_min >= 10: score += 1
    if score <= 3: risk = "Low (1% 2d stroke) · Outpatient"
    elif score <= 5: risk = "Moderate (4%) · Consider admission"
    else: risk = "High (8%) · Admit"
    return score, risk

SCORE_FUNCTIONS = {
    "cha2ds2_vasc": cha2ds2_vasc,
    "has_bled": has_bled,
    "wells_dvt": wells_dvt,
    "wells_pe": wells_pe,
    "curb65": curb65,
    "gcs": gcs,
    "child_pugh": child_pugh,
    "timi_nstemi": timi_nstemi,
    "abcd2": abcd2,
}

CRCL_ADJUSTMENTS = {
    "metformin": [(60, "No adjustment"), (30, "Max 1000mg/day. Monitor renal function q3-6mo"),
                   (15, "CONTRAINDICATED. Stop metformin"), (0, "CONTRAINDICATED")],
    "enoxaparin": [(30, "Standard dose: 1mg/kg BID or 1.5mg/kg QD"),
                    (15, "Reduce to 1mg/kg QD. Monitor anti-Xa if >5 days"),
                    (0, "Reduce to 1mg/kg QD or use UFH")],
    "dabigatran": [(30, "Standard dose: 150mg BID"),
                    (15, "Reduce to 75mg BID (US) or consider alternative"),
                    (0, "CONTRAINDICATED if CrCl <15")],
    "rivaroxaban": [(50, "Standard dose: 20mg QD (AF) / 15mg BID (VTE acute)"),
                     (15, "Reduce to 15mg QD for AF (if CrCl 15-50)"),
                     (0, "CONTRAINDICATED if CrCl <15")],
    "apixaban": [(25, "Standard dose: 5mg BID"),
                   (15, "Standard dose unless: age>=80 + wt<=60 + Cr>=1.5 (then 2.5mg BID)"),
                   (0, "Use with caution. Limited data at CrCl <15")],
}

def calculate_score(score_type: str, params: dict) -> Tuple[int, str]:
    if score_type not in SCORE_FUNCTIONS:
        return 0, f"Unknown score type: {score_type}"
    return SCORE_FUNCTIONS[score_type](**params)

def check_crcl_adjustment(drug_name: str, crcl: float) -> str:
    drug_lower = drug_name.lower()
    for drug_key, adjustments in CRCL_ADJUSTMENTS.items():
        if drug_key in drug_lower:
            for threshold, recommendation in adjustments:
                if crcl >= threshold:
                    return recommendation
    return "No specific adjustment recommended"
