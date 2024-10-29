from bson import json_util
import json

from mongoengine import Document, StringField, FloatField, IntField, ListField, ReferenceField, GeoPointField


class Zone(Document):
    zone_id = IntField(primary_key=True)
    name = StringField(required=True)
    location = GeoPointField(required=True)
    cell_side = FloatField(required=True)
    devices = ListField(ReferenceField('Device'))
    barriers = ListField(ReferenceField('Barrier'))

    def to_dict(self):
        data = self.to_mongo().to_dict()
        return json.loads(json_util.dumps(data))

    @classmethod
    def create_zone(cls, zone_id, name, location, cell_side):
        zone = cls(zone_id=zone_id, name=name, location=location, cell_side=cell_side)
        zone.save()
        return zone

    @classmethod
    def get_zones(cls):
        return cls.objects.all()

    def get_barriers_in_zone(self):
        return self.barriers

    def get_devices_in_zone(self):
        return self.devices
