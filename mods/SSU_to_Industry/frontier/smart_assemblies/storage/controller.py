# Decompiled with PyLingual (https://pylingual.io)
# Internal filename: 'C:\\BuildAgent\\work\\6ec9bf56460fca58\\packages\\frontier\\smart_assemblies\\client\\storage\\controller.py'
# Bytecode version: 3.12.0rc2 (3531)
# Source timestamp: 2026-03-17 10:26:08 UTC (1773743168)

from __future__ import annotations
import signals
import contextlib
import uthread
from eveProto.generated.eve_public.assembly.storageunit.api import notices_pb2
import appConst
from eveexceptions import UserError
from frontier.smart_assemblies.client.queries.inventory import move_items_to_tmp_storage
from frontier.smart_assemblies.common import utils as sa_utils
from frontier.smart_assemblies.common.models.inventory import InventoryItem
import logging
import evetypes
import typing as t
from carbon.common.script.sys.serviceManager import ServiceManager
if t.TYPE_CHECKING:
    from frontier.smart_assemblies.client.window.controller import AssemblyController
    from frontier.smart_assemblies.client.smart_assembly_svc import SmartAssemblySvc
logger = logging.getLogger(__name__)
class StorageController(object):
    def __init__(self, structure_item_id: int, structure_type_id: int, assembly_owner_id: int, assembly_controller: 'AssemblyController'):
        self._assembly_controller = assembly_controller
        self._structure_item_id = structure_item_id
        self._structure_type_id = structure_type_id
        self._assembly_owner_id = assembly_owner_id
        self._name = evetypes.GetName(self._structure_type_id)
        self._items = None
        self._fetching_items = False
        self.on_settings_open_changed = signals.Signal()
        self.on_inventory_change = signals.Signal()
        self.on_deposit_items_started = signals.Signal()
        self.on_deposit_items_completed = signals.Signal()
        self.on_withdraw_items_started = signals.Signal()
        self.on_withdraw_items_completed = signals.Signal()
        self._connect_event_handlers()
    def __del__(self):
        self._disconnect_event_handlers()
    def _connect_event_handlers(self):
        assembly_svc = self.smart_assembly_svc
        assembly_svc.on_items_deposited.connect(self._on_items_deposited)
        assembly_svc.on_items_withdrawn.connect(self._on_items_withdrawn)
        assembly_svc.on_deposit_items_started.connect(self.on_deposit_items_started)
        assembly_svc.on_deposit_items_completed.connect(self._on_deposit_items_completed)
        assembly_svc.on_withdraw_items_started.connect(self.on_withdraw_items_started)
        assembly_svc.on_withdraw_items_completed.connect(self._on_withdraw_items_completed)
    def _disconnect_event_handlers(self):
        assembly_svc = self.smart_assembly_svc
        assembly_svc.on_items_deposited.disconnect(self._on_items_deposited)
        assembly_svc.on_items_withdrawn.disconnect(self._on_items_withdrawn)
        assembly_svc.on_deposit_items_started.disconnect(self.on_deposit_items_started)
        assembly_svc.on_deposit_items_completed.disconnect(self._on_deposit_items_completed)
        assembly_svc.on_withdraw_items_started.disconnect(self.on_withdraw_items_started)
        assembly_svc.on_withdraw_items_completed.disconnect(self._on_withdraw_items_completed)
    @property
    def is_owner(self):
        return self.assembly_owner_id == session.charid
    def GetName(self):
        return self._name
    @property
    def GetItems(self):
        return self.items
    @property
    def assembly_id(self):
        return self._structure_item_id
    @property
    def assembly_type_id(self):
        return self._structure_type_id
    @property
    def assembly_owner_id(self):
        return self._assembly_owner_id
    @property
    def smart_storage_attributes(self):
        return sa_utils.get_smart_storage_unit_attributes(self.assembly_type_id)
    @property
    def smart_assembly_svc(self) -> SmartAssemblySvc:
        return ServiceManager.Instance().GetService('smartAssemblySvc')
    @property
    def sui_wallet(self):
        return ServiceManager.Instance().GetService('sui_wallet')
    @property
    def items(self) -> 'list[InventoryItem]':
        if self._items is not None:
            print(self._items)
            return self._items
        else:
            with self._lock('fetch_items'):
                if not self._fetching_items:
                    self._fetching_items = True
                    uthread.new(self._fetch_items_background)
                    print(f"{self._items} from fetch_items")
                    return self._items
                else:
                    print("a")
    @property
    def items(self):
        if self._items is not None:
            print(self._items)
            return self._items
        else:
            with self._lock('fetch_items'):
                if not self._fetching_items:
                    self._fetching_items = True
                    uthread.new(self._fetch_items_background)
                    print(f"{self._items} from fetch_items")
                    return self._items
                else:
                    print("b")       
    def is_online(self):
        return self._assembly_controller.is_online()
    def withdraw_all(self):
        uthread.new(self._withdraw_all, session.charid, session.shipid)
    def _withdraw_all(self, char_id, ship_id):
        items = self.smart_assembly_svc.get_inventory_for_ssu(char_id, self.assembly_id)
        if items is None:
            return
        else:
            self.smart_assembly_svc.withdraw_items(ship_id, appConst.flagCargo, items, self.assembly_id)
    @items.setter
    def items(self, items: 'list[InventoryItem]') -> None:
        print("!??!")
        self._items = items
        self.on_inventory_change(self.assembly_id)
    def _fetch_items_background(self):
        try:
            items = self.smart_assembly_svc.get_inventory_for_ssu(session.charid, self.assembly_id)
            if items is not None:
                self._items = items
                self.items = self._items
            else:
                logger.error('[SmartStorageUnit] Failed to fetch items from chain for owner %s, ssu %s, res %s', self.assembly_owner_id, self.assembly_id, res.data)
                self._items = []
                self.items = self._items
        except Exception as e:
            logger.exception('[SmartStorageUnit] Exception while fetching items: %s', e)
            self._items = []
            self.items = self._items
        finally:
            self._fetching_items = False
    @contextlib.contextmanager
    def _lock(self, key: str) -> t.Generator[None, None, None]:
        print("_lock called!")
        uthread.Lock(self, key)
        try:
            yield key
        finally:
            uthread.UnLock(self, key)
    def _on_deposit_items_completed(self, assembly_id: int, success: bool, items: list[InventoryItem]):
        if assembly_id!= self.assembly_id:
            return
        else:
            self.on_deposit_items_completed(assembly_id, success, items)
    def _on_withdraw_items_completed(self, assembly_id: int, success: bool, items: list[InventoryItem]):
        if assembly_id!= self.assembly_id:
            return
        else:
            self.on_withdraw_items_completed(assembly_id, success, items)
    def _on_items_deposited(self, assembly_id: int, items: list[InventoryItem]):
        if assembly_id!= self.assembly_id:
            return
        else:
            self._initialize_items()
            for item in items:
                self._add_item_to_inventory(item)
    def _add_item_to_inventory(self, item: InventoryItem):
        for existing_item in self._items:
            if existing_item.type_id == item.type_id:
                existing_item.quantity += item.quantity
                self.items = self._items
                return
        self._items.append(item)
        self.items = self._items
    def _on_items_withdrawn(self, assembly_id: int, items: list[InventoryItem]):
        if assembly_id!= self.assembly_id:
            return
        else:
            self._initialize_items()
            for item in items:
                self._remove_item_from_inventory(item)
    def _remove_item_from_inventory(self, item: InventoryItem):
        for i, existing_item in enumerate(self._items):
            if existing_item.type_id == item.type_id:
                if existing_item.quantity <= item.quantity:
                    self._items.pop(i)
                else:
                    existing_item.quantity -= item.quantity
                self.items = self._items
                break
    def _initialize_items(self):
        if self._items is None:
            self._items = []
            with self._lock('fetch_items'):
                if not self._fetching_items:
                    self._fetching_items = True
                    uthread.new(self._fetch_items_background)
    def on_drop_items(self, items, quantity: int | None):
        self.sui_wallet.validate_wallet_address()
        if not self.smart_assembly_svc.is_operational(self.assembly_id):
            raise UserError('AssemblyNotOperational')
        else:
            new_item_id, location, flag = move_items_to_tmp_storage(self.assembly_id, items, quantity)
            self.smart_assembly_svc.deposit_items(self.assembly_id, items, quantity, new_item_id, location, flag)