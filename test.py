# test endpoint for gemini
@analysis_router.get("/test-gemini/")
async def test_gemini():
    headers = {
        "Content-Type": "application/json",
    }
    data = {
        # you are a helpful assistant to check documents for errors about formatting and content. you need to chat user about the document and the errors.
        "contents": [
            {
                "parts": [
                    {
                        "text": "You are a helpful assistant to check documents for errors about formatting and content. you need to chat user about the document and the errors."
                    }
                ]
            }
        ]
    }
    url = f"{BASE_URL}?key={API_KEY}"

    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Gemini API Error: {response.text}",
            )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error sending data to Gemini: {str(e)}"
        )
