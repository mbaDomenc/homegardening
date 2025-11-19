# backend/controllers/sensor_controller.py
from fastapi import HTTPException
from database import db
from models.sensorModel import SensorReading, SensorReadingResponse
from datetime import datetime, timedelta
from typing import List, Optional


async def save_sensor_data(reading: SensorReading) -> SensorReadingResponse:
    """Salva una lettura del sensore nel database MongoDB"""
    try:
        reading_dict = reading.dict()
        result = await db["sensor_readings"].insert_one(reading_dict)

        return SensorReadingResponse(
            status="success",
            id=str(result.inserted_id),
            message=f"Sensor reading from {reading.sensor_id} saved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving sensor data: {str(e)}")


async def get_sensor_history(
        sensor_id: Optional[str] = None,
        sensor_type: Optional[str] = None,
        location: Optional[str] = None,
        hours: int = 24,
        limit: int = 1000
) -> List[dict]:
    """Recupera lo storico delle letture con filtri opzionali"""
    try:
        query = {}

        if sensor_id:
            query["sensor_id"] = sensor_id
        if sensor_type:
            query["sensor_type"] = sensor_type
        if location:
            query["location"] = location

        time_threshold = datetime.utcnow() - timedelta(hours=hours)
        query["timestamp"] = {"$gte": time_threshold}

        cursor = db["sensor_readings"].find(query).sort("timestamp", -1).limit(limit)
        readings = await cursor.to_list(length=limit)

        for reading in readings:
            reading["_id"] = str(reading["_id"])

        return readings

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving sensor history: {str(e)}")


async def get_latest_readings(location: Optional[str] = None) -> dict:
    """Recupera le ultime letture di ogni tipo di sensore"""
    try:
        query = {}
        if location:
            query["location"] = location

        sensor_types = await db["sensor_readings"].distinct("sensor_type", query)
        latest_readings = {}

        for sensor_type in sensor_types:
            type_query = {**query, "sensor_type": sensor_type}
            reading = await db["sensor_readings"].find_one(
                type_query,
                sort=[("timestamp", -1)]
            )

            if reading:
                reading["_id"] = str(reading["_id"])
                latest_readings[sensor_type] = reading

        return latest_readings

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving latest readings: {str(e)}")


async def get_sensor_stats(sensor_id: str, hours: int = 24) -> dict:
    """Calcola statistiche per un sensore specifico"""
    try:
        time_threshold = datetime.utcnow() - timedelta(hours=hours)

        pipeline = [
            {
                "$match": {
                    "sensor_id": sensor_id,
                    "timestamp": {"$gte": time_threshold}
                }
            },
            {
                "$group": {
                    "_id": "$sensor_id",
                    "avg_value": {"$avg": "$value"},
                    "min_value": {"$min": "$value"},
                    "max_value": {"$max": "$value"},
                    "count": {"$sum": 1},
                    "unit": {"$first": "$unit"}
                }
            }
        ]

        result = await db["sensor_readings"].aggregate(pipeline).to_list(length=1)

        if not result:
            raise HTTPException(status_code=404, detail=f"No data found for sensor {sensor_id}")

        return result[0]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating stats: {str(e)}")
