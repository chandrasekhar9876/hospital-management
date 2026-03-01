import json
import os
import re
from datetime import datetime, timedelta
from urllib import error, request as urllib_request

from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text
from werkzeug.security import check_password_hash, generate_password_hash

# -------------------------------------------------
# APP CONFIGURATION
# -------------------------------------------------

app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

ALLOWED_ROLES = {'admin', 'doctor', 'patient'}
ALLOWED_STATUSES = {'Pending', 'Approved', 'Completed', 'Cancelled'}
CITY_HOSPITALS = {
    'gajuwaka': {
        'label': 'Gajuwaka',
        'center': {'lat': 17.6865, 'lng': 83.2118},
        'hospitals': [
            {
                'name': 'KIMS ICON Hospital',
                'address': 'Sheela Nagar Main Road, Gajuwaka, Visakhapatnam',
                'lat': 17.6869,
                'lng': 83.2098,
                'speciality': 'Multi-speciality',
            },
            {
                'name': 'NRI General Hospital',
                'address': 'Near Gajuwaka Junction, Visakhapatnam',
                'lat': 17.6854,
                'lng': 83.2017,
                'speciality': 'General Medicine',
            },
            {
                'name': 'RK Hospital Gajuwaka',
                'address': 'Old Gajuwaka Junction, Visakhapatnam',
                'lat': 17.6861,
                'lng': 83.2182,
                'speciality': 'General & Emergency',
            },
            {
                'name': 'Lalitha Super Speciality Hospital',
                'address': 'Near Gajuwaka Main Road, Visakhapatnam',
                'lat': 17.6812,
                'lng': 83.2145,
                'speciality': 'Super Speciality',
            },
            {
                'name': 'Sunrise Hospital',
                'address': 'Gajuwaka Area, Visakhapatnam',
                'lat': 17.6920,
                'lng': 83.2134,
                'speciality': 'General & Diagnostics',
            },
        ],
    },
    'visakhapatnam': {
        'label': 'Visakhapatnam',
        'center': {'lat': 17.7231, 'lng': 83.3013},
        'hospitals': [
            {'name': 'King George Hospital', 'address': 'Maharani Peta, Visakhapatnam', 'lat': 17.7102, 'lng': 83.3154, 'speciality': 'Government Multi-speciality'},
            {'name': 'Apollo Hospitals', 'address': 'Health City, Arilova, Visakhapatnam', 'lat': 17.7606, 'lng': 83.3447, 'speciality': 'Multi-speciality'},
            {'name': 'CARE Hospitals', 'address': 'Ram Nagar, Visakhapatnam', 'lat': 17.7258, 'lng': 83.3041, 'speciality': 'Cardiac & Critical Care'},
            {'name': 'SevenHills Hospital', 'address': 'Rockdale Layout, Waltair Main Road', 'lat': 17.7180, 'lng': 83.3117, 'speciality': 'Super Speciality'},
        ],
    },
    'vijayawada': {
        'label': 'Vijayawada',
        'center': {'lat': 16.5062, 'lng': 80.6480},
        'hospitals': [
            {'name': 'Andhra Hospitals', 'address': 'Governorpet, Vijayawada', 'lat': 16.5143, 'lng': 80.6335, 'speciality': 'Multi-speciality'},
            {'name': 'Sentini Hospitals', 'address': 'Poranki, Vijayawada', 'lat': 16.4734, 'lng': 80.7175, 'speciality': 'General & Surgical'},
            {'name': 'Ramesh Hospitals', 'address': 'Gunadala, Vijayawada', 'lat': 16.5340, 'lng': 80.6597, 'speciality': 'Cardiac & Neuro'},
            {'name': 'Manipal Hospital Vijayawada', 'address': 'Tadepalli, Vijayawada', 'lat': 16.4800, 'lng': 80.6112, 'speciality': 'Multi-speciality'},
        ],
    },
    'hyderabad': {
        'label': 'Hyderabad',
        'center': {'lat': 17.3850, 'lng': 78.4867},
        'hospitals': [
            {'name': 'Yashoda Hospitals', 'address': 'Somajiguda, Hyderabad', 'lat': 17.4226, 'lng': 78.4582, 'speciality': 'Multi-speciality'},
            {'name': 'KIMS Hospitals', 'address': 'Secunderabad, Hyderabad', 'lat': 17.4386, 'lng': 78.4983, 'speciality': 'Critical Care'},
            {'name': 'Apollo Hospitals', 'address': 'Jubilee Hills, Hyderabad', 'lat': 17.4216, 'lng': 78.4109, 'speciality': 'Super Speciality'},
            {'name': 'AIG Hospitals', 'address': 'Gachibowli, Hyderabad', 'lat': 17.4401, 'lng': 78.3489, 'speciality': 'Gastro & Liver Care'},
        ],
    },
    'chennai': {
        'label': 'Chennai',
        'center': {'lat': 13.0827, 'lng': 80.2707},
        'hospitals': [
            {'name': 'Apollo Hospital', 'address': 'Greams Road, Chennai', 'lat': 13.0637, 'lng': 80.2518, 'speciality': 'Multi-speciality'},
            {'name': 'MIOT International', 'address': 'Manapakkam, Chennai', 'lat': 13.0188, 'lng': 80.1852, 'speciality': 'Orthopedic & Trauma'},
            {'name': 'Global Hospitals', 'address': 'Perumbakkam, Chennai', 'lat': 12.8994, 'lng': 80.2072, 'speciality': 'Liver & Multi-organ'},
            {'name': 'Fortis Malar', 'address': 'Adyar, Chennai', 'lat': 13.0089, 'lng': 80.2571, 'speciality': 'Cardiac Care'},
        ],
    },
}

PLATFORM_FEATURES = {
    'For Patients': [
        'Online Appointment Booking: Patients can check doctor availability and book slots without calling.',
        'Patient Portal: Access to personal medical records, lab results, and prescriptions.',
        'Telemedicine: Integrated video consultations for remote care.',
        'Online Payments: Securely paying for consultations or hospital bills via credit card or insurance.',
    ],
    'For Doctors & Staff': [
        'Electronic Health Records (EHR): A digital version of a patient chart with history, diagnoses, and medications.',
        'Pharmacy Management: Tracking medicine stock, expiry dates, and automated re-ordering.',
        'Laboratory Management: Recording test results and automatically sharing them with doctor and patient.',
    ],
    'For Administration': [
        'Billing & Accounting: Managing insurance claims, invoices, and payroll.',
        'Inventory Tracking: Monitoring hospital supplies from surgical masks to oxygen tanks.',
        'Staff Scheduling: Managing nursing shifts and doctor rotations.',
    ],
}


# -------------------------------------------------
# DATABASE MODELS
# -------------------------------------------------


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), nullable=False)


class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_name = db.Column(db.String(100), nullable=False)
    doctor_name = db.Column(db.String(100), nullable=False)
    hospital_name = db.Column(db.String(150), default='')
    hospital_location = db.Column(db.String(200), default='')
    date = db.Column(db.String(50), nullable=False)
    time = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50), default='Pending')
    issue = db.Column(db.Text, default='')
    prescription = db.Column(db.Text, default='')


class MedicalRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_name = db.Column(db.String(100), nullable=False)
    doctor_name = db.Column(db.String(100), nullable=False)
    diagnosis = db.Column(db.Text, nullable=False)
    medications = db.Column(db.Text, default='')
    notes = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class LabResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_name = db.Column(db.String(100), nullable=False)
    doctor_name = db.Column(db.String(100), nullable=False)
    test_name = db.Column(db.String(120), nullable=False)
    result_value = db.Column(db.String(200), nullable=False)
    normal_range = db.Column(db.String(120), default='')
    status = db.Column(db.String(50), default='Final')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_name = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_for = db.Column(db.String(200), nullable=False)
    method = db.Column(db.String(60), nullable=False)
    status = db.Column(db.String(60), default='Paid')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class TelemedicineSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), nullable=False)
    patient_name = db.Column(db.String(100), nullable=False)
    doctor_name = db.Column(db.String(100), nullable=False)
    room_link = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(50), default='Scheduled')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class PharmacyItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(120), unique=True, nullable=False)
    stock_qty = db.Column(db.Integer, nullable=False, default=0)
    expiry_date = db.Column(db.String(20), nullable=False)
    reorder_level = db.Column(db.Integer, nullable=False, default=10)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class BillingEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    entry_type = db.Column(db.String(60), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(60), default='Open')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class HospitalSupply(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    supply_name = db.Column(db.String(120), unique=True, nullable=False)
    category = db.Column(db.String(80), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    min_level = db.Column(db.Integer, nullable=False, default=5)
    unit = db.Column(db.String(30), default='units')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class StaffSchedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    staff_name = db.Column(db.String(100), nullable=False)
    staff_role = db.Column(db.String(80), nullable=False)
    shift_date = db.Column(db.String(20), nullable=False)
    shift_slot = db.Column(db.String(30), nullable=False)
    notes = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


# -------------------------------------------------
# HELPERS
# -------------------------------------------------


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def role_dashboard_endpoint(role):
    mapping = {
        'admin': 'admin_dashboard',
        'doctor': 'doctor_dashboard',
        'patient': 'patient_dashboard',
    }
    return mapping.get(role, 'index')


def parse_appointment_datetime(date_str, time_str):
    try:
        return datetime.strptime(f'{date_str} {time_str}', '%Y-%m-%d %H:%M')
    except (TypeError, ValueError):
        return None


def parse_date(value):
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except (TypeError, ValueError):
        return None


LANGUAGE_PACKS = {
    'en': {
        'empty': 'Please type your medical question. You can also ask about booking an appointment.',
        'emergency': 'This may be an emergency. Please call emergency services immediately or go to the nearest ER. Do not wait for online advice.',
        'ask_symptoms': 'I can assist like a medical triage agent. Tell me your symptoms, duration, and severity (example: "fever and cough for 2 days, moderate").',
        'book_hint': 'Use the Quick Appointment form below to choose doctor, date, and time.',
        'follow_up': 'Please share age and any existing conditions (diabetes, BP, asthma, thyroid, pregnancy) for more precise guidance.',
        'care': 'General care: hydrate, rest, and monitor symptoms.',
        'persist': 'If symptoms worsen or persist, please book an appointment today.',
        'medicine_title': 'Suggested OTC options (adult, generic guidance):',
        'safety': 'Safety warning: avoid self-medication if pregnant, breastfeeding, under 18, or if you have liver/kidney/heart disease or drug allergies. Confirm with a doctor/pharmacist before taking any medicine.',
        'specialist': 'Recommended specialist',
        'recommended_doctor': 'Recommended doctor',
        'recommended_hospital': 'Recommended hospital',
        'doctor_profession': 'Doctor profession',
        'duration': 'Duration',
        'severity': 'Severity',
        'symptoms': 'Noted symptoms',
    },
    'hi': {
        'empty': 'कृपया अपना मेडिकल सवाल लिखें। आप अपॉइंटमेंट बुक करने के बारे में भी पूछ सकते हैं।',
        'emergency': 'यह आपातकाल हो सकता है। तुरंत इमरजेंसी सेवा को कॉल करें या नज़दीकी अस्पताल जाएं। ऑनलाइन सलाह का इंतज़ार न करें।',
        'ask_symptoms': 'मैं मेडिकल ट्रायाज सहायक की तरह मदद कर सकता हूं। अपने लक्षण, कितने दिनों से हैं, और गंभीरता बताएं।',
        'book_hint': 'नीचे Quick Appointment फॉर्म में डॉक्टर, तारीख और समय चुनकर बुक करें।',
        'follow_up': 'कृपया उम्र और पहले से मौजूद बीमारियां (शुगर, BP, अस्थमा, थायरॉइड, प्रेग्नेंसी) बताएं ताकि सलाह अधिक सटीक हो।',
        'care': 'सामान्य देखभाल: पानी पिएं, आराम करें और लक्षणों पर निगरानी रखें।',
        'persist': 'यदि लक्षण बढ़ें या बने रहें तो आज ही अपॉइंटमेंट बुक करें।',
        'medicine_title': 'OTC दवा सुझाव (वयस्कों के लिए, सामान्य मार्गदर्शन):',
        'safety': 'सुरक्षा चेतावनी: गर्भावस्था, स्तनपान, 18 वर्ष से कम उम्र, या लीवर/किडनी/हृदय रोग या दवा एलर्जी में स्वयं दवा न लें। दवा लेने से पहले डॉक्टर/फार्मासिस्ट से पुष्टि करें।',
        'specialist': 'सुझावित विशेषज्ञ',
        'duration': 'अवधि',
        'severity': 'गंभीरता',
        'symptoms': 'पहचाने गए लक्षण',
    },
    'te': {
        'empty': 'దయచేసి మీ వైద్య ప్రశ్నను టైప్ చేయండి. అపాయింట్మెంట్ బుకింగ్ గురించి కూడా అడగవచ్చు.',
        'emergency': 'ఇది అత్యవసర పరిస్థితి కావచ్చు. వెంటనే ఎమర్జెన్సీ సేవలకు కాల్ చేయండి లేదా సమీప ఆసుపత్రికి వెళ్ళండి. ఆన్‌లైన్ సలహా కోసం వేచి ఉండవద్దు.',
        'ask_symptoms': 'నేను మెడికల్ ట్రియాజ్ సహాయకుడిగా సహాయం చేస్తాను. మీ లక్షణాలు, ఎంతకాలంగా ఉన్నాయి, తీవ్రత చెప్పండి.',
        'book_hint': 'కింద ఉన్న Quick Appointment ఫారమ్‌లో డాక్టర్, తేదీ, సమయం ఎంచుకుని బుక్ చేయండి.',
        'follow_up': 'మరింత కచ్చితమైన మార్గదర్శకత్వం కోసం మీ వయస్సు మరియు ఉన్న ఆరోగ్య సమస్యలు (షుగర్, BP, ఆస్థమా, థైరాయిడ్, గర్భధారణ) చెప్పండి.',
        'care': 'సాధారణ జాగ్రత్తలు: నీరు బాగా తాగండి, విశ్రాంతి తీసుకోండి, లక్షణాలను గమనించండి.',
        'persist': 'లక్షణాలు ఎక్కువైతే లేదా కొనసాగితే ఈరోజే అపాయింట్మెంట్ బుక్ చేయండి.',
        'medicine_title': 'OTC మందుల సూచనలు (పెద్దలకు సాధారణ మార్గదర్శకం):',
        'safety': 'భద్రత హెచ్చరిక: గర్భిణీ/స్తన్యపాన మాతలు, 18 సంవత్సరాల లోపు వారు, లేదా కాలేయం/కిడ్నీ/హృదయ సమస్యలు లేదా మందుల అలర్జీ ఉన్నవారు స్వయంగా మందులు వాడొద్దు. ముందుగా డాక్టర్/ఫార్మసిస్ట్‌ను సంప్రదించండి.',
        'specialist': 'సిఫారసు నిపుణుడు',
        'duration': 'వ్యవధి',
        'severity': 'తీవ్రత',
        'symptoms': 'గమనించిన లక్షణాలు',
    },
}

SYMPTOM_SPECIALIST_MAP = {
    'fever': 'General Physician',
    'cough': 'General Physician',
    'cold': 'General Physician',
    'sore throat': 'ENT Specialist',
    'headache': 'Neurologist',
    'migraine': 'Neurologist',
    'stomach pain': 'Gastroenterologist',
    'vomiting': 'Gastroenterologist',
    'nausea': 'Gastroenterologist',
    'chest pain': 'Cardiologist',
    'breathing': 'Pulmonologist',
    'skin rash': 'Dermatologist',
    'joint pain': 'Orthopedic Specialist',
    'back pain': 'Orthopedic Specialist',
    'anxiety': 'Psychiatrist',
    'depression': 'Psychiatrist',
}

SPECIALIST_DOCTOR_HOSPITAL_MAP = {
    'General Physician': {
        'doctor': 'Ravi Kumar',
        'hospital': 'MediCore General Hospital',
        'location': 'Gajuwaka, Visakhapatnam',
    },
    'ENT Specialist': {
        'doctor': 'Neha Sharma',
        'hospital': 'MediCore ENT & Allergy Center',
        'location': 'Maharani Peta, Visakhapatnam',
    },
    'Neurologist': {
        'doctor': 'Arjun Reddy',
        'hospital': 'MediCore Neuro Sciences',
        'location': 'Health City, Arilova, Visakhapatnam',
    },
    'Gastroenterologist': {
        'doctor': 'Ravi Kumar',
        'hospital': 'MediCore Digestive Care',
        'location': 'Ram Nagar, Visakhapatnam',
    },
    'Cardiologist': {
        'doctor': 'Neha Sharma',
        'hospital': 'MediCore Heart Institute',
        'location': 'Somajiguda, Hyderabad',
    },
    'Pulmonologist': {
        'doctor': 'Arjun Reddy',
        'hospital': 'MediCore Chest & Lung Center',
        'location': 'Secunderabad, Hyderabad',
    },
    'Dermatologist': {
        'doctor': 'Neha Sharma',
        'hospital': 'MediCore Skin Clinic',
        'location': 'Jubilee Hills, Hyderabad',
    },
    'Orthopedic Specialist': {
        'doctor': 'Arjun Reddy',
        'hospital': 'MediCore Ortho & Trauma',
        'location': 'Tadepalli, Vijayawada',
    },
    'Psychiatrist': {
        'doctor': 'Ravi Kumar',
        'hospital': 'MediCore Mental Wellness',
        'location': 'Manapakkam, Chennai',
    },
}

SYMPTOM_ALIASES = {
    'fever': ['fever', 'bukhar', 'बुखार', 'ज्वर', 'జ్వరం'],
    'cough': ['cough', 'khansi', 'खांसी', 'దగ్గు'],
    'cold': ['cold', 'sardi', 'सर्दी', 'జలుబు'],
    'sore throat': ['sore throat', 'throat pain', 'gale me dard', 'गले में दर्द', 'గొంతు నొప్పి'],
    'headache': ['headache', 'sir dard', 'सिरदर्द', 'తలనొప్పి'],
    'migraine': ['migraine', 'మైగ్రేన్'],
    'stomach pain': ['stomach pain', 'gastric pain', 'pet dard', 'पेट दर्द', 'కడుపు నొప్పి'],
    'vomiting': ['vomit', 'vomiting', 'ulti', 'उल्टी', 'వాంతులు'],
    'nausea': ['nausea', 'जी मिचलाना', 'వికారంగా'],
    'chest pain': ['chest pain', 'सीने में दर्द', 'ఛాతి నొప్పి'],
    'breathing': ['breathing', 'shortness of breath', 'सांस', 'శ్వాస'],
    'skin rash': ['rash', 'skin rash', 'चकत्ते', 'చర్మ దద్దుర్లు'],
    'joint pain': ['joint pain', 'घुटने का दर्द', 'కీళ్ల నొప్పి'],
    'back pain': ['back pain', 'पीठ दर्द', 'వెన్ను నొప్పి'],
    'anxiety': ['anxiety', 'घबराहट', 'ఆందోళన'],
    'depression': ['depression', 'उदासी', 'నిరుత్సాహం'],
}

MEDICINE_TEMPLATES = {
    'fever': ['Paracetamol 500 mg after food, every 6-8 hours if needed (max 3000 mg/day).'],
    'headache': ['Paracetamol 500 mg after food, every 6-8 hours if needed (max 3000 mg/day).'],
    'cough': ['Cetirizine 10 mg at night for allergy/cold symptoms.', 'Warm saline gargles and steam inhalation 2-3 times/day.'],
    'cold': ['Cetirizine 10 mg at night for allergy/cold symptoms.', 'Warm saline gargles and steam inhalation 2-3 times/day.'],
    'sore throat': ['Lozenges and warm saline gargles can help symptom relief.'],
    'stomach pain': ['ORS/small frequent fluids for hydration.', 'Simple antacid syrup/tablet may help acidity symptoms.'],
    'nausea': ['ORS/small frequent fluids for hydration.', 'Avoid oily and spicy food for 24-48 hours.'],
    'vomiting': ['ORS/small frequent fluids for hydration.', 'Avoid oily and spicy food for 24-48 hours.'],
}


def normalize_language(language_code):
    if language_code in {'hi', 'te', 'en'}:
        return language_code
    return 'en'


def t(language_code, key):
    language_code = normalize_language(language_code)
    return LANGUAGE_PACKS[language_code].get(key, LANGUAGE_PACKS['en'][key])


def extract_symptoms(text):
    symptoms = set()
    for canonical, aliases in SYMPTOM_ALIASES.items():
        if any(alias in text for alias in aliases):
            symptoms.add(canonical)
    return sorted(symptoms)


def choose_specialist(symptoms):
    if not symptoms:
        return 'General Physician'
    specialist_count = {}
    for symptom in symptoms:
        specialist = SYMPTOM_SPECIALIST_MAP.get(symptom, 'General Physician')
        specialist_count[specialist] = specialist_count.get(specialist, 0) + 1
    return max(specialist_count, key=specialist_count.get)


def get_doctor_hospital_recommendation(specialist):
    recommendation = SPECIALIST_DOCTOR_HOSPITAL_MAP.get(
        specialist,
        SPECIALIST_DOCTOR_HOSPITAL_MAP['General Physician'],
    )

    preferred_name = recommendation['doctor']
    doctor = User.query.filter_by(role='doctor', name=preferred_name).first()
    if not doctor:
        doctor = User.query.filter_by(role='doctor').order_by(User.name.asc()).first()

    doctor_name = doctor.name if doctor else preferred_name
    return {
        'doctor_name': doctor_name,
        'hospital_name': recommendation['hospital'],
        'hospital_location': recommendation['location'],
        'profession': specialist,
    }


def medicine_suggestion_block(symptoms, language_code):
    lines = []
    for symptom in symptoms:
        lines.extend(MEDICINE_TEMPLATES.get(symptom, []))

    unique_lines = []
    for line in lines:
        if line not in unique_lines:
            unique_lines.append(line)

    if not unique_lines:
        return ''

    title = t(language_code, 'medicine_title')
    warning = t(language_code, 'safety')
    meds = ' '.join(f'- {line}' for line in unique_lines[:4])
    return f'{title} {meds} {warning}'


def maybe_capture_duration(text, message):
    if re.search(r'(\d+\s*(day|days|week|weeks|month|months))', text):
        return message.strip()
    if any(token in text for token in ['दिन', 'दिवस', 'రోజు', 'వారం']):
        return message.strip()
    return None


def maybe_capture_severity(text):
    if any(token in text for token in ['severe', 'high', 'बहुत', 'तीव्र', 'తీవ్ర']):
        return 'severe'
    if any(token in text for token in ['moderate', 'medium', 'मध्यम', 'మధ్యస్థ']):
        return 'moderate'
    if any(token in text for token in ['mild', 'light', 'हल्का', 'స్వల్ప']):
        return 'mild'
    return None


def build_local_triage_reply(message, chat_context, language_code):
    text = (message or '').strip().lower()
    if not text:
        return t(language_code, 'empty'), chat_context

    emergency_keywords = [
        'chest pain', 'breathing problem', 'faint', 'stroke', 'severe bleeding', 'suicidal',
        'सीने में दर्द', 'सांस नहीं', 'ఛాతి నొప్పి', 'శ్వాస ఇబ్బంది',
    ]
    if any(keyword in text for keyword in emergency_keywords):
        chat_context['risk'] = 'high'
        return t(language_code, 'emergency'), chat_context

    detected_symptoms = extract_symptoms(text)
    known_symptoms = set(chat_context.get('symptoms', []))
    known_symptoms.update(detected_symptoms)
    chat_context['symptoms'] = sorted(known_symptoms)

    duration = maybe_capture_duration(text, message)
    if duration:
        chat_context['duration'] = duration

    severity = maybe_capture_severity(text)
    if severity:
        chat_context['severity'] = severity

    if any(term in text for term in ['appointment', 'book', 'doctor', 'अपॉइंटमेंट', 'డాక్టర్']):
        specialist = choose_specialist(chat_context.get('symptoms', []))
        recommendation = get_doctor_hospital_recommendation(specialist)
        return (
            f'{t(language_code, "specialist")}: {specialist}. '
            f'{t(language_code, "recommended_doctor")}: {recommendation["doctor_name"]}. '
            f'{t(language_code, "recommended_hospital")}: {recommendation["hospital_name"]}. '
            f'{t(language_code, "doctor_profession")}: {recommendation["profession"]}. '
            f'{t(language_code, "book_hint")}'
        ), chat_context

    if not chat_context.get('symptoms'):
        return t(language_code, 'ask_symptoms'), chat_context

    specialist = choose_specialist(chat_context['symptoms'])
    recommendation = get_doctor_hospital_recommendation(specialist)
    severity_text = chat_context.get('severity', 'not specified')
    duration_text = chat_context.get('duration', 'not specified')

    response_parts = [
        f'{t(language_code, "symptoms")}: {", ".join(chat_context["symptoms"])}.',
        f'{t(language_code, "duration")}: {duration_text}. {t(language_code, "severity")}: {severity_text}.',
        f'{t(language_code, "specialist")}: {specialist}.',
        f'{t(language_code, "recommended_doctor")}: {recommendation["doctor_name"]}.',
        f'{t(language_code, "recommended_hospital")}: {recommendation["hospital_name"]}.',
        f'{t(language_code, "doctor_profession")}: {recommendation["profession"]}.',
        t(language_code, 'care'),
        t(language_code, 'persist'),
    ]

    medicine_text = medicine_suggestion_block(chat_context['symptoms'], language_code)
    if medicine_text:
        response_parts.append(medicine_text)

    response_parts.append(t(language_code, 'follow_up'))
    return ' '.join(response_parts), chat_context


def call_real_ai_agent(message, chat_context, language_code):
    api_key = os.getenv('OPENAI_API_KEY', '').strip()
    if not api_key:
        return None, chat_context

    model = os.getenv('OPENAI_MODEL', 'gpt-4.1-mini')
    base_url = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1').rstrip('/')
    endpoint = f'{base_url}/responses'

    history = chat_context.get('history', [])[-8:]
    lang_name = {'en': 'English', 'hi': 'Hindi', 'te': 'Telugu'}.get(language_code, 'English')

    system_prompt = (
        'You are a medical triage assistant for a hospital app. '
        'Do not provide a final diagnosis. Provide safe, conservative guidance, red-flag escalation, '
        'likely specialist type, and appointment recommendation. '
        f'Respond in {lang_name}. Keep answers practical and concise. '
        'If suggesting medicine, give generic OTC options only with strict safety warnings.'
    )

    input_messages = [{'role': 'system', 'content': system_prompt}]
    for item in history:
        input_messages.append({'role': item.get('role', 'user'), 'content': item.get('content', '')})
    input_messages.append({'role': 'user', 'content': message})

    payload = json.dumps({'model': model, 'input': input_messages}).encode('utf-8')
    req = urllib_request.Request(
        endpoint,
        data=payload,
        method='POST',
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}',
        },
    )

    try:
        with urllib_request.urlopen(req, timeout=20) as response:
            data = json.loads(response.read().decode('utf-8'))
    except (error.HTTPError, error.URLError, TimeoutError, json.JSONDecodeError):
        return None, chat_context

    reply = data.get('output_text', '').strip()
    if not reply:
        for item in data.get('output', []):
            for content_item in item.get('content', []):
                if content_item.get('type') == 'output_text':
                    reply = content_item.get('text', '').strip()
                    if reply:
                        break
            if reply:
                break

    if not reply:
        return None, chat_context

    updated_history = history + [{'role': 'user', 'content': message}, {'role': 'assistant', 'content': reply}]
    chat_context['history'] = updated_history[-10:]
    return reply, chat_context


