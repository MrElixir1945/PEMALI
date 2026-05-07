import asyncio
import httpx

async def main():
    async with httpx.AsyncClient() as client:
        r = await client.post("http://localhost:8000/api/trigger", json={
            "prompt": "audit lokasi badung apakah disana vegetasi masih bagus"
        })
        print("Trigger Status:", r.status_code)

asyncio.run(main())
