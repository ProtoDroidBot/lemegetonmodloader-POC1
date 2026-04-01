# Decompiled with PyLingual (https://pylingual.io)
# Internal filename: 'C:\\BuildAgent\\work\\6ec9bf56460fca58\\packages\\frontier\\smart_assemblies\\client\\smart_assembly_svc.py'
# Bytecode version: 3.12.0rc2 (3531)
# Source timestamp: 2026-03-17 10:26:08 UTC (1773743168)

from __future__ import annotations
import dataclasses
import logging
import monolithconfig
import threadutils
from caching import Memoize
from carbon.common.lib.const import ixItemID
from carbon.common.script.net.machoNet import MachoNetService
from carbon.common.script.sys.service import Service
from carbon.common.script.sys.serviceManager import ServiceManager
from carbonui.uicore import uicore
from collections import defaultdict
from eve.client.script.remote.michelle import Michelle
from eve.client.script.ui.services.menusvc import MenuSvc
from eveexceptions import UserError
from frontier.smart_assemblies.client.proto_messenger import AssemblyMessenger
from frontier.smart_assemblies.client.window.window import AssemblyDockablePanel
from frontier.smart_assemblies.common import utils as sa_utils
from frontier.smart_assemblies.common.gate import Gate, validate_gate_link
from frontier.smart_assemblies.common.models.inventory import InventoryItem
from frontier.smart_assemblies.common.utils import get_smart_gate_attributes
from frontier.smart_assemblies.common.utils.const import is_portable_assembly
from frontier.web3.client.sui_wallet_service import SuiWalletService
from inventorycommon import const as inv_const
from publicGateway.publicGatewaySvc import PublicGatewaySvc
from signals import Signal
from typing import TYPE_CHECKING
from urllib.parse import urlencode
if TYPE_CHECKING:
    from frontier.smart_assemblies.server.smart_assembly_service import SmartAssemblyService
logger = logging.getLogger(__name__)
@dataclasses.dataclass
class AssemblyMetadata:
    dapp_url: str = ''
