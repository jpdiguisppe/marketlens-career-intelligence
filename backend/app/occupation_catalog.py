"""Deterministic cross-sector occupation interpretation for MarketLens.

The major-group taxonomy follows the U.S. Bureau of Labor Statistics 2018
Standard Occupational Classification (SOC). The curated canonical and alternate
titles are a compact product index modeled after the O*NET occupation and job
title datasets. Raw O*NET data is not fetched at request time, which keeps search
private, deterministic, fast, and available when upstream services are down.

This module does not decide whether a current job posting exists. It only answers
whether MarketLens understood the requested occupation and which title variants
are safe to use for provider routing and strict result filtering.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from typing import Literal

InterpretationStatus = Literal["recognized", "ambiguous", "unrecognized"]

SOC_MAJOR_GROUPS: dict[str, str] = {'11': 'Management Occupations',
 '13': 'Business and Financial Operations Occupations',
 '15': 'Computer and Mathematical Occupations',
 '17': 'Architecture and Engineering Occupations',
 '19': 'Life, Physical, and Social Science Occupations',
 '21': 'Community and Social Service Occupations',
 '23': 'Legal Occupations',
 '25': 'Educational Instruction and Library Occupations',
 '27': 'Arts, Design, Entertainment, Sports, and Media Occupations',
 '29': 'Healthcare Practitioners and Technical Occupations',
 '31': 'Healthcare Support Occupations',
 '33': 'Protective Service Occupations',
 '35': 'Food Preparation and Serving Related Occupations',
 '37': 'Building and Grounds Cleaning and Maintenance Occupations',
 '39': 'Personal Care and Service Occupations',
 '41': 'Sales and Related Occupations',
 '43': 'Office and Administrative Support Occupations',
 '45': 'Farming, Fishing, and Forestry Occupations',
 '47': 'Construction and Extraction Occupations',
 '49': 'Installation, Maintenance, and Repair Occupations',
 '51': 'Production Occupations',
 '53': 'Transportation and Material Moving Occupations',
 '55': 'Military Specific Occupations'}

@dataclass(frozen=True)
class OccupationConcept:
    key: str
    canonical_title: str
    soc_major_group: str
    search_family: str
    aliases: frozenset[str]

    @property
    def major_group_name(self) -> str:
        return SOC_MAJOR_GROUPS[self.soc_major_group]


@dataclass(frozen=True)
class OccupationInterpretation:
    status: InterpretationStatus
    original_query: str
    canonical_query: str
    occupation_phrase: str | None = None
    concept_key: str | None = None
    soc_major_group: str | None = None
    major_group_name: str | None = None
    search_family: str | None = None
    accepted_titles: tuple[str, ...] = ()
    suggestions: tuple[str, ...] = ()
    reason: str = ""

    @property
    def recognized(self) -> bool:
        return self.status == "recognized"


OCCUPATIONS: tuple[OccupationConcept, ...] = (
    OccupationConcept('general_manager', 'general manager', '11', 'operations', frozenset(('general manager', 'operations manager', 'business manager'))),
    OccupationConcept('project_manager', 'project manager', '11', 'operations', frozenset(('project manager', 'program manager'))),
    OccupationConcept('human_resources_manager', 'human resources manager', '11', 'operations', frozenset(('human resources manager', 'hr manager', 'people operations manager'))),
    OccupationConcept('marketing_manager', 'marketing manager', '11', 'marketing', frozenset(('marketing manager', 'brand manager'))),
    OccupationConcept('financial_manager', 'financial manager', '11', 'finance', frozenset(('financial manager', 'finance manager', 'controller'))),
    OccupationConcept('construction_manager', 'construction manager', '11', 'operations', frozenset(('construction manager', 'construction project manager'))),
    OccupationConcept('medical_services_manager', 'medical and health services manager', '11', 'healthcare', frozenset(('medical and health services manager', 'healthcare administrator', 'medical practice manager'))),
    OccupationConcept('education_administrator', 'education administrator', '11', 'operations', frozenset(('education administrator', 'school administrator', 'principal'))),
    OccupationConcept('accountant', 'accountant', '13', 'finance', frozenset(('accountant', 'staff accountant', 'general ledger accountant'))),
    OccupationConcept('auditor', 'auditor', '13', 'finance', frozenset(('auditor', 'internal auditor', 'external auditor'))),
    OccupationConcept('financial_analyst', 'financial analyst', '13', 'finance', frozenset(('financial analyst', 'finance analyst', 'corporate financial analyst'))),
    OccupationConcept('business_analyst', 'business analyst', '13', 'operations', frozenset(('business analyst', 'business systems analyst'))),
    OccupationConcept('loan_officer', 'loan officer', '13', 'finance', frozenset(('loan officer', 'mortgage loan officer'))),
    OccupationConcept('claims_adjuster', 'claims adjuster', '13', 'finance', frozenset(('claims adjuster', 'insurance adjuster'))),
    OccupationConcept('market_research_analyst', 'market research analyst', '13', 'marketing', frozenset(('market research analyst', 'marketing research analyst'))),
    OccupationConcept('human_resources_specialist', 'human resources specialist', '13', 'operations', frozenset(('human resources specialist', 'hr specialist', 'recruiter', 'talent acquisition specialist'))),
    OccupationConcept('logistics_analyst', 'logistics analyst', '13', 'operations', frozenset(('logistics analyst', 'supply chain analyst'))),
    OccupationConcept('compliance_officer', 'compliance officer', '13', 'legal', frozenset(('compliance officer', 'compliance analyst', 'regulatory compliance specialist'))),
    OccupationConcept('software_engineer', 'software engineer', '15', 'software', frozenset(('software engineer', 'software developer', 'application developer'))),
    OccupationConcept('systems_application_engineer', 'systems application engineer', '15', 'software', frozenset(('systems application engineer', 'system application engineer', 'systems applications engineer', 'application systems engineer'))),
    OccupationConcept('web_developer', 'web developer', '15', 'software', frozenset(('web developer', 'frontend developer', 'backend developer', 'full stack developer'))),
    OccupationConcept('data_scientist', 'data scientist', '15', 'data', frozenset(('data scientist', 'machine learning scientist'))),
    OccupationConcept('data_analyst', 'data analyst', '15', 'data', frozenset(('data analyst', 'analytics analyst'))),
    OccupationConcept('database_administrator', 'database administrator', '15', 'data', frozenset(('database administrator', 'dba'))),
    OccupationConcept('information_security_analyst', 'information security analyst', '15', 'cybersecurity', frozenset(('information security analyst', 'cybersecurity analyst', 'security analyst'))),
    OccupationConcept('network_administrator', 'network administrator', '15', 'operations', frozenset(('network administrator', 'network engineer'))),
    OccupationConcept('computer_support_specialist', 'computer support specialist', '15', 'operations', frozenset(('computer support specialist', 'it support specialist', 'help desk technician'))),
    OccupationConcept('quality_assurance_engineer', 'quality assurance engineer', '15', 'software', frozenset(('quality assurance engineer', 'qa engineer', 'software test engineer'))),
    OccupationConcept('architect', 'architect', '17', 'design', frozenset(('architect', 'building architect'))),
    OccupationConcept('civil_engineer', 'civil engineer', '17', 'technology', frozenset(('civil engineer', 'municipal engineer'))),
    OccupationConcept('mechanical_engineer', 'mechanical engineer', '17', 'technology', frozenset(('mechanical engineer', 'mechanical design engineer'))),
    OccupationConcept('electrical_engineer', 'electrical engineer', '17', 'technology', frozenset(('electrical engineer', 'electronics engineer'))),
    OccupationConcept('chemical_engineer', 'chemical engineer', '17', 'technology', frozenset(('chemical engineer', 'process engineer'))),
    OccupationConcept('industrial_engineer', 'industrial engineer', '17', 'technology', frozenset(('industrial engineer', 'manufacturing engineer'))),
    OccupationConcept('biomedical_engineer', 'biomedical engineer', '17', 'technology', frozenset(('biomedical engineer', 'bioengineer'))),
    OccupationConcept('environmental_engineer', 'environmental engineer', '17', 'technology', frozenset(('environmental engineer',))),
    OccupationConcept('aerospace_engineer', 'aerospace engineer', '17', 'technology', frozenset(('aerospace engineer', 'aeronautical engineer'))),
    OccupationConcept('systems_engineer', 'systems engineer', '17', 'technology', frozenset(('systems engineer', 'system engineer'))),
    OccupationConcept('structural_engineer', 'structural engineer', '17', 'technology', frozenset(('structural engineer',))),
    OccupationConcept('engineering_technician', 'engineering technician', '17', 'operations', frozenset(('engineering technician', 'engineering technologist'))),
    OccupationConcept('biologist', 'biologist', '19', 'data', frozenset(('biologist', 'biological scientist'))),
    OccupationConcept('chemist', 'chemist', '19', 'data', frozenset(('chemist', 'analytical chemist'))),
    OccupationConcept('physicist', 'physicist', '19', 'data', frozenset(('physicist', 'research physicist'))),
    OccupationConcept('environmental_scientist', 'environmental scientist', '19', 'data', frozenset(('environmental scientist', 'environmental specialist'))),
    OccupationConcept('geologist', 'geologist', '19', 'data', frozenset(('geologist', 'geoscientist'))),
    OccupationConcept('epidemiologist', 'epidemiologist', '19', 'healthcare', frozenset(('epidemiologist', 'public health epidemiologist'))),
    OccupationConcept('economist', 'economist', '19', 'data', frozenset(('economist', 'economic analyst', 'research economist'))),
    OccupationConcept('statistician', 'statistician', '19', 'data', frozenset(('statistician', 'applied statistician'))),
    OccupationConcept('research_scientist', 'research scientist', '19', 'data', frozenset(('research scientist', 'scientist'))),
    OccupationConcept('laboratory_technician', 'laboratory technician', '19', 'operations', frozenset(('laboratory technician', 'lab technician', 'research technician'))),
    OccupationConcept('social_worker', 'social worker', '21', 'healthcare', frozenset(('social worker', 'clinical social worker'))),
    OccupationConcept('mental_health_counselor', 'mental health counselor', '21', 'healthcare', frozenset(('mental health counselor', 'behavioral health counselor'))),
    OccupationConcept('substance_abuse_counselor', 'substance abuse counselor', '21', 'healthcare', frozenset(('substance abuse counselor', 'addiction counselor'))),
    OccupationConcept('school_counselor', 'school counselor', '21', 'operations', frozenset(('school counselor', 'guidance counselor'))),
    OccupationConcept('community_service_manager', 'community service manager', '21', 'operations', frozenset(('community service manager', 'social services manager'))),
    OccupationConcept('community_health_worker', 'community health worker', '21', 'healthcare', frozenset(('community health worker', 'health outreach worker'))),
    OccupationConcept('case_manager', 'case manager', '21', 'operations', frozenset(('case manager', 'social service case manager'))),
    OccupationConcept('social_service_assistant', 'social service assistant', '21', 'operations', frozenset(('social service assistant', 'human services assistant'))),
    OccupationConcept('attorney', 'attorney', '23', 'legal', frozenset(('attorney', 'lawyer', 'associate attorney'))),
    OccupationConcept('paralegal', 'paralegal', '23', 'legal', frozenset(('paralegal', 'legal paraprofessional'))),
    OccupationConcept('legal_assistant', 'legal assistant', '23', 'legal', frozenset(('legal assistant', 'legal secretary'))),
    OccupationConcept('law_clerk', 'law clerk', '23', 'legal', frozenset(('law clerk', 'judicial law clerk'))),
    OccupationConcept('court_reporter', 'court reporter', '23', 'legal', frozenset(('court reporter', 'stenographer'))),
    OccupationConcept('legal_operations_specialist', 'legal operations specialist', '23', 'legal', frozenset(('legal operations specialist', 'legal ops specialist'))),
    OccupationConcept('contracts_specialist', 'contracts specialist', '23', 'legal', frozenset(('contracts specialist', 'contract specialist', 'contract administrator'))),
    OccupationConcept('mediator', 'mediator', '23', 'legal', frozenset(('mediator', 'arbitrator', 'conciliator'))),
    OccupationConcept('elementary_school_teacher', 'elementary school teacher', '25', 'operations', frozenset(('elementary school teacher', 'elementary teacher'))),
    OccupationConcept('secondary_school_teacher', 'secondary school teacher', '25', 'operations', frozenset(('secondary school teacher', 'high school teacher'))),
    OccupationConcept('special_education_teacher', 'special education teacher', '25', 'operations', frozenset(('special education teacher', 'special ed teacher'))),
    OccupationConcept('preschool_teacher', 'preschool teacher', '25', 'operations', frozenset(('preschool teacher', 'early childhood teacher'))),
    OccupationConcept('college_professor', 'college professor', '25', 'operations', frozenset(('college professor', 'university professor', 'postsecondary teacher'))),
    OccupationConcept('instructional_coordinator', 'instructional coordinator', '25', 'operations', frozenset(('instructional coordinator', 'curriculum specialist'))),
    OccupationConcept('librarian', 'librarian', '25', 'operations', frozenset(('librarian', 'library media specialist'))),
    OccupationConcept('teaching_assistant', 'teaching assistant', '25', 'operations', frozenset(('teaching assistant', 'teacher aide', 'paraprofessional'))),
    OccupationConcept('academic_advisor', 'academic advisor', '25', 'operations', frozenset(('academic advisor', 'student success advisor'))),
    OccupationConcept('school_psychologist', 'school psychologist', '25', 'operations', frozenset(('school psychologist', 'educational psychologist'))),
    OccupationConcept('graphic_designer', 'graphic designer', '27', 'design', frozenset(('graphic designer', 'visual designer'))),
    OccupationConcept('user_experience_designer', 'user experience designer', '27', 'design', frozenset(('user experience designer', 'ux designer', 'product designer'))),
    OccupationConcept('journalist', 'journalist', '27', 'marketing', frozenset(('journalist', 'reporter', 'news reporter'))),
    OccupationConcept('writer', 'writer', '27', 'marketing', frozenset(('writer', 'copywriter', 'content writer'))),
    OccupationConcept('editor', 'editor', '27', 'marketing', frozenset(('editor', 'copy editor', 'content editor'))),
    OccupationConcept('public_relations_specialist', 'public relations specialist', '27', 'marketing', frozenset(('public relations specialist', 'communications specialist', 'pr specialist'))),
    OccupationConcept('coach', 'coach', '27', 'operations', frozenset(('coach', 'athletic coach', 'sports coach'))),
    OccupationConcept('sports_analyst', 'sports analyst', '27', 'data', frozenset(('sports analyst', 'sports data analyst', 'performance analyst'))),
    OccupationConcept('photographer', 'photographer', '27', 'design', frozenset(('photographer', 'photojournalist'))),
    OccupationConcept('video_editor', 'video editor', '27', 'design', frozenset(('video editor', 'film editor'))),
    OccupationConcept('producer', 'producer', '27', 'operations', frozenset(('producer', 'media producer', 'television producer'))),
    OccupationConcept('announcer', 'announcer', '27', 'marketing', frozenset(('announcer', 'broadcaster', 'sports announcer'))),
    OccupationConcept('registered_nurse', 'registered nurse', '29', 'healthcare', frozenset(('registered nurse', 'rn'))),
    OccupationConcept('physician', 'physician', '29', 'healthcare', frozenset(('physician', 'medical doctor', 'doctor'))),
    OccupationConcept('physician_assistant', 'physician assistant', '29', 'healthcare', frozenset(('physician assistant',))),
    OccupationConcept('nurse_practitioner', 'nurse practitioner', '29', 'healthcare', frozenset(('nurse practitioner', 'advanced practice nurse'))),
    OccupationConcept('pharmacist', 'pharmacist', '29', 'healthcare', frozenset(('pharmacist',))),
    OccupationConcept('dentist', 'dentist', '29', 'healthcare', frozenset(('dentist', 'general dentist'))),
    OccupationConcept('physical_therapist', 'physical therapist', '29', 'healthcare', frozenset(('physical therapist',))),
    OccupationConcept('occupational_therapist', 'occupational therapist', '29', 'healthcare', frozenset(('occupational therapist',))),
    OccupationConcept('speech_language_pathologist', 'speech language pathologist', '29', 'healthcare', frozenset(('speech language pathologist', 'speech therapist'))),
    OccupationConcept('radiologic_technologist', 'radiologic technologist', '29', 'healthcare', frozenset(('radiologic technologist', 'radiology technologist', 'x ray technologist'))),
    OccupationConcept('respiratory_therapist', 'respiratory therapist', '29', 'healthcare', frozenset(('respiratory therapist',))),
    OccupationConcept('dietitian', 'dietitian', '29', 'healthcare', frozenset(('dietitian', 'registered dietitian', 'nutritionist'))),
    OccupationConcept('veterinarian', 'veterinarian', '29', 'healthcare', frozenset(('veterinarian', 'veterinary doctor'))),
    OccupationConcept('emergency_medical_technician', 'emergency medical technician', '29', 'healthcare', frozenset(('emergency medical technician', 'emt', 'paramedic'))),
    OccupationConcept('nursing_assistant', 'nursing assistant', '31', 'healthcare', frozenset(('nursing assistant', 'certified nursing assistant', 'cna'))),
    OccupationConcept('medical_assistant', 'medical assistant', '31', 'healthcare', frozenset(('medical assistant', 'clinical medical assistant'))),
    OccupationConcept('home_health_aide', 'home health aide', '31', 'healthcare', frozenset(('home health aide', 'personal care aide'))),
    OccupationConcept('pharmacy_technician', 'pharmacy technician', '31', 'healthcare', frozenset(('pharmacy technician', 'pharmacy tech'))),
    OccupationConcept('dental_assistant', 'dental assistant', '31', 'healthcare', frozenset(('dental assistant',))),
    OccupationConcept('phlebotomist', 'phlebotomist', '31', 'healthcare', frozenset(('phlebotomist', 'phlebotomy technician'))),
    OccupationConcept('physical_therapist_assistant', 'physical therapist assistant', '31', 'healthcare', frozenset(('physical therapist assistant', 'physical therapy assistant'))),
    OccupationConcept('occupational_therapy_assistant', 'occupational therapy assistant', '31', 'healthcare', frozenset(('occupational therapy assistant',))),
    OccupationConcept('police_officer', 'police officer', '33', 'operations', frozenset(('police officer', 'law enforcement officer', 'patrol officer'))),
    OccupationConcept('detective', 'detective', '33', 'operations', frozenset(('detective', 'criminal investigator'))),
    OccupationConcept('correctional_officer', 'correctional officer', '33', 'operations', frozenset(('correctional officer', 'corrections officer'))),
    OccupationConcept('firefighter', 'firefighter', '33', 'operations', frozenset(('firefighter', 'fire fighter'))),
    OccupationConcept('security_guard', 'security guard', '33', 'operations', frozenset(('security guard', 'security officer'))),
    OccupationConcept('transportation_security_officer', 'transportation security officer', '33', 'operations', frozenset(('transportation security officer', 'tsa officer'))),
    OccupationConcept('lifeguard', 'lifeguard', '33', 'operations', frozenset(('lifeguard',))),
    OccupationConcept('probation_officer', 'probation officer', '33', 'operations', frozenset(('probation officer', 'parole officer'))),
    OccupationConcept('chef', 'chef', '35', 'operations', frozenset(('chef', 'head cook', 'executive chef'))),
    OccupationConcept('cook', 'cook', '35', 'operations', frozenset(('cook', 'line cook', 'prep cook'))),
    OccupationConcept('bartender', 'bartender', '35', 'operations', frozenset(('bartender',))),
    OccupationConcept('server', 'server', '35', 'operations', frozenset(('server', 'waiter', 'waitress'))),
    OccupationConcept('barista', 'barista', '35', 'operations', frozenset(('barista',))),
    OccupationConcept('food_preparation_worker', 'food preparation worker', '35', 'operations', frozenset(('food preparation worker', 'food prep worker'))),
    OccupationConcept('restaurant_host', 'restaurant host', '35', 'operations', frozenset(('restaurant host', 'hostess'))),
    OccupationConcept('dishwasher', 'dishwasher', '35', 'operations', frozenset(('dishwasher',))),
    OccupationConcept('janitor', 'janitor', '37', 'operations', frozenset(('janitor', 'custodian'))),
    OccupationConcept('housekeeper', 'housekeeper', '37', 'operations', frozenset(('housekeeper', 'room attendant'))),
    OccupationConcept('groundskeeper', 'groundskeeper', '37', 'operations', frozenset(('groundskeeper', 'grounds maintenance worker'))),
    OccupationConcept('landscaper', 'landscaper', '37', 'operations', frozenset(('landscaper', 'landscape technician'))),
    OccupationConcept('pest_control_worker', 'pest control worker', '37', 'operations', frozenset(('pest control worker', 'pest control technician'))),
    OccupationConcept('tree_trimmer', 'tree trimmer', '37', 'operations', frozenset(('tree trimmer', 'arborist'))),
    OccupationConcept('building_cleaner', 'building cleaner', '37', 'operations', frozenset(('building cleaner', 'commercial cleaner'))),
    OccupationConcept('pool_service_technician', 'pool service technician', '37', 'operations', frozenset(('pool service technician', 'pool technician'))),
    OccupationConcept('barber', 'barber', '39', 'operations', frozenset(('barber',))),
    OccupationConcept('cosmetologist', 'cosmetologist', '39', 'operations', frozenset(('cosmetologist', 'hair stylist', 'hairstylist'))),
    OccupationConcept('childcare_worker', 'childcare worker', '39', 'operations', frozenset(('childcare worker', 'daycare worker'))),
    OccupationConcept('fitness_trainer', 'fitness trainer', '39', 'operations', frozenset(('fitness trainer', 'personal trainer'))),
    OccupationConcept('recreation_worker', 'recreation worker', '39', 'operations', frozenset(('recreation worker', 'recreation specialist'))),
    OccupationConcept('funeral_attendant', 'funeral attendant', '39', 'operations', frozenset(('funeral attendant', 'funeral assistant'))),
    OccupationConcept('animal_caretaker', 'animal caretaker', '39', 'operations', frozenset(('animal caretaker', 'kennel attendant'))),
    OccupationConcept('concierge', 'concierge', '39', 'operations', frozenset(('concierge', 'guest services attendant'))),
    OccupationConcept('sales_representative', 'sales representative', '41', 'marketing', frozenset(('sales representative', 'sales rep'))),
    OccupationConcept('retail_salesperson', 'retail salesperson', '41', 'marketing', frozenset(('retail salesperson', 'retail associate'))),
    OccupationConcept('real_estate_agent', 'real estate agent', '41', 'finance', frozenset(('real estate agent', 'realtor'))),
    OccupationConcept('insurance_sales_agent', 'insurance sales agent', '41', 'finance', frozenset(('insurance sales agent', 'insurance agent'))),
    OccupationConcept('sales_engineer', 'sales engineer', '41', 'technology', frozenset(('sales engineer', 'solutions engineer'))),
    OccupationConcept('account_executive', 'account executive', '41', 'marketing', frozenset(('account executive',))),
    OccupationConcept('business_development_representative', 'business development representative', '41', 'marketing', frozenset(('business development representative', 'sales development representative'))),
    OccupationConcept('telemarketer', 'telemarketer', '41', 'marketing', frozenset(('telemarketer',))),
    OccupationConcept('administrative_assistant', 'administrative assistant', '43', 'operations', frozenset(('administrative assistant', 'admin assistant'))),
    OccupationConcept('executive_assistant', 'executive assistant', '43', 'operations', frozenset(('executive assistant',))),
    OccupationConcept('receptionist', 'receptionist', '43', 'operations', frozenset(('receptionist', 'front desk receptionist'))),
    OccupationConcept('data_entry_clerk', 'data entry clerk', '43', 'operations', frozenset(('data entry clerk', 'data entry specialist'))),
    OccupationConcept('bookkeeper', 'bookkeeper', '43', 'finance', frozenset(('bookkeeper', 'accounting clerk'))),
    OccupationConcept('payroll_clerk', 'payroll clerk', '43', 'finance', frozenset(('payroll clerk', 'payroll specialist'))),
    OccupationConcept('billing_clerk', 'billing clerk', '43', 'finance', frozenset(('billing clerk', 'billing specialist'))),
    OccupationConcept('customer_service_representative', 'customer service representative', '43', 'operations', frozenset(('customer service representative', 'customer support representative'))),
    OccupationConcept('office_manager', 'office manager', '43', 'operations', frozenset(('office manager',))),
    OccupationConcept('dispatcher', 'dispatcher', '43', 'operations', frozenset(('dispatcher', 'public safety dispatcher'))),
    OccupationConcept('farmer', 'farmer', '45', 'operations', frozenset(('farmer', 'farm manager'))),
    OccupationConcept('farm_worker', 'farm worker', '45', 'operations', frozenset(('farm worker', 'agricultural worker'))),
    OccupationConcept('agricultural_technician', 'agricultural technician', '45', 'data', frozenset(('agricultural technician', 'agriculture technician'))),
    OccupationConcept('forestry_technician', 'forestry technician', '45', 'operations', frozenset(('forestry technician', 'forest technician'))),
    OccupationConcept('logger', 'logger', '45', 'operations', frozenset(('logger', 'logging worker'))),
    OccupationConcept('fisher', 'fisher', '45', 'operations', frozenset(('fisher', 'commercial fisherman'))),
    OccupationConcept('animal_breeder', 'animal breeder', '45', 'operations', frozenset(('animal breeder',))),
    OccupationConcept('nursery_worker', 'nursery worker', '45', 'operations', frozenset(('nursery worker', 'greenhouse worker'))),
    OccupationConcept('carpenter', 'carpenter', '47', 'operations', frozenset(('carpenter',))),
    OccupationConcept('electrician', 'electrician', '47', 'operations', frozenset(('electrician', 'journeyman electrician'))),
    OccupationConcept('plumber', 'plumber', '47', 'operations', frozenset(('plumber',))),
    OccupationConcept('hvac_installer', 'hvac installer', '47', 'operations', frozenset(('hvac installer', 'heating and air conditioning installer', 'hvac technician'))),
    OccupationConcept('construction_laborer', 'construction laborer', '47', 'operations', frozenset(('construction laborer', 'construction worker'))),
    OccupationConcept('heavy_equipment_operator', 'heavy equipment operator', '47', 'operations', frozenset(('heavy equipment operator', 'construction equipment operator'))),
    OccupationConcept('roofer', 'roofer', '47', 'operations', frozenset(('roofer',))),
    OccupationConcept('mason', 'mason', '47', 'operations', frozenset(('mason', 'bricklayer'))),
    OccupationConcept('pipefitter', 'pipefitter', '47', 'operations', frozenset(('pipefitter', 'steamfitter'))),
    OccupationConcept('solar_installer', 'solar installer', '47', 'operations', frozenset(('solar installer', 'solar photovoltaic installer'))),
    OccupationConcept('automotive_technician', 'automotive technician', '49', 'operations', frozenset(('automotive technician', 'auto mechanic', 'automotive mechanic'))),
    OccupationConcept('diesel_mechanic', 'diesel mechanic', '49', 'operations', frozenset(('diesel mechanic', 'diesel technician'))),
    OccupationConcept('aircraft_mechanic', 'aircraft mechanic', '49', 'operations', frozenset(('aircraft mechanic', 'aviation maintenance technician'))),
    OccupationConcept('industrial_maintenance_technician', 'industrial maintenance technician', '49', 'operations', frozenset(('industrial maintenance technician', 'maintenance mechanic'))),
    OccupationConcept('appliance_repair_technician', 'appliance repair technician', '49', 'operations', frozenset(('appliance repair technician', 'appliance repairer'))),
    OccupationConcept('electrical_line_installer', 'electrical line installer', '49', 'operations', frozenset(('electrical line installer', 'lineworker', 'lineman'))),
    OccupationConcept('telecommunications_technician', 'telecommunications technician', '49', 'operations', frozenset(('telecommunications technician', 'telecom technician'))),
    OccupationConcept('elevator_installer', 'elevator installer', '49', 'operations', frozenset(('elevator installer', 'elevator mechanic'))),
    OccupationConcept('machinist', 'machinist', '51', 'operations', frozenset(('machinist',))),
    OccupationConcept('cnc_operator', 'cnc operator', '51', 'operations', frozenset(('cnc operator', 'computer numerical control operator'))),
    OccupationConcept('assembler', 'assembler', '51', 'operations', frozenset(('assembler', 'assembly worker'))),
    OccupationConcept('production_worker', 'production worker', '51', 'operations', frozenset(('production worker', 'manufacturing associate'))),
    OccupationConcept('quality_inspector', 'quality inspector', '51', 'operations', frozenset(('quality inspector', 'quality control inspector'))),
    OccupationConcept('welder', 'welder', '51', 'operations', frozenset(('welder', 'fabricator'))),
    OccupationConcept('baker', 'baker', '51', 'operations', frozenset(('baker', 'production baker'))),
    OccupationConcept('plant_operator', 'plant operator', '51', 'operations', frozenset(('plant operator', 'process operator'))),
    OccupationConcept('printing_press_operator', 'printing press operator', '51', 'operations', frozenset(('printing press operator', 'press operator'))),
    OccupationConcept('packaging_operator', 'packaging operator', '51', 'operations', frozenset(('packaging operator', 'packaging technician'))),
    OccupationConcept('truck_driver', 'truck driver', '53', 'operations', frozenset(('truck driver', 'tractor trailer driver', 'commercial driver'))),
    OccupationConcept('delivery_driver', 'delivery driver', '53', 'operations', frozenset(('delivery driver', 'courier'))),
    OccupationConcept('bus_driver', 'bus driver', '53', 'operations', frozenset(('bus driver', 'transit driver'))),
    OccupationConcept('forklift_operator', 'forklift operator', '53', 'operations', frozenset(('forklift operator', 'forklift driver'))),
    OccupationConcept('warehouse_worker', 'warehouse worker', '53', 'operations', frozenset(('warehouse worker', 'warehouse associate', 'material handler'))),
    OccupationConcept('logistics_coordinator', 'logistics coordinator', '53', 'operations', frozenset(('logistics coordinator', 'shipping coordinator'))),
    OccupationConcept('flight_attendant', 'flight attendant', '53', 'operations', frozenset(('flight attendant',))),
    OccupationConcept('pilot', 'pilot', '53', 'operations', frozenset(('pilot', 'airline pilot'))),
    OccupationConcept('railroad_conductor', 'railroad conductor', '53', 'operations', frozenset(('railroad conductor', 'train conductor'))),
    OccupationConcept('transportation_dispatcher', 'transportation dispatcher', '53', 'operations', frozenset(('transportation dispatcher', 'truck dispatcher'))),
    OccupationConcept('military_service_member', 'military service member', '55', 'operations', frozenset(('military service member', 'service member'))),
    OccupationConcept('army_officer', 'army officer', '55', 'operations', frozenset(('army officer', 'military officer'))),
    OccupationConcept('military_intelligence_specialist', 'military intelligence specialist', '55', 'data', frozenset(('military intelligence specialist', 'intelligence analyst'))),
    OccupationConcept('infantry_member', 'infantry member', '55', 'operations', frozenset(('infantry member', 'infantry soldier'))),
    OccupationConcept('military_police', 'military police', '55', 'operations', frozenset(('military police', 'military police officer'))),
    OccupationConcept('aviation_officer', 'aviation officer', '55', 'operations', frozenset(('aviation officer', 'military pilot'))),
    OccupationConcept('logistics_officer', 'logistics officer', '55', 'operations', frozenset(('logistics officer', 'military logistics officer'))),
    OccupationConcept('cyber_operations_specialist', 'cyber operations specialist', '55', 'technology', frozenset(('cyber operations specialist', 'military cyber specialist'))),
)

AMBIGUOUS_ACRONYMS: dict[str, tuple[str, ...]] = {'ae': ('account executive', 'aerospace engineer', 'applications engineer'),
 'am': ('account manager', 'area manager', 'asset manager'),
 'ba': ('business analyst', 'brand ambassador', 'banking associate'),
 'bd': ('business development', 'building designer', 'behavioral health director'),
 'bm': ('business manager', 'branch manager', 'building maintenance'),
 'ca': ('certified accountant', 'claims adjuster', 'California'),
 'ce': ('civil engineer', 'chief engineer', 'customer engineer'),
 'cm': ('construction manager', 'content manager', 'case manager'),
 'cs': ('computer science', 'customer service', 'clinical specialist'),
 'da': ('data analyst', 'district attorney', 'dental assistant'),
 'de': ('data engineer', 'design engineer', 'Delaware'),
 'ea': ('executive assistant', 'enterprise architect', 'enrolled agent'),
 'ee': ('electrical engineer', 'electronics engineer', 'employee experience'),
 'fa': ('financial analyst', 'flight attendant', 'faculty assistant'),
 'fe': ('field engineer', 'facilities engineer', 'front-end engineer'),
 'hr': ('human resources', 'heart-rate technician', 'hotel representative'),
 'ia': ('information architect', 'internal auditor', 'intelligence analyst'),
 'ie': ('industrial engineer', 'integration engineer', 'Ireland'),
 'ma': ('medical assistant', 'management analyst', 'Massachusetts'),
 'me': ('mechanical engineer', 'manufacturing engineer', 'Maine'),
 'na': ('nursing assistant', 'network administrator', 'not applicable'),
 'ot': ('occupational therapist', 'operational technology specialist', 'overtime work'),
 'pa': ('physician assistant', 'personal assistant', 'production assistant'),
 'pe': ('professional engineer', 'petroleum engineer', 'physical education teacher'),
 'pm': ('project manager', 'product manager', 'preventive maintenance technician'),
 'pt': ('physical therapist', 'personal trainer', 'part-time work'),
 'ra': ('research assistant', 'resident assistant', 'risk analyst'),
 're': ('reliability engineer', 'real estate agent', 'research engineer'),
 'sa': ('systems analyst', 'sales associate', 'security analyst'),
 'sae': ('systems application engineer', 'sales application engineer', 'service application engineer'),
 'se': ('software engineer', 'systems engineer', 'sales engineer'),
 'ta': ('teaching assistant', 'talent acquisition specialist', 'technical analyst'),
 'te': ('test engineer', 'telecommunications engineer', 'technical editor')}

_QUERY_FILLER = frozenset(
    {
        "a", "an", "and", "career", "careers", "entry", "entry-level", "for",
        "grad", "graduate", "intern", "internship", "job", "jobs", "junior",
        "level", "mid", "new", "opening", "openings", "position", "positions",
        "role", "roles", "senior", "sr", "staff",
    }
)
_GENERIC_HEAD_WORDS = frozenset(
    {
        "accountant", "administrator", "advisor", "aide", "analyst", "architect",
        "assistant", "attendant", "attorney", "auditor", "barber", "bartender",
        "broker", "carpenter", "chemist", "clerk", "coach", "consultant", "cook",
        "coordinator", "counselor", "designer", "detective", "developer",
        "director", "dispatcher", "doctor", "driver", "economist", "editor",
        "electrician", "engineer", "farmer", "firefighter", "guard", "instructor",
        "investigator", "journalist", "lawyer", "librarian", "machinist", "manager",
        "mechanic", "nurse", "officer", "operator", "paralegal", "pharmacist",
        "photographer", "physician", "pilot", "planner", "plumber", "producer",
        "professor", "recruiter", "reporter", "representative", "researcher",
        "scientist", "specialist", "supervisor", "teacher", "technician",
        "therapist", "trainer", "worker", "writer",
    }
)
_FAMILY_KEYWORDS: tuple[tuple[str, frozenset[str]], ...] = (
    ("legal", frozenset({"attorney", "lawyer", "legal", "paralegal", "court", "contract"})),
    ("healthcare", frozenset({"health", "medical", "nurse", "physician", "therapy", "therapist", "pharmacy", "dental"})),
    ("cybersecurity", frozenset({"cyber", "security", "infosec", "soc"})),
    ("software", frozenset({"software", "developer", "application", "web", "programmer", "test"})),
    ("data", frozenset({"data", "analytics", "scientist", "economist", "statistician", "research"})),
    ("marketing", frozenset({"marketing", "sales", "communications", "public relations", "writer", "editor", "media"})),
    ("design", frozenset({"design", "designer", "architect", "photographer"})),
    ("technology", frozenset({"engineer", "engineering", "network", "systems", "system"})),
)


def normalize_occupation_text(value: str) -> str:
    normalized = value.lower().replace("&", " and ")
    normalized = re.sub(r"[^a-z0-9+#]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def _base_query_tokens(query: str) -> tuple[str, ...]:
    return tuple(
        token
        for token in normalize_occupation_text(query).split()
        if token not in _QUERY_FILLER
    )


def _pure_acronym(query: str) -> str | None:
    tokens = _base_query_tokens(query)
    if len(tokens) != 1:
        return None
    token = tokens[0]
    return token if token in AMBIGUOUS_ACRONYMS else None


def _replace_alias(query: str, alias: str, canonical: str) -> str:
    normalized_query = normalize_occupation_text(query)
    normalized_alias = normalize_occupation_text(alias)
    pattern = re.compile(r"(?<![a-z0-9])" + re.escape(normalized_alias) + r"(?![a-z0-9])")
    return re.sub(r"\s+", " ", pattern.sub(canonical, normalized_query, count=1)).strip()


def _alias_candidates() -> tuple[tuple[str, OccupationConcept], ...]:
    pairs: list[tuple[str, OccupationConcept]] = []
    for concept in OCCUPATIONS:
        for alias in concept.aliases:
            pairs.append((normalize_occupation_text(alias), concept))
    return tuple(sorted(pairs, key=lambda item: (-len(item[0].split()), -len(item[0]), item[0])))


_ALIAS_CANDIDATES = _alias_candidates()


def _exact_match(query: str) -> tuple[str, OccupationConcept] | None:
    normalized = normalize_occupation_text(query)
    for alias, concept in _ALIAS_CANDIDATES:
        if re.search(r"(?<![a-z0-9])" + re.escape(alias) + r"(?![a-z0-9])", normalized):
            return alias, concept
    return None


def _fuzzy_match(query: str) -> tuple[str, OccupationConcept] | None:
    candidate = " ".join(_base_query_tokens(query))
    if len(candidate) < 5:
        return None
    scored: list[tuple[float, str, OccupationConcept]] = []
    candidate_tokens = candidate.split()
    for alias, concept in _ALIAS_CANDIDATES:
        if abs(len(alias.split()) - len(candidate_tokens)) > 1:
            continue
        if alias[0] != candidate[0]:
            continue
        score = difflib.SequenceMatcher(None, candidate, alias).ratio()
        if score >= 0.88:
            scored.append((score, alias, concept))
    if not scored:
        return None
    scored.sort(key=lambda item: (-item[0], item[1], item[2].key))
    best = scored[0]
    runner_up = scored[1][0] if len(scored) > 1 else 0.0
    if best[0] < 0.90 or best[0] - runner_up < 0.035:
        return None
    return best[1], best[2]


def _generic_family(tokens: set[str]) -> str:
    joined = " ".join(sorted(tokens))
    for family, keywords in _FAMILY_KEYWORDS:
        if any(keyword in tokens or keyword in joined for keyword in keywords):
            return family
    return "operations"


def _generic_interpretation(query: str) -> OccupationInterpretation | None:
    tokens = set(_base_query_tokens(query))
    if not tokens or not (tokens & _GENERIC_HEAD_WORDS):
        return None
    canonical = " ".join(_base_query_tokens(query))
    return OccupationInterpretation(
        status="recognized",
        original_query=query.strip(),
        canonical_query=normalize_occupation_text(query),
        occupation_phrase=canonical,
        search_family=_generic_family(tokens),
        accepted_titles=(canonical,),
        reason="Recognized a descriptive occupation title by its occupational head word.",
    )


def interpret_occupation_query(query: str) -> OccupationInterpretation:
    original = query.strip()
    acronym = _pure_acronym(original)
    if acronym:
        return OccupationInterpretation(
            status="ambiguous",
            original_query=original,
            canonical_query=normalize_occupation_text(original),
            suggestions=AMBIGUOUS_ACRONYMS[acronym],
            reason=f"{acronym.upper()} has multiple common occupational meanings.",
        )

    match = _exact_match(original)
    match_reason = "Matched a canonical or accepted occupation title."
    if match is None:
        match = _fuzzy_match(original)
        match_reason = "Matched a high-confidence spelling variant."
    if match is not None:
        alias, concept = match
        accepted = tuple(
            sorted(
                {normalize_occupation_text(value) for value in concept.aliases},
                key=lambda value: (-len(value.split()), -len(value), value),
            )
        )
        return OccupationInterpretation(
            status="recognized",
            original_query=original,
            canonical_query=_replace_alias(original, alias, concept.canonical_title),
            occupation_phrase=concept.canonical_title,
            concept_key=concept.key,
            soc_major_group=concept.soc_major_group,
            major_group_name=concept.major_group_name,
            search_family=concept.search_family,
            accepted_titles=accepted,
            reason=match_reason,
        )

    generic = _generic_interpretation(original)
    if generic is not None:
        return generic

    return OccupationInterpretation(
        status="unrecognized",
        original_query=original,
        canonical_query=normalize_occupation_text(original),
        reason="No deterministic occupation title or safe generic occupational pattern matched.",
    )


def title_matches_occupation(title: str, interpretation: OccupationInterpretation) -> bool:
    if not interpretation.recognized or not interpretation.occupation_phrase:
        return False
    normalized_title = normalize_occupation_text(title)
    for alias in interpretation.accepted_titles:
        if re.search(r"(?<![a-z0-9])" + re.escape(alias) + r"(?![a-z0-9])", normalized_title):
            return True

    requested_tokens = {
        token
        for token in normalize_occupation_text(interpretation.occupation_phrase).split()
        if token not in _QUERY_FILLER
    }
    title_tokens = set(normalized_title.split())
    if not requested_tokens or not (requested_tokens & _GENERIC_HEAD_WORDS):
        return False
    head_tokens = requested_tokens & _GENERIC_HEAD_WORDS
    if not head_tokens.issubset(title_tokens):
        return False
    qualifier_tokens = requested_tokens - head_tokens
    if not qualifier_tokens:
        return True
    required = max(1, len(qualifier_tokens) - 1)
    return len(qualifier_tokens & title_tokens) >= required


def registry_summary() -> dict[str, int]:
    represented = {concept.soc_major_group for concept in OCCUPATIONS}
    return {
        "major_groups": len(represented),
        "occupations": len(OCCUPATIONS),
        "accepted_titles": sum(len(concept.aliases) for concept in OCCUPATIONS),
        "ambiguous_acronyms": len(AMBIGUOUS_ACRONYMS),
    }
