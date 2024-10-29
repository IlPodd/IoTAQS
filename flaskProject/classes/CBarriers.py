from mongoengine import DateTimeField, BooleanField
from mongoengine import StringField, GeoPointField
from mongoengine import Document

from datetime import datetime


class Barrier(Document):
    barrier_id = StringField(required=True, unique=True)
    location = GeoPointField(required=True)
    status = BooleanField(required=True)
    last_updated = DateTimeField(required=False, default=datetime)