def bootstrap_demo_data():
    """Create minimal demo data when key roles or appointments are missing."""
    admin = User.query.filter_by(email='admin@medicore.local').first()
    patient = User.query.filter_by(email='patient@medicore.local').first()

    changed = False

    if not admin:
        db.session.add(
            User(
                name='Admin User',
                email='admin@medicore.local',
                password=generate_password_hash('admin123'),
                role='admin',
            )
        )
        changed = True

    demo_doctors = [
        ('Ravi Kumar', 'doctor1@medicore.local'),
        ('Neha Sharma', 'doctor2@medicore.local'),
        ('Arjun Reddy', 'doctor3@medicore.local'),
    ]
    for doctor_name, doctor_email in demo_doctors:
        existing_doctor = User.query.filter_by(email=doctor_email).first()
        if not existing_doctor:
            db.session.add(
                User(
                    name=doctor_name,
                    email=doctor_email,
                    password=generate_password_hash('doctor123'),
                    role='doctor',
                )
            )
            changed = True

    if not patient:
        db.session.add(
            User(
                name='Anita Rao',
                email='patient@medicore.local',
                password=generate_password_hash('patient123'),
                role='patient',
            )
        )
        changed = True

    if changed:
        db.session.commit()
        patient = User.query.filter_by(email='patient@medicore.local').first()

    sample_doctor = User.query.filter_by(role='doctor').order_by(User.name.asc()).first()
    if Appointment.query.count() == 0 and sample_doctor and patient:
        now = datetime.now() + timedelta(days=1)
        db.session.add(
            Appointment(
                patient_name=patient.name,
                doctor_name=sample_doctor.name,
                hospital_name='MediCore General Hospital',
                hospital_location='Gajuwaka, Visakhapatnam',
                date=now.strftime('%Y-%m-%d'),
                time=now.strftime('%H:%M'),
                status='Pending',
                issue='Fever and throat pain for 2 days',
                prescription='',
            )
        )
        db.session.commit()

    if patient and sample_doctor and MedicalRecord.query.count() == 0:
        db.session.add(
            MedicalRecord(
                patient_name=patient.name,
                doctor_name=sample_doctor.name,
                diagnosis='Viral fever',
                medications='Paracetamol 650 mg SOS',
                notes='Hydration and rest advised.',
            )
        )

    if patient and sample_doctor and LabResult.query.count() == 0:
        db.session.add(
            LabResult(
                patient_name=patient.name,
                doctor_name=sample_doctor.name,
                test_name='CBC',
                result_value='WBC mildly elevated',
                normal_range='4,000 - 11,000 /uL',
                status='Final',
            )
        )

    if patient and Payment.query.count() == 0:
        db.session.add(
            Payment(
                patient_name=patient.name,
                amount=500.0,
                payment_for='OP Consultation',
                method='Card',
                status='Paid',
            )
        )

    if PharmacyItem.query.count() == 0:
        db.session.add(
            PharmacyItem(
                item_name='Paracetamol 500mg',
                stock_qty=120,
                expiry_date=(datetime.now() + timedelta(days=180)).strftime('%Y-%m-%d'),
                reorder_level=40,
            )
        )

    if BillingEntry.query.count() == 0:
        db.session.add(
            BillingEntry(
                entry_type='Invoice',
                subject='General OPD - February',
                amount=125000.0,
                status='Open',
            )
        )

    if HospitalSupply.query.count() == 0:
        db.session.add(
            HospitalSupply(
                supply_name='Surgical Masks',
                category='PPE',
                quantity=2000,
                min_level=500,
                unit='pieces',
            )
        )

    if StaffSchedule.query.count() == 0:
        db.session.add(
            StaffSchedule(
                staff_name='Nurse Priya',
                staff_role='Nurse',
                shift_date=(datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'),
                shift_slot='Morning',
                notes='Ward A',
            )
        )

    db.session.commit()


def ensure_appointment_issue_column():
    """Backfill schema for older databases that lack latest appointment columns."""
    columns = {column['name'] for column in inspect(db.engine).get_columns('appointment')}
    with db.engine.begin() as connection:
        if 'issue' not in columns:
            connection.execute(text("ALTER TABLE appointment ADD COLUMN issue TEXT DEFAULT ''"))
        if 'hospital_name' not in columns:
            connection.execute(text("ALTER TABLE appointment ADD COLUMN hospital_name VARCHAR(150) DEFAULT ''"))
        if 'hospital_location' not in columns:
            connection.execute(text("ALTER TABLE appointment ADD COLUMN hospital_location VARCHAR(200) DEFAULT ''"))


# -------------------------------------------------
# ROUTES
# -------------------------------------------------


@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for(role_dashboard_endpoint(current_user.role)))
    return render_template('index.html', platform_features=PLATFORM_FEATURES)


