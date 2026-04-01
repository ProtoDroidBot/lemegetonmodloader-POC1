# Decompiled with PyLingual (https://pylingual.io)
# Internal filename: 'C:\\BuildAgent\\work\\6ec9bf56460fca58\\packages\\frontier\\industry\\common\\utility.py'
# Bytecode version: 3.12.0rc2 (3531)
# Source timestamp: 2026-03-17 10:26:08 UTC (1773743168)

import math
import typing as t
import evetypes
from frontier.industry.common import data_loader
from frontier.industry.common.model import FacilityBlueprint, IndustryFacility, ItemSlot
from inventorycommon.util import GetMaxQuantityForItem, GetPackagedVolume
def is_industry_facility(type_id):
    return type_id in data_loader.get_facilities()
def does_facility_have_output(facility_type_id, type_ids=None, group_ids=None, category_ids=None):
    if not is_industry_facility(facility_type_id):
        return False
    else:
        facility_data = data_loader.get_facility_data(facility_type_id)
        def filter_func(type_id):
            if type_ids is not None and type_id in type_ids:
                return True
            else:
                if group_ids is not None and evetypes.GetGroupID(type_id) in group_ids:
                    return True
                else:
                    if category_ids is not None and evetypes.GetCategoryID(type_id) in category_ids:
                            return True
        for blueprint_info in facility_data.blueprints:
            blueprint_data = data_loader.get_blueprint_data(blueprint_info.blueprintID)
            if any((filter_func(item.typeID) for item in blueprint_data.outputs)):
                return True
        return False
def get_facility(type_id) -> IndustryFacility:
    return _construct_facility(type_id)
def get_all_facilities() -> t.Dict[int, IndustryFacility]:
    return {type_id: _construct_facility(type_id) for type_id in data_loader.get_facilities()}
def get_blueprint_for_facility(facility_type_id, blueprint_id) -> t.Optional[FacilityBlueprint]:
    try:
        facility_data = data_loader.get_facility_data(facility_type_id)
    except KeyError:
        return None
    facility_blueprint_info = next((b for b in facility_data.blueprints if b.blueprintID == blueprint_id), None)
    if facility_blueprint_info is None:
        return
    else:
        blueprint_data = data_loader.get_blueprint_data(blueprint_id)
        return FacilityBlueprint(blueprint_id=blueprint_id, run_time=blueprint_data.runTime, inputs=_construct_item_slots(blueprint_data.inputs, facility_blueprint_info.maxInputRuns), outputs=_construct_item_slots(blueprint_data.outputs, facility_blueprint_info.maxOutputRuns))
def get_valid_items_to_move(items, capacity, filter_func=None):
    if not capacity or not items:
        return ({}, 0)
    else:
        valid_items = {}
        remaining_capacity = capacity
        for type_id, quantity in items.items():
            if filter_func is not None and (not filter_func(type_id)):
                    continue
            volume = GetPackagedVolume(type_id)
            max_quantity = GetMaxQuantityForItem(volume, remaining_capacity)
            if quantity is None:
                used_quantity = max_quantity
            else:
                used_quantity = min(quantity, max_quantity)
            if used_quantity == 0:
                continue
            else:
                valid_items[type_id] = used_quantity
                remaining_capacity -= volume * used_quantity
        return (valid_items, remaining_capacity)
def _construct_facility(facility_type_id) -> IndustryFacility:
    data = data_loader.get_facility_data(facility_type_id)
    return IndustryFacility(type_id=facility_type_id, blueprints=_construct_blueprints_for_facility(data))
def _construct_blueprints_for_facility(facility_data) -> t.Dict[int, FacilityBlueprint]:
    result = {}
    for blueprint in facility_data.blueprints:
        blueprint_id = blueprint.blueprintID
        blueprint_data = data_loader.get_blueprint_data(blueprint_id)
        if blueprint_data:
            result[blueprint_id] = FacilityBlueprint(blueprint_id=blueprint_id, run_time=blueprint_data.runTime, inputs=_construct_item_slots(blueprint_data.inputs, blueprint.maxInputRuns), outputs=_construct_item_slots(blueprint_data.outputs, blueprint.maxOutputRuns))
    return result
def _construct_item_slots(items_data, max_runs) -> t.Dict[int, ItemSlot]:
    return {item.typeID: ItemSlot(item_id=0, type_id=item.typeID, quantity_per_run=item.quantity, max_storable_quantity=item.quantity * max_runs) for item in items_data}
def get_blueprint_output_type_ids(blueprint_id):
    from frontier.industry.common.data_loader import get_blueprint_data
    try:
        blueprint_data = get_blueprint_data(blueprint_id)
    except:
        return set()
    return set([output.typeID for output in blueprint_data.outputs])