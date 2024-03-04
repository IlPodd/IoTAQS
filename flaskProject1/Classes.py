from mongoengine import Document, EmbeddedDocument, StringField
from mongoengine import (FloatField, StringField, IntField, ListField,
                         EmbeddedDocumentListField, DateTimeField, EmbeddedDocumentField,
                         GeoPointField, BooleanField)
from datetime import datetime, timedelta
from bson import json_util
import json


class User(EmbeddedDocument):
    username = StringField(required=True)
    password = StringField(required=True)
    role = StringField(required=True)


class DataIQA(EmbeddedDocument):
    date = DateTimeField(required=True)
    humidity_level = FloatField(required=True)
    temperature = FloatField(required=True)
    position = GeoPointField(required=True)


class Sensors(EmbeddedDocument):
    name = StringField(required=True)
    id = StringField(required=True)
    type = StringField(required=True)
    position = GeoPointField(required=True)


class DataZone(EmbeddedDocument):
    date = DateTimeField(required=True)
    value = FloatField(required=True)
    type = StringField(required=True)


class Barrier(EmbeddedDocument):
    id = StringField(required=True)
    position = GeoPointField(required=True)
    status = BooleanField(required=True)
    name = StringField(required=True)


class Zone(Document):
    z_id = IntField(required=True, unique=True)
    sensors = ListField(EmbeddedDocumentField(Sensors))
    data_zone = ListField(EmbeddedDocumentField(DataZone))
    barrier = EmbeddedDocumentField(Barrier)

    def to_dict(self):
        data = self.to_mongo().to_dict()
        return json.loads(json_util.dumps(data))

    def add_data(self, date, value, type):
        new_data = DataZone(date=date, value=value, type=type)
        self.data_zone.append(new_data)
        self.save()

    def add_sensors(self, name, id):
        new_sensor = Sensors(name=name, id=id)
        self.sensors.append(new_sensor)
        self.save()

    def get_sensors(self, id):
        for sensors in self.sensors:
            if sensors.id == id:
                return sensors
        return None

    def get_data(self, type, start_date=None, end_date=None):
        if start_date is None:
            start_date = datetime.min
        if end_date is None:
            end_date = datetime.max
        return [data for data in self.data_zone if data.type ==
                type and start_date <= data.date <= end_date]

    @classmethod
    def get_zone_from_id(cls, z_id):
        try:
            return cls.objects.get(id=z_id)
        except:
            return None

    @classmethod
    def add_zone(cls, name, id):
        new_sensor = Sensors(name=name, id=id)
        new_zone = cls.objects.get(id=id, sensors=new_sensor)
        new_zone.save()
        return new_zone

    def is_sensor_in_zone(self, s):
        name = s.name
        id = s.name
        type = s.type
        for sensor in self.sensors:
            if sensor.name == name and sensor.id == id and sensor.type == type:
                return True
            return False

    def get_temperature_data(self):
        return self.get_data(type='temperature')

    def get_humidity_data(self):
        return self.get_data(type='humidity')

    def get_gps_data(self):
        return self.get_data(type='gpsdata')

    def update_id(self, sensor, new_id):
        for s in self.sensors:
            if s == sensor:
                s.id = new_id
        self.save()
