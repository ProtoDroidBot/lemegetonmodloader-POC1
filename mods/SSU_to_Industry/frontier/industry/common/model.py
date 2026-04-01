# Decompiled with PyLingual (https://pylingual.io)
# Internal filename: 'C:\\BuildAgent\\work\\6ec9bf56460fca58\\packages\\frontier\\industry\\common\\model.py'
# Bytecode version: 3.12.0rc2 (3531)
# Source timestamp: 2026-03-17 10:26:08 UTC (1773743168)

from __future__ import annotations
import hashlib
import json
import typing as t
from dataclasses import dataclass, field
@dataclass(frozen=True)
class IndustryFacility:
    type_id: int
    blueprints: t.Dict[int, FacilityBlueprint]
@dataclass(frozen=True)
class FacilityBlueprint:
    blueprint_id: int
    run_time: int
    inputs: t.Dict[int, ItemSlot]
    outputs: t.Dict[int, ItemSlot]
    content_hash: str = field(init=False)
    @classmethod
    def from_dict(cls, d):
        print(d['inputs'].values())
        return cls(blueprint_id=d['blueprint_id'], run_time=d['run_time'], inputs={item['type_id']: ItemSlot(0, **item) for item in d['inputs'].values()}, outputs={item['type_id']: ItemSlot(0, **item) for item in d['outputs'].values()})
    def to_dict(self, include_hash=True) -> dict:
        result = {'blueprint_id': self.blueprint_id, 'run_time': self.run_time, 'inputs': {type_id: self.inputs[type_id].to_dict() for type_id in sorted(self.inputs)}, 'outputs': {type_id: self.outputs[type_id].to_dict() for type_id in sorted(self.outputs)}}
        if include_hash:
            result['content_hash'] = self.content_hash
        return result
    def __eq__(self, other):
        return isinstance(other, FacilityBlueprint) and self.content_hash == other.content_hash
    def __hash__(self) -> int:
        return int(self.content_hash, 16)
    def __post_init__(self):
        data = self.to_dict(include_hash=False)
        s = json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        content_hash_hex = hashlib.sha256(s.encode('utf-8')).hexdigest()
        object.__setattr__(self, 'content_hash', content_hash_hex)
@dataclass(frozen=True)
class ItemSlot:
    item_id: int
    type_id: int
    quantity_per_run: int
    max_storable_quantity: int
    def to_dict(self) -> dict:
        return {'item_id': self.item_id, 'type_id': self.type_id, 'quantity_per_run': self.quantity_per_run, 'max_storable_quantity': self.max_storable_quantity}
class ProductionState:
    UNSPECIFIED = 'UNSPECIFIED'
    IDLE = 'IDLE'
    RUNNING = 'RUNNING'
    DISCONTINUING = 'DISCONTINUING'
    STOPPED = 'STOPPED'
@dataclass(frozen=True)
class ProductionRun:
    start_time: t.Optional[int] = None
    end_time: t.Optional[int] = None
    state: t.Optional[ProductionState] = ProductionState.IDLE
    def to_dict(self) -> dict:
        return {'start_time': self.start_time, 'end_time': self.end_time, 'state': self.state}