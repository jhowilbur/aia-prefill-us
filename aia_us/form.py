"""The OMB M-25-21 Section 4(b)(ii) impact-assessment items, quoted from the memo.

Source: OMB M-25-21, "Accelerating Federal Use of AI through Innovation, Governance, and Public
Trust" (April 3, 2025), Appendix Section 4(b)(ii). PDF SHA-256
0aab0aa4eaeac969ed93894d3940c5dc9d0b7377048171b164a439e8b9e49813 (see data/SOURCES.csv).
Page numbers are the memo's printed page numbers (they equal the PDF page index).
The PDF is an OCR'd scan; quotes fix only OCR spacing ("ofthe" -> "of the", "AI' s" -> "AI's").
Footnote marker 30 after item C is dropped.
"""
from __future__ import annotations

MEMO = "OMB M-25-21, Appendix, Section 4(b)(ii)"

LEAD_IN = {
    "page": 16,
    "quote": ("Agencies must complete an AI impact assessment before deploying any high-impact AI use case. "
              "These assessments must be updated periodically and throughout the AI's lifecycle, as appropriate, "
              "using target variables that anticipate real-world outcomes. The AI impact assessments must be "
              "documented and address or include, at a minimum:"),
}

ITEMS = [
    {"id": "A", "key": "purpose_and_benefit", "title": "Intended purpose and expected benefit", "page": 16,
     "quote": ("the intended purpose for the AI and its expected benefit, supported by specific metrics or qualitative "
               "analysis, assessing impact inclusive of but not limited to costs, customer experience, or expected "
               "positive outcomes of AI use, as compared to existing agency processes;")},
    {"id": "B", "key": "data_and_model", "title": "Quality and appropriateness of data and model capability", "page": 16,
     "quote": ("the quality and appropriateness of the relevant data and model capability, supported by a summary of the "
               "data used in the AI's design, development, training, testing, and operation and its fitness for the AI's "
               "intended purpose; describe the data collection, and preparation process; and indicate whether the data "
               "is to be publicly disclosed as an open government data asset. When applicable, this summary must "
               "describe information included in the data about classes protected by Federal nondiscrimination laws;")},
    {"id": "C", "key": "potential_impacts", "title": "Potential impacts of using AI", "page": 16,
     "quote": ("the potential impacts of using AI, supported by documentation on potential impacts on the privacy, civil "
               "rights, and civil liberties of the public, and of using or not using AI. The assessment should reference "
               "privacy impact assessments, CAIO-approved minimum risk management practice waivers or other materials, "
               "if relevant, and also describe any planned mitigation measures for anticipated negative impacts, such as "
               "unlawful discrimination;")},
    {"id": "D", "key": "reassessment", "title": "Reassessment scheduling and procedures", "page": 16,
     "quote": ("reassessment scheduling and procedures, supported by schedules for periodic reassessments as well as "
               "reassessment requirements following significant modifications to an underlying AI system, in addition "
               "to the specific requirements and processes for such testing;")},
    {"id": "E", "key": "costs", "title": "Related costs analysis", "page": 16,
     "quote": "related costs analysis, supported by a summary of direct costs associated and expected savings, if any;"},
    {"id": "F", "key": "independent_review", "title": "Results of independent review", "page": 16,
     "quote": ("results of independent review, supported by an independent reviewer within the agency who has not been "
               "involved in the development. The independent reviewer of the impact assessment shall identify any "
               "potential concerns or gaps. Any comments provided by the independent reviewer must be included in the "
               "impact assessment documentation and shared with the individual accepting the risk for the AI use case "
               "when that determination is made; and")},
    {"id": "G", "key": "risk_acceptance", "title": "Risk acceptance", "page": 17,
     "quote": "risk acceptance, supported by a signature from the individual accepting the risk."},
]

ITEM_IDS = [i["id"] for i in ITEMS]
STATUSES = ["not started", "in progress", "complete"]

# High-impact status options, worded as in the 2025 inventory data call (data_dictionary.md, column is_high_impact).
HIGH_IMPACT_STATUSES = ["High-impact", "Presumed high-impact, but determined not high impact", "Not high-impact"]
DOWNGRADE_STATUS = HIGH_IMPACT_STATUSES[1]

HEADER_FIELDS = [
    ("agency", "Agency"),
    ("use_case_id", "Use case ID"),
    ("use_case_name", "Use case name"),
    ("development_stage", "Development stage"),
    ("high_impact_status", "High-impact status"),
    ("high_impact_justification", "Justification if determined not high-impact"),
    ("assessment_date", "Assessment date"),
]
G_EXTRA = [("signatory_title", "Signatory title"), ("signature_date", "Signature date")]
