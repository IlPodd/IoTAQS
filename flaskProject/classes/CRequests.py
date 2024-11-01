from bson.binary import Binary, UUID_SUBTYPE
import uuid

class Request:
    def __init__(self, _id=None, id_request=None, barrier_id=None, id=None, request_id=None, type=None, data=None, time=None, status=None, outcome=None):
        self._id = _id  # ObjectId
        self.id_request = id_request  # Binary UUID
        self.barrier_id = barrier_id
        self.id = id  # 'Server' or other identifier
        self.request_id = request_id  # String representation of UUID
        self.type = type
        self.data = data
        self.time = time  # datetime
        self.status = status
        self.outcome = outcome

    @classmethod
    def from_dict(cls, data):
        id_request_binary = data.get('id_request')
        if isinstance(id_request_binary, Binary):
            id_request_str = str(uuid.UUID(bytes=id_request_binary))
        else:
            id_request_str = data.get('id_request')

        return cls(
            _id=data.get('_id'),
            id_request=id_request_binary,
            barrier_id=data.get('barrier_id'),
            id=data.get('id'),
            request_id=id_request_str,
            type=data.get('type'),
            data=data.get('data'),
            time=data.get('time'),
            status=data.get('status'),
            outcome=data.get('outcome')
        )

    def to_dict(self):
        return {
            'id_request': self.id_request,
            'barrier_id': self.barrier_id,
            'id': self.id,
            'type': self.type,
            'data': self.data,
            'time': self.time,
            'status': self.status,
            'outcome': self.outcome
        }

    def save(self, db):
        requests_collection = db['requests']
        if self._id:
            # Update existing document
            requests_collection.update_one({'_id': self._id}, {'$set': self.to_dict()})
        else:
            # Insert new document
            result = requests_collection.insert_one(self.to_dict())
            self._id = result.inserted_id

    @classmethod
    def get_by_id_request(cls, db, id_request_str):
        requests_collection = db['requests']
        # Convert id_request_str to Binary UUID
        try:
            id_request_binary = Binary(uuid.UUID(id_request_str).bytes, subtype=UUID_SUBTYPE)
        except ValueError:
            print(f"Invalid UUID string: {id_request_str}")
            return None
        data = requests_collection.find_one({'id_request': id_request_binary})
        if data:
            return cls.from_dict(data)
        return None

    def update_status(self, db, status, outcome):
        self.status = status
        self.outcome = outcome
        self.save(db)
