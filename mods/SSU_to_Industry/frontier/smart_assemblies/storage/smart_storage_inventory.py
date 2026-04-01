# Decompiled with PyLingual (https://pylingual.io)
# Internal filename: 'C:\\BuildAgent\\work\\6ec9bf56460fca58\\packages\\frontier\\smart_assemblies\\client\\storage\\smart_storage_inventory.py'
# Bytecode version: 3.12.0rc2 (3531)
# Source timestamp: 2026-03-17 10:26:08 UTC (1773743168)

import uuid
import blue
import appConst
import evetypes
import localization
import operator
import telemetry
import uthread
import utillib
from carbonui import uiconst
from carbonui.uicore import uicore
from eve.client.script.environment.invControllers import BaseCelestialContainer, ShipCargo
from eve.client.script.ui.shared.item import InvItem
from eve.client.script.ui.util import uix
from eve.common.lib import appConst as const
from eveexceptions import UserError
from eveservices.menu import GetMenuService
import typing as t
from inventorycommon.util import GetItemVolume
from utillib import KeyVal
if t.TYPE_CHECKING:
    from frontier.smart_assemblies.client.storage.controller import StorageController
class SmartStorageUnitInventory(BaseCelestialContainer):
    # ***<module>.SmartStorageUnitInventory: Failure: Different bytecode
    __guid__ = 'invCtrl.BlockchainStorageInventory'
    iconName = 'res:/ui/Texture/WindowIcons/itemHangar.png'
    locationFlag = const.flagSmartStorageUnit
    hasCapacity = True
    def __init__(self, ss_controller: StorageController, itemID=None, typeID=None):
        super(SmartStorageUnitInventory, self).__init__(itemID=itemID, typeID=typeID)
        self.smart_storage_controller = ss_controller
    @telemetry.ZONE_METHOD
    def _GetItems(self):
        _items = self.smart_storage_controller.items
        items = []
        for item in _items:
            type_id = item.type_id
            quantity = item.quantity
            is_singleton = item.is_singleton
            items.append(StorageInventoryItem(type_id, quantity, is_singleton, self.smart_storage_controller.assembly_owner_id, self.locationFlag, self.smart_storage_controller.assembly_id, self.smart_storage_controller.is_owner))
        return items
    def GetItem(self, itemID):
        return
    def GetItems(self):
        _items = self.smart_storage_controller.items
        items = []
        for item in _items:
            type_id = item.type_id
            quantity = item.quantity
            is_singleton = item.is_singleton
            items.append(StorageInventoryItem(type_id, quantity, is_singleton, self.smart_storage_controller.assembly_owner_id, self.locationFlag, self.smart_storage_controller.assembly_id, self.smart_storage_controller.is_owner))
        return items
    def GetName(self):
        return evetypes.GetName(self.smart_storage_controller._structure_item_id)
    def MultiMerge(self, data, mergeSourceID):
        return
    def StackAll(self, securityCode=None):
        return
    def LootAll(self, *args):
        items_quantity = sum([item.quantity for item in self.GetItems()])
        shipCargo = ShipCargo()
        max_quantity = sum([shipCargo.get_max_quantity(float(evetypes.GetVolume(typeID=item.type_id)), item.quantity) for item in self.GetItems()]) if self.hasCapacity else items_quantity
        if max_quantity < items_quantity:
            cap = shipCargo.GetCapacity()
            total_volume = sum([GetItemVolume(item) for item in self.GetItems()])
            raise UserError('NotEnoughCargoSpace', {'available': cap.capacity - cap.used, 'volume': total_volume})
        else:
            self.smart_storage_controller.withdraw_all()
    def OnDropData(self, nodes):
        if not self.smart_storage_controller.is_online():
            raise UserError('SmartStorageOffline')
        else:
            items = list(map(operator.attrgetter('item'), filter(lambda data: hasattr(data, 'item'), nodes)))
            if not items:
                return
            else:
                if any((item[appConst.ixSingleton] for item in items)):
                    raise UserError('SmartDeployableDoesNotAcceptSingleton', {'name': 'Smart storage unit'})
                else:
                    self._check_capacity(items)
    def _check_capacity(self, items):
        total_volume = []
        max_quantity = []
        items_quantity = []
        quantity = None
        cap = self.GetCapacity()
        available = cap.capacity - cap.used
        type_ids = [item.typeID for item in items]
        for item in items:
            items_quantity.append(item.quantity)
            itemvolume = float(GetItemVolume(item))
            total_volume.append(itemvolume)
            max_quantity.append(self.get_max_quantity(itemvolume / item.quantity, item.quantity))
        total_volume = sum(total_volume)
        max_quantity = sum(max_quantity)
        items_quantity = sum(items_quantity)
        if len(type_ids)!= 1 and available < total_volume or (len(type_ids) == 1 and max_quantity < 1):
            total_volume = sum([GetItemVolume(item) for item in items])
            raise UserError('NotEnoughCargoSpace', {'available': available, 'volume': total_volume})
        else:
            if len(type_ids) == 1 and max_quantity < items_quantity or (uicore.uilib.Key(uiconst.VK_SHIFT) and len(type_ids) == 1):
                itemvolume = float(GetItemVolume(items[0]) / items[0].quantity)
                quantity = self.prompt_user_for_quantity_sd_resource(itemvolume, items_quantity)
                if not quantity:
                    return
            self.smart_storage_controller.on_drop_items(items, quantity)
    def quantity_from_prompt(self, item, itemQuantity, sourceLocation=None):
        message = localization.GetByLabel('UI/Inventory/ItemActions/DivideItemStack')
        quantity = item.stacksize
        ret = uix.QtyPopup(maxvalue=quantity, minvalue=0, setvalue=quantity, hint=message)
        if ret:
            return ret['qty']
        else:
            return None
    def AddItems(self, items):
        return
    def GetCapacity(self):
        ssu_attr = self.smart_storage_controller.smart_storage_attributes
        capacity = ssu_attr.capacity if session.charid == self.smart_storage_controller.assembly_owner_id else ssu_attr.personal_capacity
        totalVolume = sum((GetItemVolume(item) for item in self.GetItems()), 0)
        return utillib.KeyVal(capacity=capacity, used=totalVolume)