@app.route('/nearby-hospitals')
def nearby_hospitals():
    selected_city = (request.args.get('city', 'gajuwaka') or 'gajuwaka').strip().lower()
    if selected_city not in CITY_HOSPITALS:
        selected_city = 'gajuwaka'

    city_data = CITY_HOSPITALS[selected_city]
    city_options = [
        {'key': key, 'label': value['label']}
        for key, value in CITY_HOSPITALS.items()
    ]

    return render_template(
        'nearby_hospitals.html',
        hospitals=city_data['hospitals'],
        map_center=city_data['center'],
        selected_city=selected_city,
        selected_city_label=city_data['label'],
        city_options=city_options,
    )


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        role = request.form.get('role', '').strip().lower()

        if not name or not email or not password or role not in ALLOWED_ROLES:
            flash('Please provide valid registration details.', 'danger')
            return redirect(url_for('register'))

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered.', 'warning')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)

        new_user = User(name=name, email=email, password=hashed_password, role=role)
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Logged in successfully.', 'success')
            return redirect(url_for(role_dashboard_endpoint(user.role)))

        flash('Invalid credentials.', 'danger')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))


# -------------------------------------------------
# DASHBOARDS
# -------------------------------------------------


@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('You are not authorized to access the admin dashboard.', 'danger')
        return redirect(url_for(role_dashboard_endpoint(current_user.role)))

    appointments = Appointment.query.order_by(Appointment.id.desc()).all()

    total_appointments = len(appointments)
    total_doctors = User.query.filter_by(role='doctor').count()
    total_patients = User.query.filter_by(role='patient').count()
    doctors = User.query.filter_by(role='doctor').order_by(User.name.asc()).all()

    status_counts = {status: 0 for status in ALLOWED_STATUSES}
    for appointment in appointments:
        if appointment.status in status_counts:
            status_counts[appointment.status] += 1

    today = datetime.today().date()
    labels = [(today - timedelta(days=offset)) for offset in range(6, -1, -1)]
    label_text = [day.strftime('%a') for day in labels]
    daily_counts = {day.strftime('%Y-%m-%d'): 0 for day in labels}

    for appointment in appointments:
        parsed = parse_appointment_datetime(appointment.date, appointment.time)
        if parsed:
            key = parsed.date().strftime('%Y-%m-%d')
            if key in daily_counts:
                daily_counts[key] += 1

    weekly_counts = [daily_counts[day.strftime('%Y-%m-%d')] for day in labels]

    return render_template(
        'admin.html',
        appointments=appointments,
        total_appointments=total_appointments,
        total_doctors=total_doctors,
        total_patients=total_patients,
        doctors=doctors,
        weekly_labels=label_text,
        weekly_counts=weekly_counts,
        status_counts=status_counts,
    )


