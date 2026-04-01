# Decompiled with PyLingual (https://pylingual.io)
# Internal filename: 'C:\\BuildAgent\\work\\6ec9bf56460fca58\\packages\\frontier\\industry\\client\\ui\\controller.py'
# Bytecode version: 3.12.0rc2 (3531)
# Source timestamp: 2026-03-17 10:26:08 UTC (1773743168)

from __future__ import annotations
import evetypes
import graviton
import inventorycommon.const as inv_const
import typing as t
import uthread2
from carbon.common.lib.const import SEC
from carbonui import uiconst
from carbonui.uicore import uicore
from collections import defaultdict
from eve.client.script.ui.util import uix
from frontier.industry.client import qa_tools
from frontier.industry.client.facility_instance import IndustryFacilityInstance
from frontier.industry.client.utility import get_blueprint_name, get_errors_hint, get_production_time_remaining, get_remaining_input_runs, get_remaining_output_runs, prompt_error_message
from frontier.industry.common.errors import ErrorHeaders, ErrorReason, IndustryDiscontinueErrors, IndustryInventoryErrors, LoadErrorReason, StartErrorReason
from frontier.industry.common.model import ItemSlot, ProductionState
from frontier.industry.common.utility import get_facility, get_valid_items_to_move
from frontier.smart_assemblies.client.util import get_available_inventories
from frontier.smart_assemblies.common.utils.const import is_portable_assembly
from eve.common.lib import appConst as const
from signals import Signal
import re
if t.TYPE_CHECKING:
    import blue
    from frontier.industry.common.model import FacilityBlueprint
    from frontier.industry.client.industry_svc import IndustryService
class ItemSlotController(object):
    def __init__(self, item_slot: ItemSlot, current_quantity: int, pending_quantity: int, get_nearby_inventories, deposit, withdraw):
        self._item_slot = item_slot
        self._current_quantity = current_quantity
        self._pending_quantity = pending_quantity
        self._get_nearby_inventories = get_nearby_inventories
        self._deposit = deposit
        self._withdraw = withdraw
        self.on_current_quantity_changed = Signal('on_current_quantity_changed')
        self.on_pending_quantity_changed = Signal('on_pending_quantity_changed')
    def deposit(self, inventory, location, runs=None, prompt_quantity=False):
        print(f"Attempting to deposit to location {location} with inventory {inventory} for item slot {self.type_id} and its {self._deposit}")
        if self._deposit:
            print(location)
            self._deposit(self.type_id, inventory, location, runs, prompt_quantity)
    def withdraw(self, inventory, location, runs=None, prompt_quantity=False):
        if self._withdraw:
            self._withdraw(self.type_id, inventory, location, runs, prompt_quantity)
    def set_current_quantity(self, value):
        if self._current_quantity == value:
            return
        else:
            self._current_quantity = value
            self.on_current_quantity_changed()
    def set_pending_quantity(self, value):
        if self._pending_quantity == value:
            return
        else:
            self._pending_quantity = value
            self.on_pending_quantity_changed()
    @property
    def name(self):
        return evetypes.GetName(self.type_id)
    @property
    def group_name(self):
        return evetypes.GetGroupName(self.type_id)
    @property
    def type_id(self):
        return self._item_slot.type_id
    @property
    def quantity_per_run(self):
        return self._item_slot.quantity_per_run
    @property
    def max_quantity(self):
        return self._item_slot.max_storable_quantity
    @property
    def current_quantity(self):
        return self._current_quantity
    @property
    def pending_quantity(self):
        return self._pending_quantity
    @property
    def remaining_quantity(self):
        return max(0, self.max_quantity - self.current_quantity)
    @property
    def max_runs(self):
        return self.max_quantity // self.quantity_per_run
    @property
    def remaining_runs(self):
        return self.remaining_quantity // self.quantity_per_run
    @property
    def usage_percentage(self):
        if self.current_quantity is None:
            return 0
        else:
            return self.current_quantity / self.max_quantity
    @property
    def is_full(self):
        return self.usage_percentage >= 1
    @property
    def pending_usage_percentage(self):
        if self._pending_quantity is None:
            return
        else:
            return (self.current_quantity + self.pending_quantity) / self.max_quantity
    @property
    def allow_deposit(self):
        return self._deposit is not None
    @property
    def can_deposit(self):
        return self.allow_deposit and self.remaining_quantity > 0
    @property
    def allow_withdraw(self):
        return self._withdraw is not None
    @property
    def can_withdraw(self):
        return self.allow_withdraw and bool(self.current_quantity)
    def get_nearby_inventories(self):
        return self._get_nearby_inventories([self.type_id])
