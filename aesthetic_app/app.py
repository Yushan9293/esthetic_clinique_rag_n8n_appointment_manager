import os
import streamlit as st
from dotenv import load_dotenv
from backend.loader import load_documents
from backend.qa_chain_compatible_0325 import build_qa_chain
import json
from pathlib import Path
from langchain_core.runnables import RunnableConfig
from backend.calendar_utils import get_available_slots
from datetime import datetime
import requests
import uuid  

# Load environment variables from .env file
load_dotenv()
N8N_WEBHOOK_BOOK = os.getenv("WEBHOOK_BOOK")
credentials_path = os.getenv("GOOGLE_CREDENTIALS_PATH")

# Load treatment data from JSON
with open("data/aesthetic_treatments_final.json", "r", encoding="utf-8") as f:
    treatment_data_list = json.load(f)

fallback_duration = {
    "Consultation": 20,
    "Follow-up": 15
}

def get_duration(service_name, treatment_data_list):
    for treatment in treatment_data_list:
        if treatment["treatment"].lower() == service_name.lower():
            return treatment.get("duration", 30)
    return fallback_duration.get(service_name, 30)

st.set_page_config(page_title="💉 MedSpa RAG Chatbot")
st.title("💬 Ask our AI Aesthetic Assistant")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

@st.cache_resource
def init_chain(data_version: float):  
    docs = load_documents("data/aesthetic_treatments_final.json")
    return build_qa_chain(docs)

data_version = Path("data/aesthetic_treatments_final.json").stat().st_mtime
qa_chain = init_chain(data_version)


query = st.text_input(
    "What would you like to know about our treatments?",
    placeholder="e.g., Can I wear makeup after microneedling?"
)

def detect_booking_intent(message: str) -> bool:
    keywords = ["book", "appointment", "consultation", "schedule", "I'd like to come", "can I visit", "预约", "咨询"]
    return any(k.lower() in message.lower() for k in keywords)

if query:
    with st.spinner("Thinking..."):
        if isinstance(query, dict):
            query = json.dumps(query)

        assert isinstance(query, str)

        if detect_booking_intent(query):
            st.warning("🗓️ It looks like you'd like to book a consultation or treatment. Please fill in your info below 👇")

            if "selected_doctor" not in st.session_state:
                st.session_state.selected_doctor = "No preference"

            if "selected_date" not in st.session_state:
                st.session_state.selected_date = datetime.today().date()

            new_doctor = st.selectbox(
                "Select your preferred doctor",
                ["No preference", "Dr A", "Dr B"],
                index=["No preference", "Dr A", "Dr B"].index(st.session_state.selected_doctor)
            )
            if new_doctor != st.session_state.selected_doctor:
                st.session_state.selected_doctor = new_doctor
                st.rerun()

            new_date = st.date_input(
                "Select appointment date",
                value=st.session_state.selected_date,
                min_value=datetime.today().date()
            )
            if new_date != st.session_state.selected_date:
                st.session_state.selected_date = new_date
                st.rerun()

            treatment_options = ["Consultation"] + [t["treatment"] for t in treatment_data_list]
            service = st.selectbox("Select a treatment", treatment_options)
            duration = get_duration(service, treatment_data_list)

            date_str = st.session_state.selected_date.strftime("%Y-%m-%d")
            doctor = st.session_state.selected_doctor
            slots = []

            if doctor == "No preference":
                for doc in ["Dr A", "Dr B"]:
                    temp = get_available_slots(doc, date_str, duration)
                    if temp:
                        slots = temp
                        doctor = doc
                        st.session_state.selected_doctor = doc
                        st.info(f"👨‍⚕️ Automatically assigned to **{doc}** with available slots.")
                        break
            else:
                slots = get_available_slots(doctor, date_str, duration)

            slot_key = f"slot_{doctor}_{date_str}"
            if slots:
                time_slot = st.selectbox("Choose a time slot", options=slots, key=slot_key)
            else:
                time_slot = None
                st.info("⚠️ No available slots for the selected date and doctor.")

            with st.form("booking_form"):
                name = st.text_input("Name")
                email = st.text_input("Email")
                phone = st.text_input("Phone")
                age = st.text_input("Age")
                allergy = st.text_input("Do you have any known allergies?")
                recent_treatment = st.text_input("Any recent aesthetic treatments?")

                submitted = st.form_submit_button("Submit Booking")
                if submitted:
                    if not time_slot:
                        st.error("❌ Please select a valid time slot.")
                    else:
                        note_parts = []
                        if allergy:
                            note_parts.append(f"Allergy: {allergy}")
                        if recent_treatment:
                            note_parts.append(f"Recent treatment: {recent_treatment}")
                        note = ". ".join(note_parts)

                        # ✅ Generate permanent booking_id
                        booking_id = str(uuid.uuid4())

                        payload = {
                            "booking_id": booking_id,  # ✅ NEW
                            "name": name,
                            "email": email,
                            "phone": phone,
                            "age": age,
                            "service": service,
                            "doctor": doctor,
                            "date": time_slot,
                            "duration": duration,
                            "note": note
                        }

                        res = requests.post(
                            N8N_WEBHOOK_BOOK,
                            json=payload
                        )

                        if res.status_code == 200:
                            st.success("✅ Your booking request has been sent!")
                        else:
                            st.error("❌ Failed to send booking. Please try again.")
        else:
            result = qa_chain.invoke(
                {"question": query},
                config=RunnableConfig(configurable={"session_id": "user"})
            )
            answer = result
            st.session_state.chat_history.append((query, answer))

if st.session_state.chat_history:
    st.markdown("---")
    for q, a in reversed(st.session_state.chat_history):
        st.markdown(f"**🧍 You:** {q}")
        st.markdown(f"**🧴 Assistant:** {a}")
        st.markdown("---")


