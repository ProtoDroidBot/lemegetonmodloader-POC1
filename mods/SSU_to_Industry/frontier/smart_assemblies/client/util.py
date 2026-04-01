# Decompiled with PyLingual (https://pylingual.io)
# Internal filename: 'C:\\BuildAgent\\work\\6ec9bf56460fca58\\packages\\frontier\\smart_assemblies\\client\\util.py'
# Bytecode version: 3.12.0rc2 (3531)
# Source timestamp: 2026-03-17 10:26:08 UTC (1773743168)

from frontier.smart_assemblies.common.utils import get_smart_assembly_access_range
from menucheckers import CelestialChecker
from menucheckers.sessionChecker import SessionChecker
from inventorycommon import const as inv_const
from spacecomponents.common.componentConst import CARGO_BAY
from spacecomponents.common.data import get_space_component_for_type
from spacecomponents.common.helper import HasSmartHangarComponent, IsActiveComponent, HasSmartStorageUnitComponent
from eve.client.script.environment import invControllers
import builtins
from frontier.smart_assemblies.client.storage.controller import StorageController
from frontier.smart_assemblies.client.storage.smart_storage_inventory import SmartStorageUnitInventory
def get_interactable_assemblies(filter=None):
    ballpark = sm.GetService('michelle').GetBallpark()
    if ballpark is None:
        return {}
    else:
        session_checker = SessionChecker(session, sm)
        def validate(cr_data):
            if filter and (not filter(cr_data)):
                return False
            else:
                return is_assembly_interactable(cr_data, session_checker, ballpark)
        return ballpark.GetCrDataByFilter(filterFunction=validate)
def is_assembly_interactable(cr_data, session_checker=None, ballpark=None):
    if session_checker is None:
        session_checker = SessionChecker(session, sm)
    if ballpark is None:
        ballpark = sm.GetService('michelle').GetBallpark()
        if ballpark is None:
            return False
    if cr_data.itemID is None or session.shipid is None:
        return False
    else:
        checker = CelestialChecker(cr_data, cfg, session_checker)
        if not checker.OfferOpenSmartAssembly():
            return False
        else:
            access_range = get_smart_assembly_access_range(cr_data.typeID)
            return ballpark.DistanceBetween(session.shipid, cr_data.itemID) <= access_range
def get_available_inventories(exclude_item_ids=None, include_ship_hangars=False):
    session = builtins.session
    if exclude_item_ids is None:
        exclude_item_ids = []
    sm = getattr(builtins, 'sm', None)
    bp = sm.GetService('michelle').GetBallpark()
    result = []
    result2 = []
    if bp is None:
        return []
    else:
        inventories = []
        for cr_data in bp.GetCrDataByFilter().values():
            if cr_data.categoryID!= inv_const.categoryDeployable:
                continue
            else:
                if cr_data.itemID in exclude_item_ids:
                    continue
                else:
                    if cr_data.ownerID!= session.charid:
                        continue
                    else:
                        if not IsActiveComponent(bp.componentRegistry, cr_data.typeID, cr_data.ballID):
                            continue
                        else:
                            try:
                                distance = bp.DistanceBetween(session.shipid, cr_data.ballID)
                                if distance > 5000:
                                    continue
                            except:
                                pass
                            else:
                                cargoComponent = get_space_component_for_type(cr_data.typeID, CARGO_BAY)
                                if cargoComponent and (not cargoComponent.hidden):
                                    inventories.append((inv_const.spaceComponentInventory, cr_data.itemID))
                                if include_ship_hangars and HasSmartHangarComponent(cr_data.typeID):
                                    inventories.append((inv_const.smartHangarInventory, cr_data.itemID))
                                if HasSmartStorageUnitComponent(cr_data.typeID):
                                    inventories.append(('SmartStorageUnitInventory', cr_data.itemID, cr_data.typeID))
                                    result2 = [SmartStorageUnitInventory(StorageController(item_id, type_id, cr_data.ownerID, 'AssemblyController'), item_id, type_id) for class_name, item_id, type_id, *_ in inventories if class_name == 'SmartStorageUnitInventory']
                                #Formatted exception info: TypeError: StorageController.__init__() missing 4 required positional arguments: 'structure_item_id', 'structure_type_id', 'assembly_owner_id', and 'assembly_controller'
            if result2 != None:
                result = [getattr(invControllers, class_name)(itemID=item_id) for class_name, item_id, *_ in inventories if class_name != 'SmartStorageUnitInventory' ]
                result.extend(result2)
            else:
                result = [getattr(invControllers, class_name)(itemID=item_id) for class_name, item_id, *_ in inventories]
        result.sort(key=lambda inventory: inventory.GetName())
        result.insert(0, invControllers.ShipCargo(session.shipid))
    print(f'Available Inventories: {result}')
    return result