@app.route('/admin/doctors/add', methods=['POST'])
@login_required
def add_doctor():
    if current_user.role != 'admin':
        flash('Only admin can add doctors.', 'danger')
        return redirect(url_for(role_dashboard_endpoint(current_user.role)))

    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '').strip() or 'doctor123'

    if not name or not email:
        flash('Doctor name and email are required.', 'danger')
        return redirect(url_for('admin_dashboard'))

    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        flash('Email already exists.', 'warning')
        return redirect(url_for('admin_dashboard'))

    db.session.add(
        User(
            name=name,
            email=email,
            password=generate_password_hash(password),
            role='doctor',
        )
    )
    db.session.commit()
    flash('Doctor added successfully.', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/doctor')
@login_required
def doctor_dashboard():
    if current_user.role != 'doctor':
        flash('You are not authorized to access the doctor dashboard.', 'danger')
        return redirect(url_for(role_dashboard_endpoint(current_user.role)))

    appointments = Appointment.query.filter_by(doctor_name=current_user.name).order_by(
        Appointment.date.asc(), Appointment.time.asc()
    ).all()

    return render_template('doctor.html', appointments=appointments)


@app.route('/patient')
@login_required
def patient_dashboard():
    if current_user.role != 'patient':
        flash('You are not authorized to access the patient dashboard.', 'danger')
        return redirect(url_for(role_dashboard_endpoint(current_user.role)))

    appointments = Appointment.query.filter_by(patient_name=current_user.name).order_by(
        Appointment.date.asc(), Appointment.time.asc()
    ).all()

    doctors = User.query.filter_by(role='doctor').order_by(User.name.asc()).all()

    return render_template('patient.html', appointments=appointments, doctors=doctors)


@app.route('/patient/recommendation', methods=['POST'])
@login_required
def patient_recommendation():
    if current_user.role != 'patient':
        return jsonify({'error': 'Only patients can access recommendations.'}), 403

    payload = request.get_json(silent=True) or {}
    issue = (payload.get('issue') or '').strip().lower()
    if len(issue) < 3:
        return jsonify({'ok': True, 'suggested': False})

    symptoms = extract_symptoms(issue)
    specialist = choose_specialist(symptoms)
    recommendation = get_doctor_hospital_recommendation(specialist)

    return jsonify(
        {
            'ok': True,
            'suggested': True,
            'doctor_name': recommendation['doctor_name'],
            'hospital_name': recommendation['hospital_name'],
            'hospital_location': recommendation['hospital_location'],
            'profession': recommendation['profession'],
        }
    )


@app.route('/chatbot')
@login_required
def chatbot_page():
    doctors = User.query.filter_by(role='doctor').order_by(User.name.asc()).all()
    ai_available = bool(os.getenv('OPENAI_API_KEY', '').strip())
    current_lang = normalize_language(session.get('chatbot_language', 'en'))
    return render_template('chatbot.html', doctors=doctors, ai_available=ai_available, current_lang=current_lang)


@app.route('/chatbot/message', methods=['POST'])
@login_required
def chatbot_message():
    payload = request.get_json(silent=True) or {}
    message = payload.get('message', '')
    language_code = normalize_language(payload.get('language') or session.get('chatbot_language', 'en'))
    session['chatbot_language'] = language_code

    chat_context = session.get('chatbot_context', {})
    use_real_ai = bool(payload.get('use_real_ai', True))
    reply = None
    ai_used = False

    if use_real_ai:
        reply, chat_context = call_real_ai_agent(message, chat_context, language_code)
        ai_used = bool(reply)

    if not reply:
        reply, chat_context = build_local_triage_reply(message, chat_context, language_code)

    updated_context = chat_context
    session['chatbot_context'] = updated_context
    return jsonify({'reply': reply, 'ai_used': ai_used, 'language': language_code})


@app.route('/chatbot/reset', methods=['POST'])
@login_required
def chatbot_reset():
    session.pop('chatbot_context', None)
    session.pop('chatbot_language', None)
    return jsonify({'ok': True})


# -------------------------------------------------
# APPOINTMENT BOOKING
# -------------------------------------------------


@app.route('/book', methods=['POST'])
@login_required
def book():
    if current_user.role != 'patient':
        flash('Only patients can book appointments.', 'danger')
        return redirect(url_for(role_dashboard_endpoint(current_user.role)))

    doctor_name = request.form.get('doctor', '').strip()
    hospital_name = request.form.get('hospital_name', '').strip()
    hospital_location = request.form.get('hospital_location', '').strip()
    date = request.form.get('date', '').strip()
    time = request.form.get('time', '').strip()
    issue = request.form.get('issue', '').strip()

    doctor = User.query.filter_by(name=doctor_name, role='doctor').first()
    if not doctor:
        flash('Selected doctor does not exist.', 'danger')
        return redirect(url_for('patient_dashboard'))

    appointment_dt = parse_appointment_datetime(date, time)
    if not appointment_dt:
        flash('Please enter a valid date and time.', 'danger')
        return redirect(url_for('patient_dashboard'))

    if appointment_dt < datetime.now():
        flash('Appointment time cannot be in the past.', 'warning')
        return redirect(url_for('patient_dashboard'))

    slot_taken = Appointment.query.filter_by(doctor_name=doctor_name, date=date, time=time).filter(
        Appointment.status != 'Cancelled'
    ).first()
    if slot_taken:
        flash('Selected slot is not available. Please choose another time.', 'warning')
        return redirect(url_for('patient_dashboard'))

    if len(issue) < 10:
        flash('Please describe your issue in at least 10 characters.', 'warning')
        return redirect(url_for('patient_dashboard'))

    if not hospital_name or not hospital_location:
        flash('Hospital name and hospital location are required.', 'warning')
        return redirect(url_for('patient_dashboard'))

    new_appointment = Appointment(
        patient_name=current_user.name,
        doctor_name=doctor_name,
        hospital_name=hospital_name,
        hospital_location=hospital_location,
        date=date,
        time=time,
        status='Pending',
        issue=issue,
    )

    db.session.add(new_appointment)
    db.session.commit()

    flash('Appointment booked successfully.', 'success')
    return redirect(url_for('patient_dashboard'))


# -------------------------------------------------
# UPDATE APPOINTMENT (DOCTOR)
# -------------------------------------------------


@app.route('/update/<int:id>', methods=['POST'])
@login_required
def update(id):
    if current_user.role != 'doctor':
        flash('Only doctors can update appointments.', 'danger')
        return redirect(url_for(role_dashboard_endpoint(current_user.role)))

    appointment = Appointment.query.get_or_404(id)
    if appointment.doctor_name != current_user.name:
        flash('You can only update your own appointments.', 'danger')
        return redirect(url_for('doctor_dashboard'))

    status = request.form.get('status', '').strip().title()
    prescription = request.form.get('prescription', '').strip()

    if status not in ALLOWED_STATUSES:
        flash('Invalid status selected.', 'danger')
        return redirect(url_for('doctor_dashboard'))

    appointment.status = status
    appointment.prescription = prescription

    db.session.commit()

    flash('Appointment updated successfully.', 'success')
    return redirect(url_for('doctor_dashboard'))


# -------------------------------------------------
# FEATURE MODULES
# -------------------------------------------------


@app.route('/patient/portal')
@login_required
def patient_portal():
    if current_user.role != 'patient':
        flash('Only patients can access the patient portal.', 'danger')
        return redirect(url_for(role_dashboard_endpoint(current_user.role)))

    records = MedicalRecord.query.filter_by(patient_name=current_user.name).order_by(MedicalRecord.created_at.desc()).all()
    lab_results = LabResult.query.filter_by(patient_name=current_user.name).order_by(LabResult.created_at.desc()).all()
    payments = Payment.query.filter_by(patient_name=current_user.name).order_by(Payment.created_at.desc()).all()
    telemedicine_sessions = TelemedicineSession.query.filter_by(patient_name=current_user.name).order_by(
        TelemedicineSession.created_at.desc()
    ).all()
    total_paid = sum(entry.amount for entry in payments if entry.status.lower() == 'paid')

    return render_template(
        'patient_portal.html',
        records=records,
        lab_results=lab_results,
        payments=payments,
        telemedicine_sessions=telemedicine_sessions,
        total_paid=total_paid,
    )


@app.route('/patient/payments/add', methods=['POST'])
@login_required
def patient_add_payment():
    if current_user.role != 'patient':
        flash('Only patients can submit payments.', 'danger')
        return redirect(url_for(role_dashboard_endpoint(current_user.role)))

    payment_for = request.form.get('payment_for', '').strip()
    method = request.form.get('method', '').strip()
    try:
        amount = float(request.form.get('amount', '0').strip())
    except ValueError:
        amount = 0.0

    if not payment_for or not method or amount <= 0:
        flash('Please provide valid payment details.', 'danger')
        return redirect(url_for('patient_portal'))

    status = 'Claim Submitted' if method.lower() == 'insurance' else 'Paid'
    payment = Payment(
        patient_name=current_user.name,
        amount=amount,
        payment_for=payment_for,
        method=method,
        status=status,
    )
    db.session.add(payment)
    db.session.add(
        BillingEntry(
            entry_type='Patient Payment',
            subject=f'{current_user.name} - {payment_for}',
            amount=amount,
            status=status,
        )
    )

    if method.lower() == 'insurance':
        db.session.add(
            BillingEntry(
                entry_type='Insurance Claim',
                subject=f'{current_user.name} - {payment_for}',
                amount=amount,
                status='Under Review',
            )
        )

    db.session.commit()
    flash('Payment entry added successfully.', 'success')
    return redirect(url_for('patient_portal'))


@app.route('/doctor/tools')
@login_required
def doctor_tools():
    if current_user.role != 'doctor':
        flash('Only doctors can access this module.', 'danger')
        return redirect(url_for(role_dashboard_endpoint(current_user.role)))

    my_appointments = Appointment.query.filter_by(doctor_name=current_user.name).order_by(
        Appointment.date.desc(), Appointment.time.desc()
    ).all()
    my_records = MedicalRecord.query.filter_by(doctor_name=current_user.name).order_by(MedicalRecord.created_at.desc()).all()
    my_labs = LabResult.query.filter_by(doctor_name=current_user.name).order_by(LabResult.created_at.desc()).all()
    pharmacy_items = PharmacyItem.query.order_by(PharmacyItem.item_name.asc()).all()
    telemedicine_sessions = TelemedicineSession.query.filter_by(doctor_name=current_user.name).order_by(
        TelemedicineSession.created_at.desc()
    ).all()

    return render_template(
        'doctor_tools.html',
        appointments=my_appointments,
        records=my_records,
        lab_results=my_labs,
        pharmacy_items=pharmacy_items,
        telemedicine_sessions=telemedicine_sessions,
    )


@app.route('/doctor/records/add', methods=['POST'])
@login_required
def doctor_add_record():
    if current_user.role != 'doctor':
        flash('Only doctors can add records.', 'danger')
        return redirect(url_for(role_dashboard_endpoint(current_user.role)))

    patient_name = request.form.get('patient_name', '').strip()
    diagnosis = request.form.get('diagnosis', '').strip()
    medications = request.form.get('medications', '').strip()
    notes = request.form.get('notes', '').strip()

    if not patient_name or not diagnosis:
        flash('Patient name and diagnosis are required.', 'danger')
        return redirect(url_for('doctor_tools'))

    db.session.add(
        MedicalRecord(
            patient_name=patient_name,
            doctor_name=current_user.name,
            diagnosis=diagnosis,
            medications=medications,
            notes=notes,
        )
    )
    db.session.commit()
    flash('EHR record saved.', 'success')
    return redirect(url_for('doctor_tools'))


@app.route('/doctor/labs/add', methods=['POST'])
@login_required
def doctor_add_lab_result():
    if current_user.role != 'doctor':
        flash('Only doctors can add lab results.', 'danger')
        return redirect(url_for(role_dashboard_endpoint(current_user.role)))

    patient_name = request.form.get('patient_name', '').strip()
    test_name = request.form.get('test_name', '').strip()
    result_value = request.form.get('result_value', '').strip()
    normal_range = request.form.get('normal_range', '').strip()
    status = request.form.get('status', 'Final').strip() or 'Final'

    if not patient_name or not test_name or not result_value:
        flash('Patient, test name and result are required.', 'danger')
        return redirect(url_for('doctor_tools'))

    db.session.add(
        LabResult(
            patient_name=patient_name,
            doctor_name=current_user.name,
            test_name=test_name,
            result_value=result_value,
            normal_range=normal_range,
            status=status,
        )
    )
    db.session.commit()
    flash('Lab result saved and shared with patient portal.', 'success')
    return redirect(url_for('doctor_tools'))


@app.route('/doctor/pharmacy/add', methods=['POST'])
@login_required
def doctor_add_pharmacy_item():
    if current_user.role != 'doctor':
        flash('Only doctors can update pharmacy items.', 'danger')
        return redirect(url_for(role_dashboard_endpoint(current_user.role)))

    item_name = request.form.get('item_name', '').strip()
    expiry_date = request.form.get('expiry_date', '').strip()
    try:
        stock_qty = int(request.form.get('stock_qty', '0').strip())
        reorder_level = int(request.form.get('reorder_level', '0').strip())
    except ValueError:
        stock_qty = -1
        reorder_level = -1

    if not item_name or not parse_date(expiry_date) or stock_qty < 0 or reorder_level < 0:
        flash('Please provide valid pharmacy item details.', 'danger')
        return redirect(url_for('doctor_tools'))

    existing = PharmacyItem.query.filter_by(item_name=item_name).first()
    if existing:
        existing.stock_qty = stock_qty
        existing.expiry_date = expiry_date
        existing.reorder_level = reorder_level
    else:
        db.session.add(
            PharmacyItem(
                item_name=item_name,
                stock_qty=stock_qty,
                expiry_date=expiry_date,
                reorder_level=reorder_level,
            )
        )
    db.session.commit()
    flash('Pharmacy inventory updated.', 'success')
    return redirect(url_for('doctor_tools'))


@app.route('/doctor/telemedicine/create', methods=['POST'])
@login_required
def doctor_create_telemedicine():
    if current_user.role != 'doctor':
        flash('Only doctors can create telemedicine sessions.', 'danger')
        return redirect(url_for(role_dashboard_endpoint(current_user.role)))

    appointment_id = request.form.get('appointment_id', '').strip()
    appointment = Appointment.query.get_or_404(int(appointment_id)) if appointment_id.isdigit() else None
    if not appointment or appointment.doctor_name != current_user.name:
        flash('Invalid appointment selected.', 'danger')
        return redirect(url_for('doctor_tools'))

    existing = TelemedicineSession.query.filter_by(appointment_id=appointment.id).first()
    if existing:
        flash('Telemedicine session already exists for this appointment.', 'warning')
        return redirect(url_for('doctor_tools'))

    room_link = request.form.get('room_link', '').strip()
    if not room_link:
        room_key = f"medicore-{appointment.id}-{appointment.date.replace('-', '')}-{appointment.time.replace(':', '')}"
        room_link = f'https://meet.jit.si/{room_key}'

    db.session.add(
        TelemedicineSession(
            appointment_id=appointment.id,
            patient_name=appointment.patient_name,
            doctor_name=appointment.doctor_name,
            room_link=room_link,
            status='Scheduled',
        )
    )
    db.session.commit()
    flash('Telemedicine session created.', 'success')
    return redirect(url_for('doctor_tools'))


@app.route('/admin/operations')
@login_required
def admin_operations():
    if current_user.role != 'admin':
        flash('Only admin can access operations.', 'danger')
        return redirect(url_for(role_dashboard_endpoint(current_user.role)))

    billing_entries = BillingEntry.query.order_by(BillingEntry.created_at.desc()).all()
    patient_payments = Payment.query.order_by(Payment.created_at.desc()).all()
    supplies = HospitalSupply.query.order_by(HospitalSupply.supply_name.asc()).all()
    schedules = StaffSchedule.query.order_by(StaffSchedule.shift_date.desc(), StaffSchedule.id.desc()).all()
    pharmacy_items = PharmacyItem.query.order_by(PharmacyItem.item_name.asc()).all()
    appointments = Appointment.query.order_by(Appointment.date.asc(), Appointment.time.asc()).all()
    upcoming_appointments = []
    now = datetime.now()
    for appointment in appointments:
        parsed = parse_appointment_datetime(appointment.date, appointment.time)
        if parsed and parsed >= now and appointment.status != 'Cancelled':
            upcoming_appointments.append(appointment)

    low_supplies = [item for item in supplies if item.quantity <= item.min_level]
    today = now.date()
    low_pharmacy = []
    for item in pharmacy_items:
        expiry = parse_date(item.expiry_date)
        if item.stock_qty <= item.reorder_level or (expiry and expiry <= today):
            low_pharmacy.append(item)

    return render_template(
        'admin_operations.html',
        billing_entries=billing_entries,
        patient_payments=patient_payments,
        supplies=supplies,
        schedules=schedules,
        pharmacy_items=pharmacy_items,
        low_supplies=low_supplies,
        low_pharmacy=low_pharmacy,
        upcoming_appointments=upcoming_appointments,
    )


@app.route('/admin/billing/add', methods=['POST'])
@login_required
def admin_add_billing():
    if current_user.role != 'admin':
        flash('Only admin can add billing entries.', 'danger')
        return redirect(url_for(role_dashboard_endpoint(current_user.role)))

    entry_type = request.form.get('entry_type', '').strip()
    subject = request.form.get('subject', '').strip()
    status = request.form.get('status', 'Open').strip() or 'Open'
    try:
        amount = float(request.form.get('amount', '0').strip())
    except ValueError:
        amount = 0.0

    if not entry_type or not subject or amount <= 0:
        flash('Please provide valid billing details.', 'danger')
        return redirect(url_for('admin_operations'))

    db.session.add(BillingEntry(entry_type=entry_type, subject=subject, amount=amount, status=status))
    db.session.commit()
    flash('Billing entry created.', 'success')
    return redirect(url_for('admin_operations'))


@app.route('/admin/supplies/add', methods=['POST'])
@login_required
def admin_add_supply():
    if current_user.role != 'admin':
        flash('Only admin can update supplies.', 'danger')
        return redirect(url_for(role_dashboard_endpoint(current_user.role)))

    supply_name = request.form.get('supply_name', '').strip()
    category = request.form.get('category', '').strip()
    unit = request.form.get('unit', '').strip() or 'units'
    try:
        quantity = int(request.form.get('quantity', '0').strip())
        min_level = int(request.form.get('min_level', '0').strip())
    except ValueError:
        quantity = -1
        min_level = -1

    if not supply_name or not category or quantity < 0 or min_level < 0:
        flash('Please provide valid supply details.', 'danger')
        return redirect(url_for('admin_operations'))

    existing = HospitalSupply.query.filter_by(supply_name=supply_name).first()
    if existing:
        existing.category = category
        existing.quantity = quantity
        existing.min_level = min_level
        existing.unit = unit
    else:
        db.session.add(
            HospitalSupply(
                supply_name=supply_name,
                category=category,
                quantity=quantity,
                min_level=min_level,
                unit=unit,
            )
        )

    db.session.commit()
    flash('Hospital supply inventory updated.', 'success')
    return redirect(url_for('admin_operations'))


@app.route('/admin/schedules/add', methods=['POST'])
@login_required
def admin_add_schedule():
    if current_user.role != 'admin':
        flash('Only admin can manage schedules.', 'danger')
        return redirect(url_for(role_dashboard_endpoint(current_user.role)))

    staff_name = request.form.get('staff_name', '').strip()
    staff_role = request.form.get('staff_role', '').strip()
    shift_date = request.form.get('shift_date', '').strip()
    shift_slot = request.form.get('shift_slot', '').strip()
    notes = request.form.get('notes', '').strip()

    if not staff_name or not staff_role or not parse_date(shift_date) or not shift_slot:
        flash('Please provide valid schedule details.', 'danger')
        return redirect(url_for('admin_operations'))

    db.session.add(
        StaffSchedule(
            staff_name=staff_name,
            staff_role=staff_role,
            shift_date=shift_date,
            shift_slot=shift_slot,
            notes=notes,
        )
    )
    db.session.commit()
    flash('Staff schedule added.', 'success')
    return redirect(url_for('admin_operations'))


@app.route('/telemedicine/join/<int:session_id>')
@login_required
def join_telemedicine(session_id):
    session_obj = TelemedicineSession.query.get_or_404(session_id)
    if current_user.role == 'patient' and session_obj.patient_name != current_user.name:
        flash('You are not allowed to join this session.', 'danger')
        return redirect(url_for('patient_portal'))
    if current_user.role == 'doctor' and session_obj.doctor_name != current_user.name:
        flash('You are not allowed to join this session.', 'danger')
        return redirect(url_for('doctor_tools'))
    if current_user.role == 'admin':
        flash('Admin cannot join patient telemedicine sessions.', 'warning')
        return redirect(url_for('admin_operations'))
    return redirect(session_obj.room_link)


# -------------------------------------------------
# MAIN
# -------------------------------------------------


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        ensure_appointment_issue_column()
        bootstrap_demo_data()

    app.run(debug=True)
