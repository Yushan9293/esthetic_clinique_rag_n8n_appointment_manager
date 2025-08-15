# Esthetic Clinique RAG + n8n Appointment Manager

<a href="https://youtu.be/RSWfQzccIQk" target="_blank">
  <img src="https://raw.githubusercontent.com/Yushan9293/esthetic_clinique_rag_n8n_appointment_manager/main/cover.png" width="720">
</a>

AI-powered assistant for aesthetic clinics, integrating **LangChain RAG** and **n8n workflow automation** to manage clinic appointments.  
Supports **booking**, **rescheduling**, and **canceling** appointments with real-time Google Calendar & Google Sheets synchronization.

---

## ✨ Features

- **RAG (Retrieval-Augmented Generation)**:  
  Uses LangChain to answer clinic FAQs from your own documents.
- **n8n Workflow Integration**:  
  Automates booking, rescheduling, and canceling appointments.
- **Google Calendar Sync**:  
  Shows available time slots, updates automatically.
- **Google Sheets Integration**:  
  Stores and retrieves patient information.
- **Streamlit UI**:  
  Clean and interactive web interface for staff and patients.
- **Email Notifications**:  
  Sends Gmail confirmation for booking, rescheduling, and canceling appointments.
- **Custom Prompting**:  
  Tailored summaries and responses in the clinic’s tone.

---

## 🛠 Tech Stack

- **Frontend**: [Streamlit](https://streamlit.io/)  
- **Backend**: [Python](https://www.python.org/) + [LangChain](https://www.langchain.com/)  
- **Database**: [ChromaDB](https://www.trychroma.com/) (vector store)  
- **Automation**: [n8n](https://n8n.io/)  
- **Integrations**: Google Calendar API, Google Sheets API, Gmail  
- **Environment**: `.env` for API keys & credentials

---

## 📦 Installation

### 1. Clone the repository
```bash
git clone https://github.com/Yushan9293/esthetic_clinique_rag_n8n_appointment_manager.git
cd esthetic_clinique_rag_n8n_appointment_manager
````

### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate   # macOS/Linux
venv\Scripts\activate      # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## 🔑 Environment Variables

Create a `.env` file in the project root:

```env
# OpenAI
OPENAI_API_KEY=your_openai_api_key

# Google Calendar (per doctor)
DOCTOR_A_CALENDAR_ID=calendar_id_for_doctor_A
DOCTOR_B_CALENDAR_ID=calendar_id_for_doctor_B

# n8n Webhooks
WEBHOOK_BOOK=https://your_n8n_instance/webhook/book
WEBHOOK_MANAGE=https://your_n8n_instance/webhook/manage

# Google API credentials
GOOGLE_CREDENTIALS_PATH=credentials.json
```

You must also enable the **Google Calendar API** and **Google Sheets API** in your Google Cloud project.

---

## ▶️ Run the App

> Use separate terminals if running both at once. Specify different ports.

### 1. Client / Booking Interface

```bash
python -m streamlit run aesthetic_app/app.py --server.port 8501
```

Open your browser at `http://localhost:8501`.

### 2. Doctor Dashboard

```bash
python -m streamlit run doctor_dashboard.py --server.port 8502
```

Open your browser at `http://localhost:8502`.

---

## 🧩 How It Works

1. **User selects appointment action**: book, reschedule, or cancel.
2. **System fetches available time slots** from Google Calendar (via n8n workflow).
3. **Action processed**:

   * Book → Creates event in Google Calendar + stores data in Google Sheets + sends confirmation email
   * Reschedule → Updates event and Sheets entry + sends updated confirmation email
   * Cancel → Deletes event and updates Sheets + sends cancellation email
4. **RAG chatbot** answers clinic-related questions using your custom knowledge base.

---

## 📌 Project Structure

```
esthetic_clinique_rag_n8n_appointment_manager/
├── aesthetic_app/
│   ├── app.py                 # Client booking interface
│   └── pages/
│       └── manage_booking.py  # Booking/reschedule/cancel flow
├── backend/
│   ├── loader.py              # Load clinic documents
│   ├── calendar_utils.py      # Google Calendar integration
│   ├── sheet_utils.py         # Google Sheets integration
│   └── qa_chain_*.py          # LangChain QA chain
├── data/
│   └── aesthetic_treatments_final.json  # Treatment config / catalog
├── doctor_dashboard.py        # Doctor management dashboard (root)
├── .env                       # Environment variables (not committed)
├── requirements.txt
└── README.md
```

---

## 🚀 Future Improvements

* Multi-language chatbot support
* Payment integration for online booking
* Patient portal with authentication

---

## 📄 License

MIT License. Feel free to modify and use.

---

**Author:** [Yushan LIN](https://github.com/Yushan9293)
💬 *AI Solutions for Clinics — from booking automation to intelligent patient support.*

```

---

