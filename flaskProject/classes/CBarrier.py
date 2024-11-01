# CBarrier.py

from bson import ObjectId
from datetime import datetime

class Barrier:
    def __init__(self, barrier_id=None, location=None, status=None, last_updated=None, zone=None):
        self.barrier_id = barrier_id
        self.location = location
        self.status = status
        self.last_updated = last_updated
        self.zone = zone

    def to_dict(self):
        return {
            'barrier_id': self.barrier_id,
            'location': self.location,
            'status': self.status,
            'last_updated': self.last_updated,
            'zone': self.zone
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            barrier_id=data.get('barrier_id'),
            location=data.get('location'),
            status=data.get('status'),
            last_updated=data.get('last_updated'),
            zone=data.get('zone')
        )

    def save(self, db):
        barriers_collection = db['barriers']
        barriers_collection.update_one(
            {'barrier_id': self.barrier_id},
            {'$set': self.to_dict()},
            upsert=True
        )

    @classmethod
    def get_by_barrier_id(cls, db, barrier_id):
        barriers_collection = db['barriers']
        data = barriers_collection.find_one({'barrier_id': barrier_id})
        if data:
            return cls.from_dict(data)
        else:
            return None

    def update_status(self, db, status):
        self.status = status
        self.last_updated = datetime.utcnow().isoformat()
        self.save(db)

    @classmethod
    def get_all(cls, db):
        barriers_collection = db['barriers']
        barriers_cursor = barriers_collection.find()
        barriers = []
        for data in barriers_cursor:
            barrier = cls.from_dict(data)
            barriers.append(barrier)
        return barriers
