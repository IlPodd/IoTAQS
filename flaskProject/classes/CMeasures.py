from mongoengine import EmbeddedDocument, DateTimeField, BooleanField
from mongoengine import FloatField, StringField, GeoPointField
from mongoengine import EmbeddedDocumentField, ListField
from mongoengine import Document, DictField
from bson import json_util
import json

class Measures(EmbeddedDocument):
    id = StringField(required=True)  # Assuming id is required
    date = DateTimeField(required=True)
    temperature = FloatField(required=True)
    humidity = FloatField(required=True)
    location = GeoPointField(required=True)  # Correctly define GeoPointField for location
    air_quality_index = FloatField(required=True)



class Sensor(EmbeddedDocument):
    sensor_id = StringField(required=True)
    enabled = BooleanField(required=True)
    measures = ListField(EmbeddedDocumentField(Measures))

    meta = {'collection': 'sensors'}


class Device(Document):
    dt_id = StringField(required=True)
    description = StringField(required=True)
    sensors = DictField(EmbeddedDocumentField(Sensor))

    meta = {'collection': 'devices'}

    def to_dict(self):
        data = self.to_mongo().to_dict()
        return json.loads(json_util.dumps(data))

    @classmethod
    def create_device(cls, dt_id, description, sensors):
        device = cls(dt_id=dt_id, description=description, sensors=sensors)
        device.save()
        return device

    def toggle_sensors(self, sensors):
        for sensor in sensors:
            if sensor in self.sensors:
                self.sensors[sensor].enabled = not self.sensors[sensor].enabled
                self.save()
            else:
                self.sensors[sensor] = Sensor()
                self.save()

    def add_measures(self, sensor_id, measure):
        if sensor_id in self.sensors and self.sensors[sensor_id].enabled:
            self.sensors[sensor_id].measures.append(measure)
            self.save()