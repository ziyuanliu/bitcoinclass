"""
Serialization component for named tuples
http://www.effectivepython.com/2015/02/02/register-class-existence-with-metaclasses/
"""

import binascii
import json

from typing import NamedTuple, get_type_hints, Iterable, Mapping, Union


namedtuple_cls_registry = {}


def register_namedtuple(cls):
    """
    Here's a registry hook, we can add the class name to the registry
    and set the dynamic methods
    """

    namedtuple_cls_registry[cls.__name__] = cls
    setattr(cls, 'deserialize', classmethod(deserialize))
    setattr(cls, 'serialize', serialize)
    return cls


class RegistryMeta(type):
    def __new__(cls, clsname, bases, attrs):
        newclass = super().__new__(cls, clsname, bases, attrs)
        namedtuple_cls_registry[newclass.__name__] = newclass()
        print(newclass._fields)
        return newclass


def serialize(self) -> str:
    """
    NameTuples do not have a method to nest serialize
    """
    def as_primitive(obj):
        if hasattr(obj, '_asdict'):
            obj = {**obj._asdict(), '_type': type(obj).__name__}
        elif isinstance(obj, (list, tuple)):
            return [as_primitive(elem) for elem in obj]
        elif isinstance(obj, bytes):
            return binascii.hexlify(obj).decode()
        elif not isinstance(obj, (dict, bytes, str, int, type(None))):
            raise ValueError(f'{obj} cannot be serialized')

        if isinstance(obj, Mapping):
            for key, value in obj.items():
                obj[key] = as_primitive(value)

        return obj

    return json.dumps(as_primitive(self), sort_keys=True, separators=(',', ':'))


def deserialize(cls, json_str: str) -> NamedTuple:
    """
    This function will deserialize json_str into their NamedTuple instances
    We will need to import all of the NamedTuple classes here
    """

    def str_to_objs(obj):
        if isinstance(obj, list):
            return [str_to_objs(elem) for elem in obj]
        elif not isinstance(obj, Mapping):
            return obj

        _type = namedtuple_cls_registry[obj.pop('_type', None)]
        bytes_key = {
            key for key, value in get_type_hints(_type).items() if value == bytes
        }

        for key, value in obj.items():
            obj[key] = str_to_objs(value)

            if key in bytes_key:
                obj[key] = binascii.unhexlify(obj[key]) if obj[key] else obj[key]

        return _type(**obj)

    return str_to_objs(json.loads(json_str))