class SmartAssemblySvc(Service):
    # ***<module>.SmartAssemblySvc: Failure: Compilation Error
    __guid__ = 'svc.smartAssemblySvc'
    __servicename__ = 'SmartAssemblySvc'
    __displayname__ = 'Smart Storage Unit Svc'
    __notifyevents__ = ['OnAssemblyMetadataChanged', 'OnCRDataChange', 'OnSessionChanged']
    menu_service: MenuSvc
    macho_net: MachoNetService
    michelle: Michelle
    public_gateway: PublicGatewaySvc
    sui_wallet: SuiWalletService
    def __init__(self):
        super(SmartAssemblySvc, self).__init__()
        self._messenger = None
        self._assemblies_metadata = defaultdict(AssemblyMetadata)
        self._energy_config = {}
        self._fuel_config = {}
        self._base_dapp_url = ''
        self._chain_tenant = ''
        self.state_changed_signal = Signal('smart_assembly_state_change')
        self.on_name_changed = Signal('on_name_changed')
        self.on_metadata_changed = Signal('on_metadata_changed')
        self.on_network_node_fuel_changed = Signal('on_network_node_fuel_changed')
        self.on_gate_link_changed = Signal('on_gate_link_changed')
        self.on_items_deposited = Signal('on_items_deposited')
        self.on_items_withdrawn = Signal('on_items_withdrawn')
        self.on_deposit_items_started = Signal('on_deposit_items_started')
        self.on_deposit_items_completed = Signal('on_deposit_items_completed')
        self.on_withdraw_items_started = Signal('on_withdraw_items_started')
        self.on_withdraw_items_completed = Signal('on_withdraw_items_completed')
        self.on_withdraw_item_types_started = Signal('on_withdraw_item_types_started')
        self.on_withdraw_item_types_completed = Signal('on_withdraw_item_types_completed')
    @property
    def _remote_service(self) -> SmartAssemblyService:
        return ServiceManager.Instance().RemoteSvc('smartAssemblyService')
    def Run(self, *args, **kwargs):
        Service.Run(self, *args, **kwargs)
        self._messenger = AssemblyMessenger(self.public_gateway, on_network_node_fuel_changed=self.on_network_node_fuel_changed, on_items_deposited=self.on_items_deposited, on_items_withdrawn=self.on_items_withdrawn)
        self._base_dapp_url = self.macho_net.GetGlobalConfig().get('smart_assembly_base_dapp_url', _get_default_base_dapp_url())
        self._chain_tenant = monolithconfig.get_client_tenant().lower()
    def OnSessionChanged(self, isRemote, session, change):
        if 'solarsystemid2' in change:
            self._assemblies_metadata.clear()
    def OnCRDataChange(self, ball_id: int, update: dict):
        cr_data = self.michelle.GetCrData(ball_id)
        if cr_data is None or cr_data.categoryID!= inv_const.categoryDeployable or cr_data.itemID is None:
            return None
        else:
            if 'assembly_status' in update:
                self.state_changed_signal(cr_data.itemID, cr_data.assembly_status)
            if 'name' in update:
                self.on_name_changed(cr_data.itemID, cr_data.name)
            if 'targetSolarsystemID' in update:
                self.on_gate_link_changed(cr_data.itemID, cr_data.targetSolarsystemID)
    def OnAssemblyMetadataChanged(self, assembly_id: int, dapp_url: str):
        self._assemblies_metadata[assembly_id].dapp_url = dapp_url
        self.on_metadata_changed(assembly_id, dapp_url)
    def open_assembly_window(self, item_id: int, type_id: int, ball_id: int, owner_id: int):
        AssemblyDockablePanel.open(item_id=item_id, type_id=type_id, ball_id=ball_id, owner_id=owner_id, menu_svc=self.menu_service, sui_wallet=self.sui_wallet)
    @threadutils.threaded
    def on_interaction(self, assembly_id):
        state = self.get_state(assembly_id)
        if state == sa_utils.SmartDeployableGameState.UNSPECIFIED:
            uicore.Message('CustomNotify', {'notify': 'Assembly corrupted.\nAttempting reconnection.'})
            self._remote_service.retry_chain_anchor(assembly_id)
        self.sui_wallet.refresh_wallet_address()
    def get_base_dapp_url(self):
        return self._base_dapp_url
    def get_energy_usage(self, type_id) -> int | None:
        return self.get_energy_config().get(type_id, 0)
    @Memoize(5)
    def get_energy_config(self) -> dict:
        if not self._energy_config:
            self._energy_config = self._messenger.get_energy_config()
        return self._energy_config
    @Memoize(5)
    def get_fuel_config(self):
        if not self._fuel_config:
            self._fuel_config = self._messenger.get_fuel_config()
        return self._fuel_config
    def get_root_url(self, assembly_id):
        return f'{self.get_base_dapp_url()}/client/root/?{self._get_url_params(assembly_id)}'
    def get_behaviour_url(self, assembly_id):
        return f'{self.get_base_dapp_url()}/client/behaviour/?{self._get_url_params(assembly_id)}'
    def get_custom_behaviour_url(self, assembly_id: int) -> str:
        if assembly_id not in self._assemblies_metadata:
            self._fetch_metadata(assembly_id)
            return ''
        else:
            return self._assemblies_metadata[assembly_id].dapp_url
    @threadutils.threaded
    def _fetch_metadata(self, assembly_id: int):
        metadata = self._messenger.get_metadata(assembly_id)
        if metadata is None:
            return
        else:
            self._assemblies_metadata[assembly_id].dapp_url = metadata['dapp_url']
            self.on_metadata_changed(assembly_id, metadata['dapp_url'])
    def get_state(self, assembly_id):
        cr_data = self.michelle.GetCrData(assembly_id)
        if cr_data is None:
            return sa_utils.SmartDeployableGameState.UNSPECIFIED
        else:
            if is_portable_assembly(cr_data.typeID):
                return sa_utils.SmartDeployableGameState.ONLINE
            else:
                if cr_data:
                    return cr_data.assembly_status
                else:
                    return sa_utils.SmartDeployableGameState.UNSPECIFIED
    def is_online(self, assembly_id):
        return self.get_state(assembly_id) == sa_utils.SmartDeployableGameState.ONLINE
    def is_operational(self, assembly_id):
        state = self.get_state(assembly_id)
        return state in (sa_utils.SmartDeployableGameState.OFFLINE, sa_utils.SmartDeployableGameState.ONLINE)
    @threadutils.threaded
    def set_online(self, assembly_id: int, type_id: int):
        if is_portable_assembly(type_id):
            return
        else:
            self.sui_wallet.validate_wallet_address()
            success = False
            try:
                transaction = self._remote_service.set_online(assembly_id)
                signature = self.sui_wallet.sign_transaction(transaction['transaction_data'])
                success = self._remote_service.set_online_signature(assembly_id, transaction['transaction_uuid'], signature)
            except:
                pass
            finally:
                if not success:
                    uicore.Message('CustomNotify', {'notify': 'Failed to online assembly'})
    @threadutils.threaded
    def set_offline(self, assembly_id: int, type_id: int):
        if is_portable_assembly(type_id):
            return
        else:
            self.sui_wallet.validate_wallet_address()
            success = False
            try:
                transaction = self._remote_service.set_offline(assembly_id)
                signature = self.sui_wallet.sign_transaction(transaction['transaction_data'])
                success = self._remote_service.set_offline_signature(assembly_id, transaction['transaction_uuid'], signature)
            except:
                pass
            finally:
                if not success:
                    uicore.Message('CustomNotify', {'notify': 'Failed to offline assembly'})
    @threadutils.threaded
    def publish_location(self, assembly_id: int):
        try:
            self._remote_service.publish_location(assembly_id)
        except:
            uicore.Message('CustomNotify', {'notify': 'Failed to publish assembly location'})
    def get_network_node_monitor_url(self, assembly_id):
        return f'{self.get_base_dapp_url()}/client/networknode/monitor/?{self._get_url_params(assembly_id)}'
    def get_network_node_fuel(self, network_node_id: int) -> dict | None:
        return self._messenger.get_network_node_fuel(network_node_id)
    def get_inventory_for_ssu(self, character_id: int, assembly_id: int) -> list[InventoryItem] | None:
        return self._messenger.get_inventory_for_ssu(character_id, assembly_id)
    @Memoize(2)
    def get_my_gates(self) -> dict[int, Gate]:
        return self._messenger.get_my_gates() or {}
    def get_available_gates(self, gate_id: int) -> list[Gate]:
        # ***<module>.SmartAssemblySvc.get_available_gates: Failure: Different control flow
        my_gates = self.get_my_gates()
        source_gate = my_gates.get(gate_id, None)
        if not source_gate:
            return []
        else:
            max_distance = get_smart_gate_attributes(source_gate.type_id).range
            return [destination_gate if validate_gate_link(source_gate, destination_gate, max_distance) else destination_gate for destination_gate in my_gates.values()]
    @threadutils.threaded
    def deposit_items(self, assembly_id, items, quantity, new_item_id, source_location, source_flag):
        if len(items) == 0:
            return
        else:
            self.sui_wallet.validate_wallet_address()
            success = False
            if type(items) == dict:
                if new_item_id == None:
                    item_ids = 1
                for typeid, qty in items.items():
                    inv_items = []
                    inv_items.append(InventoryItem(new_item_id, typeid, qty))
            else:
                item_ids = [item[ixItemID] for item in items]
                inv_items = list(map(InventoryItem.from_db_item, items))
            if len(inv_items) == 1:
                if quantity is not None:
                    inv_items[0].quantity = quantity
                if new_item_id is not None:
                    inv_items[0].item_id = new_item_id
                    item_ids[0] = new_item_id
            print(item_ids)
            if not item_ids:
                return

            else:
                print("HERE WE GO")
                self.on_deposit_items_started(assembly_id, inv_items)
                try:
                    transaction = self._remote_service.deposit_items(assembly_id, list(map(InventoryItem.to_jsonable, inv_items)), source_location, source_flag)
                    print(f"Transaction attempt: {transaction}")
                    signature = self.sui_wallet.sign_transaction(transaction['transaction_data'])
                    print(signature)
                    success = self._remote_service.deposit_items_signature(assembly_id, transaction['transaction_uuid'], signature)
                    print(success)
                except Exception as e:
                    print(f"NO! {e}")
                    pass
                finally:
                    self.on_deposit_items_completed(assembly_id, success, inv_items)
    @threadutils.threaded
    def withdraw_items(self, destination_id, destination_flag, items, assembly_id):
        if not items:
            return
        else:
            self.sui_wallet.validate_wallet_address()
            if not isinstance(items[0], InventoryItem):
                items = list(map(InventoryItem.from_db_item, items))
            self.on_withdraw_items_started(assembly_id, items)
            success = False
            try:
                transaction = self._remote_service.withdraw_items(assembly_id, [item.to_jsonable() for item in items], destination_id, destination_flag)
                signature = self.sui_wallet.sign_transaction(transaction['transaction_data'])
                success = self._remote_service.withdraw_items_signature(assembly_id, transaction['transaction_uuid'], signature)
            except:
                pass
            finally:
                self.on_withdraw_items_completed(assembly_id, success, items)
    @threadutils.threaded
    def withdraw_item_types(self, assembly_id, item_types: dict[int], dst_id: int, dst_flag: int | None):
        if not item_types:
            return
        else:
            self.sui_wallet.validate_wallet_address()
            self.on_withdraw_item_types_started(assembly_id, item_types)
            success = False
            try:
                transaction = self._remote_service.withdraw_item_types(assembly_id, item_types, dst_id, dst_flag)
                signature = self.sui_wallet.sign_transaction(transaction['transaction_data'])
                success = self._remote_service.withdraw_item_types_signature(assembly_id, transaction['transaction_uuid'], signature)
            except:
                pass
            finally:
                self.on_withdraw_item_types_completed(assembly_id, success, item_types)
    @threadutils.threaded
    def link_gates(self, gate_id: int, destination_gate_id: int):
        if not gate_id or not destination_gate_id:
            return None
        else:
            self.sui_wallet.validate_wallet_address()
            success = False
            try:
                transaction = self._remote_service.link_gates(gate_id, destination_gate_id)
                signature = self.sui_wallet.sign_transaction(transaction['transaction_data'])
                success = self._remote_service.link_gates_signature(gate_id, transaction['transaction_uuid'], signature)
            except:
                pass
            finally:
                if not success:
                    uicore.Message('CustomNotify', {'notify': 'Failed to link gates'})
    @threadutils.threaded
    def unlink_gate(self, gate_id: int):
        if not gate_id:
            return
        else:
            self.sui_wallet.validate_wallet_address()
            success = False
            try:
                transaction = self._remote_service.unlink_gate(gate_id)
                signature = self.sui_wallet.sign_transaction(transaction['transaction_data'])
                success = self._remote_service.unlink_gate_signature(gate_id, transaction['transaction_uuid'], signature)
            except:
                pass
            finally:
                if not success:
                    uicore.Message('CustomNotify', {'notify': 'Failed to unlink gates'})
    @threadutils.threaded
    def gate_jump(self, gate_id):
        # ***<module>.SmartAssemblySvc.gate_jump: Failure: Different control flow
        if not gate_id:
            return
        else:
            self.sui_wallet.validate_wallet_address()
            if not self.is_online(gate_id):
                uicore.Message('CustomNotify', {'notify': 'Gate is offline'})
                return
            try:
                success = False
                try:
                    transaction = self._remote_service.gate_jump(gate_id)
                    signature = self.sui_wallet.sign_transaction(transaction['transaction_data'])
                    success = self._remote_service.gate_jump_signature(gate_id, transaction['transaction_uuid'], signature)
                except:
                    pass
            except:
                pass
            if not success:
                uicore.Message('CustomNotify', {'notify': 'Failed to jump'})
            return success
    def _get_url_params(self, assembly_id):
        return urlencode({'tenant': self._chain_tenant, 'itemId': assembly_id})
def _get_default_base_dapp_url():
    tier = monolithconfig.get_tier()
    if tier == 'live':
        return 'https://dapps.evefrontier.com'
    else:
        return f'https://{tier}.dapps.evefrontier.com'