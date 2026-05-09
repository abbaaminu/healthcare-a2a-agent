import os
from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, List
from datetime import datetime

app = FastAPI(title="Healthcare A2A Agent")

# Enable CORS for Prompt Opinion
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "Healthcare A2A Agent",
        "version": "1.0",
        "ready": True
    }

@app.get("/.well-known/ai-agent.json")
async def agent_card():
    return {
        "name": "Healthcare A2A Risk Analyzer",
        "description": "Clinical agent analyzing blood pressure, medications, and cardiovascular risk using FHIR data",
        "version": "1.0.0",
        "capabilities": [
            "blood_pressure_classification",
            "medication_reconciliation",
            "risk_assessment",
            "clinical_guidelines"
        ],
        "endpoint": "/task",
        "health_endpoint": "/health"
    }

@app.post("/task")
async def handle_task(payload: Dict[str, Any] = Body(...)):
    try:
        resources = payload.get("context", {}).get("fhir_resources", [])
        
        # Extract data from FHIR
        bp_systolic = 0
        bp_diastolic = 0
        medications = []
        patient_age = None
        
        for resource in resources:
            resource_type = resource.get("resourceType")
            
            if resource_type == "Patient":
                birth_date = resource.get("birthDate")
                if birth_date:
                    try:
                        birth_year = int(birth_date.split("-")[0])
                        patient_age = datetime.now().year - birth_year
                    except:
                        pass
            
            elif resource_type == "Observation":
                code_text = str(resource.get("code", {}).get("text", "")).lower()
                if "blood pressure" in code_text:
                    components = resource.get("component", [])
                    for component in components:
                        comp_text = str(component.get("code", {}).get("text", "")).lower()
                        value = component.get("valueQuantity", {}).get("value", 0)
                        if "systolic" in comp_text:
                            bp_systolic = value
                        elif "diastolic" in comp_text:
                            bp_diastolic = value
            
            elif resource_type == "MedicationRequest":
                med_name = resource.get("medicationCodeableConcept", {}).get("text", "")
                if med_name:
                    medications.append(med_name)
        
        # Clinical logic
        if bp_systolic >= 140 or bp_diastolic >= 90:
            bp_category = "Stage 2 Hypertension"
            recommendation = "Immediate clinical follow-up required. Consider initiating or adjusting antihypertensive medication."
            urgency = "HIGH"
        elif bp_systolic >= 130 or bp_diastolic >= 80:
            bp_category = "Stage 1 Hypertension"
            recommendation = "Lifestyle modifications recommended. Reassess in 3-6 months."
            urgency = "MEDIUM"
        else:
            bp_category = "Normal"
            recommendation = "Continue routine monitoring annually."
            urgency = "LOW"
        
        # Build response
        response_text = f"""🏥 CLINICAL ASSESSMENT

📊 Blood Pressure: {bp_systolic}/{bp_diastolic} mmHg
📋 Classification: {bp_category}
⚠️ Urgency: {urgency}

💊 Medications: {', '.join(medications) if medications else 'None documented'}

📝 Recommendation: {recommendation}
"""
        
        if patient_age:
            response_text += f"\n👤 Patient Age: {patient_age} years\n"
        
        return {
            "status": "completed",
            "output": {
                "text": response_text,
                "tool_outputs": {
                    "blood_pressure": {
                        "systolic": bp_systolic,
                        "diastolic": bp_diastolic,
                        "category": bp_category,
                        "urgency": urgency
                    },
                    "medications": medications,
                    "patient_age": patient_age
                },
                "next_tasks": [
                    "Confirm BP reading with repeat measurement",
                    "Review medication adherence",
                    "Schedule follow-up appointment" if bp_category != "Normal" else "Continue annual monitoring"
                ],
                "reasoning_trace": [
                    f"Parsed {len(resources)} FHIR resources",
                    f"BP classified as {bp_category}",
                    f"Found {len(medications)} medications"
                ]
            }
        }
    
    except Exception as e:
        return {
            "status": "failed",
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)