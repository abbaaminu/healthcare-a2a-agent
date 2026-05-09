import os
from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Dict, Any, List
from datetime import datetime

# Create the FastAPI app
app = FastAPI(title="Healthcare A2A Agent")

# Enable CORS for Prompt Opinion
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# ROOT ENDPOINT - This fixes the "Not Found" error
# ============================================
@app.get("/")
async def root():
    return {
        "message": "Healthcare A2A Agent is running!",
        "version": "1.0.0",
        "status": "active",
        "endpoints": {
            "health": "/health",
            "task": "/task (POST)",
            "agent_card": "/.well-known/ai-agent.json"
        },
        "instructions": "Send POST requests to /task with FHIR data"
    }

# ============================================
# HEALTH CHECK ENDPOINT
# ============================================
@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "Healthcare A2A Agent",
        "version": "1.0",
        "timestamp": datetime.now().isoformat(),
        "ready": True
    }

# ============================================
# AGENT CARD FOR PROMPT OPINION
# ============================================
@app.get("/.well-known/ai-agent.json")
@app.get("/agent-card.json")
async def agent_card():
    return {
        "name": "Healthcare A2A Risk Analyzer",
        "description": "Clinical agent analyzing blood pressure, medications, and cardiovascular risk using FHIR data. Provides evidence-based recommendations and clinical decision support.",
        "version": "1.0.0",
        "capabilities": [
            "blood_pressure_classification",
            "medication_reconciliation",
            "risk_assessment",
            "clinical_guidelines"
        ],
        "endpoint": "/task",
        "health_endpoint": "/health",
        "input_format": {
            "message": "string - Clinician query",
            "context.fhir_resources": "array - FHIR patient resources"
        }
    }

# ============================================
# MAIN TASK ENDPOINT
# ============================================
@app.post("/task")
async def handle_task(payload: Dict[str, Any] = Body(...)):
    try:
        # Get the message and FHIR resources
        message = payload.get("message", "")
        resources = payload.get("context", {}).get("fhir_resources", [])
        
        # Extract data from FHIR
        bp_systolic = 0
        bp_diastolic = 0
        medications = []
        patient_age = None
        patient_gender = None
        
        for resource in resources:
            resource_type = resource.get("resourceType")
            
            if resource_type == "Patient":
                patient_gender = resource.get("gender")
                birth_date = resource.get("birthDate")
                if birth_date:
                    try:
                        birth_year = int(birth_date.split("-")[0])
                        patient_age = datetime.now().year - birth_year
                    except:
                        pass
            
            elif resource_type == "Observation":
                code_text = str(resource.get("code", {}).get("text", "")).lower()
                
                # Check for blood pressure
                if "blood pressure" in code_text or "85354-9" in code_text:
                    components = resource.get("component", [])
                    for component in components:
                        comp_text = str(component.get("code", {}).get("text", "")).lower()
                        value = component.get("valueQuantity", {}).get("value", 0)
                        if "systolic" in comp_text or "8480-6" in comp_text:
                            bp_systolic = value
                        elif "diastolic" in comp_text or "8462-4" in comp_text:
                            bp_diastolic = value
            
            elif resource_type == "MedicationRequest":
                med_name = resource.get("medicationCodeableConcept", {}).get("text", "")
                if med_name:
                    medications.append(med_name)
        
        # Clinical logic - Blood Pressure Classification
        if bp_systolic >= 140 or bp_diastolic >= 90:
            bp_category = "Stage 2 Hypertension"
            bp_guidance = "Immediate clinical follow-up required. Consider initiating or adjusting antihypertensive medication."
            urgency = "HIGH"
        elif bp_systolic >= 130 or bp_diastolic >= 80:
            bp_category = "Stage 1 Hypertension"
            bp_guidance = "Lifestyle modifications recommended (DASH diet, exercise, sodium restriction). Reassess in 3-6 months."
            urgency = "MEDIUM"
        else:
            bp_category = "Normal"
            bp_guidance = "Continue routine monitoring annually. Maintain healthy lifestyle."
            urgency = "LOW"
        
        # Build the clinical recommendation text
        response_text = f"""🏥 CLINICAL ASSESSMENT REPORT

📊 VITAL SIGNS:
• Blood Pressure: {bp_systolic}/{bp_diastolic} mmHg
• Classification: {bp_category}
• Urgency Level: {urgency}

💊 MEDICATIONS:
{', '.join(medications) if medications else 'None documented'}

"""

        if patient_age:
            response_text += f"👤 PATIENT: {patient_age} years old ({patient_gender or 'gender not specified'})\n\n"

        response_text += f"""📋 CLINICAL RECOMMENDATION:
{bp_guidance}

✅ NEXT STEPS:
• Confirm BP reading with repeat measurement in clinic
• Review medication adherence
{ '• Schedule follow-up appointment within 4 weeks' if bp_category != 'Normal' else '• Continue annual health maintenance' }

📚 EVIDENCE BASE:
• ACC/AHA 2017 Hypertension Guidelines
• JNC 8 Evidence-Based Recommendations
"""

        # Return the A2A-compliant response
        return JSONResponse(content={
            "status": "completed",
            "output": {
                "text": response_text,
                "tool_outputs": {
                    "blood_pressure": {
                        "systolic": bp_systolic,
                        "diastolic": bp_diastolic,
                        "category": bp_category,
                        "guidance": bp_guidance,
                        "urgency": urgency
                    },
                    "medications": medications,
                    "patient_age": patient_age,
                    "patient_gender": patient_gender
                },
                "next_tasks": [
                    "Confirm BP with repeat measurement",
                    "Review medication adherence",
                    "Provide lifestyle modification counseling",
                    "Schedule follow-up"
                ],
                "reasoning_trace": [
                    f"✅ Parsed {len(resources)} FHIR resources",
                    f"✅ BP: {bp_systolic}/{bp_diastolic} mmHg",
                    f"✅ Classified as {bp_category}",
                    f"✅ Found {len(medications)} medications"
                ],
                "clinical_evidence": [
                    {
                        "guideline": "ACC/AHA 2017",
                        "citation": "Hypertension clinical practice guidelines"
                    }
                ]
            },
            "used_fhir_resources": [
                {"type": r.get("resourceType"), "id": r.get("id")}
                for r in resources if r.get("id")
            ]
        })
    
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "failed",
                "error": str(e),
                "message": "An error occurred while processing the request"
            }
        )

# ============================================
# FALLBACK FOR ANY OTHER ROUTES
# ============================================
@app.get("/{path:path}")
async def catch_all(path: str):
    return JSONResponse(
        status_code=200,
        content={
            "message": f"Healthcare A2A Agent is running",
            "note": "Use POST /task for clinical analysis",
            "available_endpoints": ["/", "/health", "/task", "/.well-known/ai-agent.json"]
        }
    )

# ============================================
# RUN THE APP
# ============================================
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
