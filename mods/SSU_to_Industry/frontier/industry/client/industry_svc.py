# Decompiled with PyLingual (https://pylingual.io)
# Internal filename: 'C:\\BuildAgent\\work\\6ec9bf56460fca58\\packages\\frontier\\industry\\client\\industry_svc.py'
# Bytecode version: 3.12.0rc2 (3531)
# Source timestamp: 2026-03-17 10:26:08 UTC (1773743168)

import logging
import typing as t
import uthread2
from carbon.common.script.sys.service import Service
from eve.client.script.remote.michelle import Michelle
from frontier.hud.bracket.key import BallKey
from frontier.hud.service import FrontierHudService
from frontier.industry.client.facility_instance import IndustryFacilityInstance
from frontier.industry.client.mock_listener import IndustryMockListener
from frontier.industry.client.proto_listener import IndustryListener
from frontier.industry.client.qa_tools import is_using_mock
from frontier.industry.client.utility import prompt_error_message
from frontier.industry.common.errors import ErrorHeaders, ErrorReason, IndustryError, IndustryInventoryErrors
from frontier.industry.common.model import FacilityBlueprint, ProductionState
from frontier.industry.common.utility import is_industry_facility
from publicGateway.publicGatewaySvc import PublicGatewaySvc
from frontier.smart_assemblies.client.smart_assembly_svc import SmartAssemblySvc
from frontier.web3.client.sui_wallet_service import SuiWalletService
logger = logging.getLogger('industry')
class IndustryService(Service):
    pass
    __guid__ = 'svc.industry'
    __servicename__ = 'IndustryService'
    __displayname__ = 'Industry Client Service'
    __machoresolve__ = 'location'
    __notifyevents__ = ['OnSessionChanged']
    michelle: Michelle
    public_gateway: PublicGatewaySvc
    hud_service: FrontierHudService
    _remote_service = None
    _listener: IndustryListener | IndustryMockListener | None = None
    _facilities: t.Dict[int, IndustryFacilityInstance] = {}
    sui_wallet: SuiWalletService
    def Run(self, *args):
        Service.Run(self, *args)
        self._remote_service = sm.RemoteSvc('industry')
        self._listener = IndustryListener(self.public_gateway, on_input_items_changed=self._on_input_items_changed, on_output_items_changed=self._on_output_items_changed, on_production_changed=self._on_production_changed)
        self.hud_service.get_selection_state().on_selected_changed.connect(self._on_selection_state_changed)
        sm.GetService('smartAssemblySvc').state_changed_signal.connect(self._on_state_changed)
    def OnSessionChanged(self, is_remote, session, change):
        if 'solarsystemid2' in change or 'charid' in change:
            self._facilities.clear()
        if 'userid' in change and is_using_mock():
                self.qa_use_mock(True)
    def _on_selection_state_changed(self, selection_state):
        if not isinstance(selection_state.selected, BallKey):
            return
        else:
            cr_data = self.michelle.GetCrData(selection_state.selected.ball_id)
            if not cr_data or cr_data.ownerID!= session.charid or (not is_industry_facility(cr_data.typeID)):
                return None
            else:
                if cr_data.itemID in self._facilities and self._facilities[cr_data.itemID].details_fetched:
                    return
                else:
                    self.get_facility(cr_data.itemID, cr_data.typeID)
    def get_facility(self, facility_id: int, facility_type_id: int) -> IndustryFacilityInstance:
        logger.info(f'get_facility facility_id={facility_id} facility_type_id={facility_type_id}')
        if facility_id not in self._facilities:
            self._facilities[facility_id] = IndustryFacilityInstance(facility_id, facility_type_id)
        facility = self._facilities[facility_id]
        if facility.should_refresh():
            facility.set_details_state(loading=True, error=False)
            uthread2.start_tasklet(self._request_facility_details, facility_id)
        return facility
    def load_blueprint(self, facility_id: int, blueprint_id: int):
        logger.info(f'load_blueprint facility_id={facility_id} blueprint_id={blueprint_id}')
        if not self._validate_facility(facility_id, ErrorHeaders.LOAD):
            return
        else:
            facility = self._facilities[facility_id]
            if facility.requesting:
                logger.warning(f'load_blueprint: Request already in progress for facility_id={facility_id}')
                return
            else:
                facility.set_requesting(True)
                try:
                    blueprint_info = self._remote_service.load_blueprint(facility_id, blueprint_id)
                    self._on_blueprint_changed(facility_id, blueprint_info)
                except IndustryError as e:
                    prompt_error_message(e.msg, ErrorHeaders.LOAD)
                finally:
                    facility.set_requesting(False)
    def start_production(self, facility_id: int):
        logger.info(f'start_production facility_id={facility_id}')
        if not self._validate_facility(facility_id, ErrorHeaders.START):
            return
        else:
            facility = self._facilities[facility_id]
            if facility.requesting:
                logger.warning(f'start_production: Request already in progress for facility_id={facility_id}')
                return
            else:
                blueprint = facility.blueprint
                facility.set_requesting(True)
                try:
                    self._remote_service.start_production(facility_id, blueprint.blueprint_id, blueprint.content_hash)
                    facility.update_production_state(ProductionState.RUNNING)
                    sm.ScatterEvent('OnIndustryProductionStarted', facility_id, blueprint)
                except IndustryError as e:
                    prompt_error_message(e.msg, ErrorHeaders.START)
                finally:
                    facility.set_requesting(False)
    def discontinue_production(self, facility_id: int):
        logger.info(f'discontinue_production facility_id={facility_id}')
        if not self._validate_facility(facility_id):
            return
        else:
            facility = self._facilities[facility_id]
            if facility.requesting:
                logger.warning(f'discontinue_production: Request already in progress for facility_id={facility_id}')
                return
            else:
                facility.set_requesting(True)
                try:
                    self._remote_service.discontinue_production(facility_id)
                    facility.update_production_state(ProductionState.DISCONTINUING)
                except IndustryError as e:
                    prompt_error_message(e.msg, ErrorHeaders.DISCONTINUE)
                finally:
                    facility.set_requesting(False)
    def deposit_input_items(self, facility_id: int, items: t.Dict[int, t.Optional[int]], origin_facility):
        try:
            logger.info(f'deposit_input_items facility_id={facility_id} items={items}')
            print(f'!!!deposit_input_items facility_id={facility_id} items={items} inventory flag is {origin_facility}')
            if hasattr(origin_facility,"locationFlag"):
                print(f"yolo inventory is this {origin_facility}")
            else:
                deposited_items, jettisoned_items = self._remote_service.deposit_input_items(facility_id, items)
                if jettisoned_items:
                    prompt_error_message(IndustryInventoryErrors.JETTISONED, ErrorHeaders.DEPOSIT)
        except IndustryError as e:
            prompt_error_message(e.msg, ErrorHeaders.DEPOSIT)

    def withdraw_input_items(self, facility_id: int, facility_flag: int, items: t.Dict[int, int], inventory_id: int, inventory):
        # irreducible cflow, using cdg fallback
        # ***<module>.IndustryService.withdraw_input_items: Failure: Compilation Error
        try:
            itemTypeID = 0
            logger.info(f'withdraw_input_items facility_id={facility_id} items={items} inventory flag is {inventory}')
            if not self._validate_facility(facility_id):
                return
            print(f"{inventory.locationFlag} THIS IS LOCATION FLAG: {inventory}")
            # Get the first key-value pair
            for typeid, itemqty in items.items():
                print(f"Key: {typeid}, Value: {itemqty}")
            if inventory.locationFlag == 66:
                sm.GetService('smartAssemblySvc').deposit_items(inventory.smart_storage_controller._structure_item_id, items, itemqty, inventory_id, facility_id, facility_flag)
            else:
                withdrawn_items, jettisoned_items = self._remote_service.withdraw_input_items(facility_id, items, inventory_id, inventory.locationFlag)
                if jettisoned_items:
                    prompt_error_message(IndustryInventoryErrors.JETTISONED, ErrorHeaders.WITHDRAW)
        except IndustryError as e:
            prompt_error_message(e.msg, ErrorHeaders.WITHDRAW)

    def withdraw_output_items(self, facility_id: int, facility_flag: int, items: t.Dict[int, int], inventory_id: int, inventory):
        # irreducible cflow, using cdg fallback
        # ***<module>.IndustryService.withdraw_output_items: Failure: Compilation Error
        try:
            logger.info(f'withdraw_output_items facility_id={facility_id} items={items} inventory flag is {inventory}')
            if not self._validate_facility(facility_id):
                return
            withdrawn_items, jettisoned_items = self._remote_service.withdraw_output_items(facility_id, items, inventory_id, inventory.locationFlag)
            if jettisoned_items:
                prompt_error_message(IndustryInventoryErrors.JETTISONED, ErrorHeaders.WITHDRAW)
        except IndustryError as e:
            prompt_error_message(e.msg, ErrorHeaders.WITHDRAW)
    def qa_clear_cache(self):
        self._facilities.clear()
        if isinstance(self._listener, IndustryMockListener):
            self._remote_service.qa_clear_mock()
    def qa_load_custom_blueprint(self, facility_id: int, blueprint: FacilityBlueprint):
        logger.info(f'qa_load_custom_blueprint facility_id={facility_id} blueprint={blueprint}')
        blueprint_info = self._remote_service.qa_load_custom_blueprint(facility_id, blueprint.to_dict())
        self._on_blueprint_changed(facility_id, blueprint_info)
    def qa_start_production(self, facility_id: int):
        logger.info(f'qa_start_production facility_id={facility_id}')
        self._remote_service.qa_start_production(facility_id, self._facilities[facility_id].blueprint_hash)
    def qa_use_mock(self, mock):
        if mock:
            self._listener = IndustryMockListener(on_input_items_changed=self._on_input_items_changed, on_output_items_changed=self._on_output_items_changed, on_production_changed=self._on_production_changed)
        else:
            self._listener = IndustryListener(self.public_gateway, on_input_items_changed=self._on_input_items_changed, on_output_items_changed=self._on_output_items_changed, on_production_changed=self._on_production_changed)
        self._remote_service.qa_use_mock(mock)
    def _on_blueprint_changed(self, facility_id: int, blueprint: dict):
        logger.info(f'_on_blueprint_changed facility_id={facility_id} blueprint={blueprint}')
        if facility_id not in self._facilities:
            return
        else:
            facility = self._facilities[facility_id]
            facility.update_production({'state': ProductionState.IDLE})
            facility.update_item_stacks(input_items={}, output_items={})
            facility.update_blueprint(blueprint)
    def _on_input_items_changed(self, facility_id: int, items: dict):
        logger.info(f'_on_input_items_changed facility_id={facility_id} items={items}')
        if facility_id not in self._facilities:
            return
        else:
            self._facilities[facility_id].update_item_stacks(input_items=items)
    def _on_output_items_changed(self, facility_id: int, items: dict):
        logger.info(f'_on_output_items_changed facility_id={facility_id} items={items}')
        if facility_id not in self._facilities:
            return
        else:
            self._facilities[facility_id].update_item_stacks(output_items=items)
    def _on_production_changed(self, facility_id: int, production: t.Optional[dict]):
        logger.info(f'_on_production_changed facility_id={facility_id} production={production}')
        if facility_id not in self._facilities:
            return
        else:
            self._facilities[facility_id].update_production(production)
    def _request_facility_details(self, facility_id):
        logger.info(f'_request_facility_details facility_id={facility_id}')
        if facility_id is None:
            return
        else:
            facility = self._facilities.get(facility_id, None)
            if facility is None:
                return
            else:
                is_refreshing = bool(facility.details_fetched)
                facility.set_details_state(loading=True, error=False)
                facility_info = None
                error_message = None
                try:
                    facility_info = self._remote_service.get_facility_details(facility_id)
                except IndustryError as e:
                    if e.msg == ErrorReason.FACILITY_NOT_FOUND:
                        logger.info(f'Facility not found (expected): facility_id={facility_id}')
                        facility_info = {}
                    else:
                        error_message = e.msg
                        logger.warning(f'Error fetching facility details: {e}')
                except Exception as e:
                    error_message = ErrorReason.GENERIC
                    logger.error(f'Exception fetching facility details: {e}')
                facility = self._facilities.get(facility_id, None)
                if facility is None:
                    return
                else:
                    if is_refreshing and bool(not facility_info or error_message):
                        facility.set_details_state(loading=False, error=False)
                        return
                    else:
                        if error_message:
                            prompt_error_message(error_message, ErrorHeaders.DETAILS)
                            facility.set_details_state(loading=False, error=True)
                            logger.info(f'_request_facility_details error facility_id={facility_id}')
                            return
                        else:
                            facility.set_details_state(loading=False, error=False)
                            logger.info(f'_request_facility_details response facility_id={facility_id} facility_info={facility_info}')
                            if facility_info is not None:
                                facility.update_production(facility_info.get('production', None))
                                items = facility_info.get('items', {})
                                facility.update_item_stacks(input_items=items.get('inputs', {}), output_items=items.get('outputs', {}))
                                facility.update_blueprint(facility_info.get('blueprint', None))
    def _validate_facility(self, facility_id, error_header=None):
        facility = self._facilities.get(facility_id, None)
        if facility is None:
            prompt_error_message(ErrorReason.FACILITY_NOT_FOUND, error_header)
            return False
        else:
            return True
    def _on_state_changed(self, assembly_id, state):
        if assembly_id not in self._facilities:
            return
        else:
            self._facilities[assembly_id].on_online_state_changed()