class FacilityPageController(object):
    def __init__(self, facility_id, facility_type_id):
        self._facility_id = facility_id
        self._facility_type_id = facility_type_id
        self._service = sm.GetService('industry')
        self._facility_data = get_facility(facility_type_id)
        self._facility_instance = self._service.get_facility(facility_id, facility_type_id)
        self._is_online = False
        self.locationFlag = const.flagIndustryInventory
        self._available_blueprints = None
        self._input_slots = []
        self._output_slots = []
        self._nearby_items = None
        self._update_slot_controllers()
        self.on_active_blueprint_changed = Signal('on_active_blueprint_changed')
        self.on_nearby_items_changed = Signal('on_nearby_items_changed')
        self._register()
    def close(self):
        self.on_active_blueprint_changed.clear()
        self.on_nearby_items_changed.clear()
        self._unregister()
    def _register(self):
        facility_instance = self._facility_instance
        facility_instance.on_blueprint_changed.connect(self._on_blueprint_changed)
        facility_instance.on_items_changed.connect(self._on_items_changed)
        facility_instance.on_remaining_runs_changed.connect(self._on_remaining_runs_changed)
        sm.RegisterForNotifyEvent(self, 'OnItemChanged')
    def _unregister(self):
        facility_instance = self._facility_instance
        facility_instance.on_blueprint_changed.disconnect(self._on_blueprint_changed)
        facility_instance.on_items_changed.disconnect(self._on_items_changed)
        facility_instance.on_remaining_runs_changed.disconnect(self._on_remaining_runs_changed)
        sm.UnregisterForNotifyEvent(self, 'OnItemChanged')
    def load_blueprint(self, blueprint: FacilityBlueprint):
        if blueprint == self.active_blueprint:
            self.on_active_blueprint_changed()
            return
        else:
            if not self.check_load_errors():
                return
            else:
                if self._facility_instance.production_state == ProductionState.DISCONTINUING and (not _confirm_load_blueprint()):
                    return
                else:
                    self._service.load_blueprint(self._facility_id, blueprint.blueprint_id)
    def start_production(self):
        if not self.active_blueprint:
            return
        else:
            if not self.check_start_errors():
                return
            else:
                self._service.start_production(self._facility_id)
    def discontinue_production(self):
        if not self.active_blueprint:
            return
        else:
            if self._facility_instance.production_state!= ProductionState.RUNNING:
                prompt_error_message(IndustryDiscontinueErrors.NOT_RUNNING, ErrorHeaders.DISCONTINUE)
                return
            else:
                self._service.discontinue_production(self._facility_id)
    def refresh_facility_details(self):
        if not self._facility_instance:
            return
        else:
            self._service.refresh_facility_details(self._facility_id)
    def deposit_input_items(self, type_id, inventory, origin_inventory, runs=None, prompt_quantity=False):
        # ***<module>.FacilityPageController.deposit_input_items: Failure: Different control flow
        if not self.active_blueprint:
            return
        else:
            current_quantity = self.input_stacks.get(type_id, 0)
            input_slot = self._facility_instance.blueprint.inputs[type_id]
            max_quantity = input_slot.max_storable_quantity - current_quantity

            if not max_quantity:
                prompt_error_message(IndustryInventoryErrors.FULL_SLOT, ErrorHeaders.DEPOSIT)
                return
            else:
                if runs and (not prompt_quantity):
                        remainder = current_quantity % input_slot.quantity_per_run
                        runs_quantity = input_slot.quantity_per_run if remainder == 0 else input_slot.quantity_per_run - remainder
                        max_quantity = min(runs_quantity, max_quantity)
                if type(inventory) == list:
                    for item in inventory:
                        if item.type_id == type_id and (not item.is_singleton):
                            inventory_items = [item]
                            available_quantity = item.quantity
                else:
                    inventory_items = [item for item in inventory.GetItems() if (item.typeID == type_id and (not item.singleton))]
                    available_quantity = sum([item.stacksize for item in inventory_items])
                if not available_quantity:
                    prompt_error_message(IndustryInventoryErrors.NO_ITEMS_AVAILABLE, ErrorHeaders.DEPOSIT)
                    return
                else:
                    quantity = min(max_quantity, available_quantity)
                    print(inventory_items)
                    self._deposit_input_items(inventory_items, quantity, prompt_quantity, origin_inventory)
    def deposit_input_items_from_drop(self, inventory_items, item_origin, prompt_quantity=False):
        if not self.active_blueprint or not inventory_items:
            return None
        else:
            quantity = None
            if prompt_quantity:
                quantity = inventory_items[0].stacksize
            self._deposit_input_items(inventory_items, quantity, prompt_quantity, item_origin)
    def _deposit_input_items(self, inventory_items, quantity, prompt_quantity, item_origin):
        if not self.active_blueprint or not inventory_items:
            return None
        else:
            if prompt_quantity and quantity:
                quantity = _quantity_prompt(quantity, 'Select quantity to deposit')
                if not quantity:
                    return
            deposit_items = _get_valid_deposit_items(inventory_items, self._facility_instance.blueprint.inputs, self._facility_instance.input_stacks, quantity)
            if deposit_items:
                self._service.deposit_input_items(self._facility_id, deposit_items, item_origin)
            else:
                prompt_error_message(IndustryInventoryErrors.INVALID_DEPOSIT, ErrorHeaders.DEPOSIT)
    def withdraw_input_items(self, type_id, inventory, inventory_flag=None,runs=None, prompt_quantity=False):
        if not self.active_blueprint:
            return
        else:
            quantity = self.input_stacks.get(type_id)
            if not quantity:
                prompt_error_message(IndustryInventoryErrors.NO_ITEMS_AVAILABLE, ErrorHeaders.WITHDRAW)
                return
            else:
                if runs and (not prompt_quantity):
                        slot = self._facility_instance.blueprint.inputs[type_id]
                        remainder = quantity % slot.quantity_per_run
                        runs_quantity = slot.quantity_per_run if remainder == 0 else remainder
                        quantity = min(runs_quantity, quantity)
                if prompt_quantity:
                    quantity = _quantity_prompt(quantity, 'Select quantity to withdraw')
                    if not quantity:
                        return
                withdraw_items = _get_valid_withdraw_items({type_id: quantity}, inventory.get_remaining_capacity(), self._facility_instance.blueprint.inputs.keys())
                if withdraw_items:
                    if hasattr(inventory, "smart_storage_controller"):
                        print(f"withdrawing {withdraw_items} from industry to Smart Storage {inventory.smart_storage_controller._structure_item_id}")
                        self._service.withdraw_input_items(self._facility_id, self.locationFlag, withdraw_items, inventory.smart_storage_controller._structure_item_id, inventory)
                    else:
                        self._service.withdraw_input_items(self._facility_id, self.locationFlag, withdraw_items, inventory.itemID, inventory)
    def withdraw_output_items(self, type_id, inventory, runs=None, prompt_quantity=False):
        if not self.active_blueprint:
            return
        else:
            quantity = self.output_stacks.get(type_id)
            if not quantity:
                prompt_error_message(IndustryInventoryErrors.NO_ITEMS_AVAILABLE, ErrorHeaders.WITHDRAW)
                return
            else:
                if runs and (not prompt_quantity):
                        slot = self._facility_instance.blueprint.outputs[type_id]
                        remainder = quantity % slot.quantity_per_run
                        runs_quantity = slot.quantity_per_run if remainder == 0 else remainder
                        quantity = min(runs_quantity, quantity)
                if prompt_quantity:
                    quantity = _quantity_prompt(quantity, 'Select quantity to withdraw')
                    if not quantity:
                        return
                withdraw_items = _get_valid_withdraw_items({type_id: quantity}, inventory.get_remaining_capacity(), self._facility_instance.blueprint.outputs.keys())
                print(withdraw_items)
                if withdraw_items:
                    if hasattr(inventory, "smart_storage_controller"):
                        print(f"withdrawing {withdraw_items} from industry to Smart Storage {inventory.smart_storage_controller._structure_item_id}")
                        self._service.withdraw_input_items(self._facility_id, self.locationFlag, withdraw_items, inventory.smart_storage_controller._structure_item_id, withdraw_items, inventory)
                    else:
                        self._service.withdraw_input_items(self._facility_id, self.locationFlag, withdraw_items, inventory.itemID, withdraw_items,inventory)
    @property
    def facility_instance(self) -> t.Optional[IndustryFacilityInstance]:
        return self._facility_instance
    @property
    def input_slots(self) -> list[ItemSlotController]:
        return self._input_slots
    @property
    def output_slots(self) -> list[ItemSlotController]:
        return self._output_slots
    @property
    def available_blueprints(self) -> list[FacilityBlueprint]:
        if self._available_blueprints is None:
            self._available_blueprints = sorted(self._facility_data.blueprints.values(), key=lambda b: get_blueprint_name(b))
        return self._available_blueprints
    @property
    def active_blueprint(self) -> t.Optional[FacilityBlueprint]:
        return self._facility_instance.blueprint if self._facility_instance else None
    @property
    def active_blueprint_id(self) -> t.Optional[int]:
        blueprint = self.active_blueprint
        return blueprint.blueprint_id if blueprint else None
    @property
    def is_active_blueprint_invalid(self):
        active_blueprint = self.active_blueprint
        if not active_blueprint:
            return True
        else:
            return active_blueprint not in self.available_blueprints
    @property
    def production_run(self):
        return self._facility_instance.production_run
    @property
    def input_stacks(self):
        return self._facility_instance.input_stacks
    @property
    def output_stacks(self):
        return self._facility_instance.output_stacks
    @property
    def remaining_runs(self):
        return self._facility_instance.remaining_runs
    @property
    def run_time_remaining(self):
        return get_production_time_remaining(self.facility_instance.production_run)
    @property
    def estimated_total_time(self):
        run_time_remaining = self.run_time_remaining
        return self.remaining_runs * self.active_blueprint.run_time * SEC + run_time_remaining
    @property
    def state_text(self):
        return str(self.facility_instance.production_state)
    @property
    def is_online(self):
        if is_portable_assembly(self._facility_type_id):
            return True
        else:
            return sm.GetService('smartAssemblySvc').is_online(self._facility_id)
    def get_nearby_inventories(self, relevant_type_ids=None):
        if relevant_type_ids:
            include_ship_hangars = any([evetypes.GetCategoryID(type_id) == inv_const.categoryShip for type_id in relevant_type_ids])
        else:
            include_ship_hangars = False
        return get_available_inventories(exclude_item_ids=[self._facility_id], include_ship_hangars=include_ship_hangars)
    def get_nearby_items(self):
        if self._nearby_items is None:
            inventories = self.get_nearby_inventories()
            result = defaultdict(int)
            for inventory in inventories:
                for item in inventory.GetItems():
                    if not item.singleton:
                        result[item.typeID] += item.stacksize
            self._nearby_items = dict(result)
        return self._nearby_items
    def get_cta_button_config(self):
        facility_instance = self._facility_instance
        has_details = facility_instance.details_fetched
        requesting = facility_instance.requesting
        errors = []
        if not has_details:
            errors.append(LoadErrorReason.MISSING_DETAILS)
        if facility_instance.production_state == ProductionState.RUNNING:
            return {'text': 'Discontinue', 'callback': lambda *args, **kwargs: self.discontinue_production(), 'enabled': not bool(errors) and (not requesting), 'busy': requesting, 'style': graviton.ButtonStyle.NORMAL}
        else:
            errors.extend(self.get_start_errors())
            if errors:
                hint = 'Unable to start\n\n{}'.format(get_errors_hint(errors))
            else:
                hint = None
            text = 'Start'
            return {'text': text, 'callback': lambda *args, **kwargs: self.start_production(), 'enabled': not bool(errors) and (not requesting), 'busy': requesting, 'hint': hint, 'style': graviton.ButtonStyle.PRIMARY}
    def get_load_cta_config(self, blueprint):
        if blueprint == self.active_blueprint:
            text = 'View Production'
            errors = []
        else:
            text = 'Select'
            errors = self.get_load_errors()
        requesting = self._facility_instance.requesting
        if errors:
            hint = 'Unable to select\n\n{}'.format(get_errors_hint(errors))
        else:
            hint = None
        return {'text': text, 'callback': lambda *args, **kwargs: self.load_blueprint(blueprint), 'enabled': not bool(errors) and (not requesting), 'busy': requesting, 'hint': hint, 'get_menu': lambda *args, **kwargs: qa_tools.get_cta_load_menu(self, blueprint)}
    def check_load_errors(self):
        errors = self.get_load_errors()
        if errors:
            prompt_error_message(errors[0], ErrorHeaders.LOAD)
            return False
        else:
            return True
    def get_load_errors(self):
        errors = []
        if not self._facility_instance.details_fetched:
            errors.append(LoadErrorReason.MISSING_DETAILS)
        if not self.is_online:
            errors.append(ErrorReason.FACILITY_OFFLINE)
        if self._facility_instance.has_items:
            errors.append(LoadErrorReason.ITEMS_PRESENT)
        if self._facility_instance.production_state == ProductionState.RUNNING:
            errors.append(ErrorReason.ALREADY_RUNNING)
        return errors
    def check_start_errors(self):
        errors = self.get_start_errors()
        if errors:
            prompt_error_message(errors[0], ErrorHeaders.START)
            return False
        else:
            return True
    def get_start_errors(self):
        errors = []
        blueprint = self._facility_instance.blueprint
        if not self.is_online:
            errors.append(ErrorReason.FACILITY_OFFLINE)
        if self.is_active_blueprint_invalid:
            errors.append(StartErrorReason.INVALID_BLUEPRINT)
        if not get_remaining_input_runs(blueprint.inputs, self.input_stacks):
            errors.append(StartErrorReason.MISSING_INPUT)
        if not get_remaining_output_runs(blueprint.outputs, self.output_stacks):
            errors.append(StartErrorReason.OUTPUT_CAPACITY)
        if self._facility_instance.production_state == ProductionState.RUNNING:
            errors.append(ErrorReason.ALREADY_RUNNING)
        return errors
    def _update_slot_controllers(self):
        if self.active_blueprint is None:
            self._input_slots = []
            self._output_slots = []
            return
        else:
            self._input_slots = [ItemSlotController(item_slot, current_quantity=self._facility_instance.input_stacks.get(item_slot.type_id, 0), pending_quantity=0, get_nearby_inventories=self.get_nearby_inventories, deposit=self.deposit_input_items, withdraw=self.withdraw_input_items) for item_slot in self.active_blueprint.inputs.values()]
            self._output_slots = [ItemSlotController(item_slot, current_quantity=self._facility_instance.output_stacks.get(item_slot.type_id, 0), pending_quantity=0, get_nearby_inventories=self.get_nearby_inventories, deposit=None, withdraw=self.withdraw_output_items) for item_slot in self.active_blueprint.outputs.values()]
            self._update_pending_output()
    def _on_blueprint_changed(self):
        self._update_slot_controllers()
        self._update_pending_output()
        self.on_active_blueprint_changed()
    def _on_items_changed(self):
        self._update_current_quantity()
    def _on_remaining_runs_changed(self):
        self._update_pending_output()
    def OnItemChanged(self, item, change, location):
        self._update_available_items()
    def _update_current_quantity(self):
        for slot in self.input_slots:
            slot.set_current_quantity(self._facility_instance.input_stacks.get(slot.type_id, 0))
        for slot in self.output_slots:
            slot.set_current_quantity(self._facility_instance.output_stacks.get(slot.type_id, 0))
    def _update_pending_output(self):
        pending_runs = self.remaining_runs
        if pending_runs and self.facility_instance.is_production_active:
                pending_runs += 1
        for slot in self.output_slots:
            slot.set_pending_quantity(slot.quantity_per_run * pending_runs)
    @uthread2.debounce(0.2)
    def _update_available_items(self):
        self._nearby_items = None
        self.on_nearby_items_changed()
