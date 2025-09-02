#!/usr/bin/env python3
"""Debug script to test LLM response format"""

import json

import aiohttp

API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "meta-llama/llama-3.1-8b-instruct:free"


async def test_llm_response():
    """Test LLM response format with simple query"""
    prompt = """You are an expert at matching German energy company names. Please analyze whether these companies are the same:

Target company: "Netzgesellschaft Bitterfeld_Wolfen mbH"

BDEW companies to check:
- "Netzgesellschaft Bitterfeld-Wolfen mbH"

Respond with valid JSON in this exact format:
{
  "analysis": "Brief explanation of matching logic",
  "matches": [
    {
      "bdew_company": "exact name",
      "confidence": 85
    }
  ]
}"""

    headers = {
        "Authorization": "Bearer YOUR_API_KEY_HERE",  # Replace with actual key
        "Content-Type": "application/json",
    }

    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 500,
    }

    # HTTP status constants
    HTTP_OK = 200

    try:
        async with (
            aiohttp.ClientSession() as session,
            session.post(API_URL, headers=headers, json=payload) as response,
        ):
            if response.status == HTTP_OK:
                data = await response.json()
                content = data["choices"][0]["message"]["content"].strip()

                print("=== RAW LLM RESPONSE ===")
                print(repr(content))
                print("\n=== FORMATTED RESPONSE ===")
                print(content)

                # Try to parse as JSON
                try:
                    parsed = json.loads(content)
                    print("\n=== PARSED JSON ===")
                    print(json.dumps(parsed, indent=2))
                except json.JSONDecodeError as e:
                    print("\n=== JSON ERROR ===")
                    print(f"Error: {e}")

                    # Try to extract JSON manually
                    start_idx = content.find("{")
                    end_idx = content.rfind("}")

                    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                        extracted = content[start_idx : end_idx + 1]
                        print("\n=== EXTRACTED JSON ===")
                        print(repr(extracted))
                        try:
                            parsed = json.loads(extracted)
                            print("✅ Successfully parsed extracted JSON")
                            print(json.dumps(parsed, indent=2))
                        except json.JSONDecodeError as e2:
                            print(f"❌ Extracted JSON also failed: {e2}")

            else:
                print(f"API Error: {response.status}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    print("This is a debug script to test LLM response format.")
    print("Please replace 'YOUR_API_KEY_HERE' with your actual OpenRouter API key.")
    print("Then run: python debug_llm_response.py")
