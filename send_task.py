
import httpx
import asyncio
import json
import sys

async def main():
    payload = {
        "persona": "shopper",
        "product": "Apple 2025 MacBook Air (13-inch, Apple M4 chip with 10-core CPU and 10-core GPU, 24GB Unified Memory, 512GB) - Silver",
        "url": "https://www.amazon.in/Apple-MacBook-13-inch-10-core-Unified/dp/B0DZDDTZ74/ref=sr_1_1_sspa?crid=XDS9B8YN218&dib=eyJ2IjoiMSJ9.rPvZxx0DnMagOliaoaBh3FsZvFYCGiJNsORn9WWIzsemZcHeNtlgRYPJo66rli-jelp4c5GZzkUTNTCR7RLN3EwWvRoF7WKWPzJVFENHaJyDXyUmPGcJD1C5MHs4pjrGQ3yjp906QKnj6XzWqXA0hY9odmgTVBVuYysd2GHu-RZXQmBZfCj1ly_eV8110_x2HPptntGsyH377MfLPsvuTTsv_WF0y_LU8QEUNSsFTF0.gZYio0tbrKDyqXimyTQXg8GxpocXV_GgYQmdyCSLLMo%26dib_tag%3Dse%26keywords%3Dmacbook%2Bair%2Bm4%2B512gb%26qid%3D1770097081%26sprefix%3Dmacbook%2Bair%2Bm4%2B512gb%252Caps%252C397%26sr%3D8-1-spons%26aref%3DkOApvybUT1%26sp_csd%3Dd2lkZ2V0TmFtZT1zcF9hdGY%26psc%3D1&aref=kOApvybUT1&sp_cr=ZAZ"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post('http://localhost:8000/task', json=payload, headers={'Content-Type': 'application/json'})
        response.raise_for_status()
        print(f"Task sent successfully: {response.json()}")

if __name__ == "__main__":
    asyncio.run(main())