def _confirm_load_blueprint():
    result = uicore.Message('CustomWarning', {'header': 'Active Production Detected', 'warning': 'Loading a new blueprint will stop the current run.\r\n\r\nAre you sure you want to continue?'}, buttons=uiconst.YESNO)
    return result == uiconst.ID_YES
def _get_valid_deposit_items(items, valid_input_items, deposited_items, quantity):
    if not items:
        return
    else:
        print("DEBUG")
        print("DEBUG")
        result = {}
        remaining_capacity = {type_id: item_slot.max_storable_quantity - deposited_items.get(type_id, 0) for type_id, item_slot in valid_input_items.items()}
        consume_quantity = {type_id: quantity if quantity else item_slot.max_storable_quantity for type_id, item_slot in valid_input_items.items()}
        for item in items:
            if hasattr(item, 'type_id'):
                if item.type_id not in valid_input_items:
                    prompt_error_message(IndustryInventoryErrors.INVALID_TYPE, ErrorHeaders.DEPOSIT)
                    return
                else:
                    consume = min(remaining_capacity[item.type_id], consume_quantity[item.type_id])
                    if consume > 0:
                        remaining_capacity[item.type_id] -= consume
                        consume_quantity[item.type_id] -= consume
                        #sequential: 1000000017443
                        result = {int(f"{item.item_id}"[12:25]): consume}
            else:
                if item.ownerID!= session.charid:
                    prompt_error_message(IndustryInventoryErrors.INVALID_OWNER, ErrorHeaders.DEPOSIT)
                    return
                else:
                    if bool(item.singleton):
                        prompt_error_message(IndustryInventoryErrors.SINGLETON, ErrorHeaders.DEPOSIT)
                        return
                    else:
                        consume = min(remaining_capacity[item.typeID], min(consume_quantity[item.typeID], item.stacksize))
                        if consume > 0:
                            remaining_capacity[item.typeID] -= consume
                            consume_quantity[item.typeID] -= consume
                            result[item.itemID] = consume
        if not result:
            prompt_error_message(IndustryInventoryErrors.NOT_ENOUGH_CAPACITY, ErrorHeaders.DEPOSIT)
        return result
def _get_valid_withdraw_items(items, capacity, valid_types_ids):
    # ***<module>._get_valid_withdraw_items: Failure: Different control flow
    if not items:
        return
    else:
        if sum(items.values()) == 0:
            return
        else:
            filtered_items = {type_id: quantity if type_id in valid_types_ids else None for type_id, quantity in items.items()}
            if not filtered_items:
                return
            else:
                valid_items, remaining_capacity = get_valid_items_to_move(filtered_items, capacity)
                if not valid_items:
                    prompt_error_message(IndustryInventoryErrors.NOT_ENOUGH_CAPACITY, ErrorHeaders.WITHDRAW)
                    return
                else:
                    return valid_items
def _quantity_prompt(quantity, text):
    ret = uix.QtyPopup(maxvalue=quantity, minvalue=0, setvalue=quantity, hint=text)
    if ret:
        return ret['qty']
    else:
        return None