class StorageInventoryItem(object):
    def __init__(self, type_id, quantity, is_singleton, owner_id, flag_id, location_id, is_owner):
        self.__guid__ = 'listentry.Item'
        self.item = KeyVal(itemID=None, typeID=type_id, groupID=evetypes.GetGroupID(type_id), categoryID=evetypes.GetCategoryID(type_id), flagID=flag_id, ownerID=owner_id, locationID=location_id, stacksize=quantity, singleton=is_singleton)
        self.isFitted = True
        self.viewMode = 'Icons'
        self.is_owner = is_owner
        self._quantity = self.item.stacksize
    @property
    def ownerID(self):
        return self.item.ownerID
    @property
    def stacksize(self):
        return self.item.stacksize
    @property
    def quantity(self):
        return self._quantity
    @quantity.setter
    def quantity(self, value):
        if self._quantity!= value:
            self._quantity = value
    @property
    def singleton(self):
        return self.item.singleton
    @property
    def is_singleton(self):
        return self.item.singleton
    @property
    def locationID(self):
        return self.item.locationID
    @property
    def location_id(self):
        return self.item.locationID
    @property
    def flag_id(self):
        return self.item.flagID
    @property
    def flagID(self):
        return self.item.flagID
    @property
    def rec(self):
        return self.item
    @property
    def typeID(self):
        return self.item.typeID
    @property
    def itemID(self):
        return self.item.itemID
    @property
    def groupID(self):
        return self.item.groupID
    @property
    def categoryID(self):
        return self.item.categoryID
    @property
    def type_id(self):
        return self.typeID
    @property
    def unit_volume(self):
        return evetypes.GetVolume(self.typeID)
    def __getitem__(self, idx):
        match idx:
            case appConst.ixItemID:
                return
            case appConst.ixTypeID:
                return self.typeID
            case appConst.ixOwnerID:
                return self.ownerID
            case appConst.ixLocationID:
                return self.locationID
            case appConst.ixFlag:
                return self.flagID
            case appConst.ixQuantity:
                return self.quantity
            case appConst.ixGroupID:
                return self.groupID
            case appConst.ixCategoryID:
                return self.categoryID
            case appConst.ixCustomInfo:
                return
            case appConst.ixStackSize:
                return self.stacksize
            case appConst.ixSingleton:
                return self.singleton
        if False:
            pass
        return
class SmartStorageInvItem(InvItem):
    def GetMenu(self):
        return GetMenuService().GetMenuFromItemIDTypeID(None, self.rec.typeID, includeMarketDetails=True)
    def lock_item(self):
        self.lock_item_id = str(uuid.uuid4())
        uthread.new(self._lock_item_timeout, self.lock_item_id)
        self.state = uiconst.UI_DISABLED
        self.sr.icon.opacity = 0.25
    def _lock_item_timeout(self, id_: str):
        # ***<module>.SmartStorageInvItem._lock_item_timeout: Failure: Different control flow
        ms = 6000
        blue.synchro.SleepWallclock(ms)
        if self.lock_item_id is None or self.lock_item_id == id_:
                self.unlock_item()
    def unlock_item(self):
        self.state = uiconst.UI_NORMAL
        self.sr.icon.opacity = 1.0