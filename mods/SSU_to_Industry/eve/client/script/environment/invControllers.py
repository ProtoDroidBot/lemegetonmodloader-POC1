# Decompiled with PyLingual (https://pylingual.io)
# Internal filename: 'C:\\BuildAgent\\work\\6ec9bf56460fca58\\eve\\client\\script\\environment\\invControllers.py'
# Bytecode version: 3.12.0rc2 (3531)
# Source timestamp: 2026-03-17 10:25:56 UTC (1773743156)

from brackets.client import get_brackets_repository, BracketState
from frontier.smart_assemblies.common.utils import get_smart_assembly_access_range
from frontier.station.common.inventory.platform import get_platform_count, occupies_platform
import utillib
from brennivin.itertoolsext import Bundle
from eve.common.lib import appConst as const
from eve.common.script.mgt.fighterConst import TUBE_STATE_READY
from eve.common.script.sys import eveCfg, idCheckers
from eve.common.script.sys.eveCfg import InSpace
from eve.common.script.util import inventoryFlagsCommon
from eve.common.script.util.inventoryFlagsCommon import inventoryFlagData
from inventorycommon.util import GetItemVolume, IsFittingFlag, IsFittingModule, IsStructureServiceFlag
from inventoryrestrictions import is_tradable, can_be_added_to_container
from inventoryrestrictions import ItemCannotBeTraded, ItemCannotBeAddedToContainer
from eve.client.script.ui.util import uix
import carbonui.const as uiconst
import log
import localization
import telemetry
import evetypes
import inventorycommon.typeHelpers
import inventorycommon.const as invConst
from inventoryrestrictions import can_be_unfitted, ItemCannotBeUnfitted
from eve.client.script.ui.plex.textures import PLEX_128_GRADIENT_YELLOW
from eve.client.script.ui.util import utilWindows
from spacecomponents.common.componentConst import CARGO_BAY
from spacecomponents.common.data import get_space_component_for_type, type_has_space_component
from spacecomponents.common.helper import HasCargoBayComponent, HasSmartStorageUnitComponent
from carbon.common.script.sys.row import Row
from carbonui.uicore import uicore
from eveexceptions import UserError
from eveservices.menu import GetMenuService
from frontier.hud.bracket.title import get_bracket_title
LOOT_GROUPS = (const.groupWreck, const.groupCargoContainer, const.groupFreightContainer, const.groupSpawnContainer, const.groupSpewContainer, const.groupDeadspaceOverseersBelongings, const.groupMissionContainer, const.groupAutoLooter, const.groupMobileHomes)
LOOT_GROUPS_NOCLOSE = (const.groupAutoLooter, const.groupMobileHomes)
ZERO_CAPACITY = Row(['capacity', 'used'], [0, 0.0])
def GetNameForFlag(flagID):
    return localization.GetByLabel(inventoryFlagData[flagID]['name'])
class BaseInvContainer(object):
    __guid__ = 'invCtrl.BaseInvContainer'
    name = ''
    iconName = 'res:/UI/Texture/Icons/3_64_13.png'
    locationFlag = None
    hasCapacity = False
    oneWay = False
    viewOnly = False
    scope = None
    isLockable = True
    isMovable = True
    filtersEnabled = True
    typeID = None
    acceptsDrops = True
    isCompact = False
    def __init__(self, itemID=None, typeID=None):
        self.itemID = itemID
        self.typeID = typeID
        self.invID = (self.__class__.__name__, itemID)
        self.ballID = None
        if InSpace():
            self.ballID = sm.GetService('michelle').GetBallID(self.itemID, TraceBack=False)
    def GetInvID(self):
        return self.invID
    def GetInventoryLocationID(self):
        inventoryLocationID, _ = self.invID
        return inventoryLocationID
    def GetName(self):
        return self.name
    def GetNameWithLocation(self):
        return localization.GetByLabel('UI/Inventory/BayAndLocationName', bayName=self.GetName(), locationName=cfg.evelocations.Get(self.itemID).name)
    def GetIconName(self):
        return self.iconName
    @telemetry.ZONE_METHOD
    def GetItems(self):
        try:
            return list(filter(self.IsItemHere, self._GetItems()))
        except RuntimeError as e:
            if e.args[0] == 'CharacterNotAtStation':
                return []
            else:
                raise
    @telemetry.ZONE_METHOD
    def _GetItems(self):
        if self.locationFlag:
            result = self._GetInvCacheContainer().List(flag=self.locationFlag)
            return self._GetInvCacheContainer().List(flag=self.locationFlag)
        else:
            return self._GetInvCacheContainer().List()
    def GetItemsByType(self, typeID):
        return [item for item in self.GetItems() if item.typeID == typeID]
    def GetItem(self, itemID):
        for item in self.GetItems():
            if item.itemID == itemID:
                return item
        return
    def GetScope(self):
        return self.scope
    def GetMenu(self):
        return GetMenuService().InvItemMenu(self.GetInventoryItem())
    def _GetInvCacheContainer(self):
        invCache = sm.GetService('invCache')
        return invCache.GetInventoryFromId(self.itemID)
    def GetInventoryItem(self):
        item = sm.GetService('invCache').GetParentItemFromItemID(self.itemID)
        if not item:
            item = self._GetInvCacheContainer().GetItem()
        return item
    def GetTypeID(self):
        if self.typeID is not None:
            return self.typeID
        else:
            if self.ballID is not None:
                bp = sm.GetService('michelle').GetBallpark()
                if bp is not None:
                    crData = bp.GetCrData(self.ballID)
                    if crData:
                        self.typeID = crData.typeID
                        return self.typeID
            self.typeID = self.GetInventoryItem().typeID
            return self.typeID
    def IsItemHere(self, item):
        raise NotImplementedError('IsItemHere must be implemented')
    def IsMovable(self):
        return self.isMovable
    def IsItemHereVolume(self, item):
        return self.IsItemHere(item)
    def IsInRange(self):
        return True
    def CheckCanQuery(self):
        return True
    def CheckCanTake(self):
        return True
    def IsPrimed(self):
        return sm.GetService('invCache').IsInventoryPrimedAndListed(self.itemID)
    def HasEnoughSpaceForItems(self, items):
        volume = 0.0
        for item in items:
            volume += GetItemVolume(item)
        cap = self.GetCapacity()
        remainingVolume = cap.capacity - cap.used
        return volume <= remainingVolume
    def DoesAcceptItem(self, item):
        if self.locationFlag:
            if inventoryFlagsCommon.ShouldAllowAdd(self.locationFlag, item.categoryID, item.groupID, item.typeID) is not None:
                return False
        return True
    def OnItemsViewed(self):
        return
    def AddFightersFromTube(self, fighters):
        fighterSvc = sm.GetService('fighters')
        for fighter in fighters:
            if fighter.squadronState == TUBE_STATE_READY:
                fighterSvc.UnloadTubeToFighterBay(fighter.tubeFlagID)
    def __AddItem(self, item, sourceLocationID, quantity):
        itemID = item.itemID
        dogmaLocation = sm.GetService('clientDogmaIM').GetDogmaLocation()
        stateMgr = sm.StartService('godma').GetStateManager()
        dividing = quantity!= item.stacksize
        if self.IsItemHere(item):
            if not dividing:
                return
        else:
            if not self.CheckAndConfirmOneWayMove():
                return
        if self.locationFlag:
            item = stateMgr.GetItem(itemID)
            if item and self.locationFlag in inventoryFlagData and IsFittingFlag(item.flagID):
                if item.categoryID == const.categoryCharge:
                    return dogmaLocation.UnloadAmmoToContainer(item.locationID, item, (self.itemID, self.GetOwnerID(), self.locationFlag), quantity)
                else:
                    if IsFittingModule(item.categoryID):
                        return dogmaLocation.UnloadModuleToContainer(item.locationID, item.itemID, self._GetContainerArgs(), self.locationFlag)
            else:
                return self._GetInvCacheContainer().Add(itemID, sourceLocationID, qty=quantity, flag=self.locationFlag)
        else:
            return self._GetInvCacheContainer().Add(itemID, sourceLocationID, qty=quantity, flag=self.locationFlag)
    def _AddItem(self, item, forceQuantity=False, sourceLocation=None):
        # irreducible cflow, using cdg fallback
        # ***<module>.BaseInvContainer._AddItem: Failure: Compilation Error
        locationID = session.locationid
        maxQty = None
        for i in range(2):
            try:
                if locationID!= session.locationid:
                    return
                else:
                    itemQuantity = item.stacksize
                    if itemQuantity == 1:
                        quantity = 1
                    elif uicore.uilib.Key(uiconst.VK_SHIFT) or forceQuantity:
                        quantity = self.PromptUserForQuantity(item, itemQuantity, sourceLocation)
                    else:
                        quantity = itemQuantity
                    if not item.itemID or not quantity:
                        return
                    if locationID!= session.locationid:
                        return
                    if sourceLocation is None:
                        sourceLocation = item.locationID
                    if self._ExternalChainWithdrawal(quantity if quantity < itemQuantity else None, [item], sourceLocation):
                        return

                    return self.__AddItem(item, sourceLocation, quantity)
            except UserError as what:
                if what.args[0] in ['NotEnoughCargoSpace', 'NotEnoughCargoSpaceOverload', 'NotEnoughDroneBaySpace', 'NotEnoughDroneBaySpaceOverload', 'NoSpaceForThat', 'NoSpaceForThatOverload', 'NotEnoughChargeSpace', 'NotEnoughSpecialBaySpace', 'NotEnoughSpecialBaySpaceOverload', 'NotEnoughSpace', 'NotEnoughFighterBaySpace']:
                    try:
                        cap = self.GetCapacity()
                    except UserError:
                        raise what
                    free = cap.capacity - cap.used
                    if free < 0:
                        raise
                    if item.typeID == const.typePlasticWrap:
                        volume = sm.GetService('invCache').GetInventoryFromId(item.itemID).GetCapacity().used
                    else:
                        volume = GetItemVolume(item, 1)
                    maxQty = self._CalculateMaxQuantity(free, item, volume)
                    if maxQty <= 0:
                        if volume < 0.01:
                            req = 0.01
                        else:
                            req = volume
                        eve.Message('NotEnoughCargoSpaceFor1Unit', {'type': item.typeID, 'free': free, 'required': req})
                        return
                    if self._DBLessLimitationsCheck(what.args[0], item):
                        pass
                    return
                elif msgKey == 'CannotAddToQtyLimit':
                    maxQty = what.dict.get('maxToAdd', None)
                    if maxQty <= 0:
                        raise
                    forceQuantity = 1
                else:
                    raise
    def _CalculateMaxQuantity(self, free, item, volume):
        numberOfItemsWeHaveRoomFor = int(round(free / (volume or 1), 7))
        maxQty = min(item.stacksize, numberOfItemsWeHaveRoomFor)
        return maxQty
    def prompt_user_for_quantity_sd_resource(self, itemvolume, itemQuantity):
        if self.hasCapacity:
            cap = self.GetCapacity()
            capacity = cap.capacity - cap.used
            maxQty = capacity / itemvolume + 1e-07
            maxQty = min(itemQuantity, int(maxQty))
        else:
            maxQty = itemQuantity
        if maxQty == itemQuantity:
            errmsg = localization.GetByLabel('UI/Common/NoMoreUnits')
        else:
            errmsg = localization.GetByLabel('UI/Common/NoRoomForMore')
        ret = uix.QtyPopup(int(maxQty), 0, int(maxQty), errmsg)
        if ret is not None:
            return ret['qty']
        else:
            return None
    def PromptUserForQuantity(self, item, itemQuantity, sourceLocation=None):
        if self.locationFlag is not None and item.flagID!= self.locationFlag or item.locationID!= getattr(self._GetInvCacheContainer(), 'itemID', None):
            if self.hasCapacity:
                cap = self.GetCapacity()
                capacity = cap.capacity - cap.used
                itemvolume = GetItemVolume(item, 1) or 1
                maxQty = capacity / itemvolume + 1e-07
                maxQty = min(itemQuantity, int(maxQty))
            else:
                maxQty = itemQuantity
            if maxQty == itemQuantity:
                errmsg = localization.GetByLabel('UI/Common/NoMoreUnits')
            else:
                errmsg = localization.GetByLabel('UI/Common/NoRoomForMore')
            ret = uix.QtyPopup(int(maxQty), 0, int(maxQty), errmsg)
        else:
            ret = uix.QtyPopup(itemQuantity, 1, 1, None, localization.GetByLabel('UI/Inventory/ItemActions/DivideItemStack'))
        if item.locationID!= session.stationid and (not sm.GetService('invCache').IsInventoryPrimedAndListed(item.locationID)):
            log.LogError('Item disappeared before we could add it', item)
            return
        else:
            if ret is not None:
                return ret['qty']
            else:
                return None
    def MultiMerge(self, data, mergeSourceID):
        # irreducible cflow, using cdg fallback
        # ***<module>.BaseInvContainer.MultiMerge: Failure: Compilation Error
        mergeItem = data[0][3]
        if (mergeItem.locationID!= self.itemID or mergeItem.flagID!= self.locationFlag) and (not self.CheckAndConfirmOneWayMove()):
            return
        try:
            self._GetInvCacheContainer().MultiMerge([(d[0], d[1], d[2]) for d in data], mergeSourceID)
            return True
        except UserError as what:
            if len(data) == 1 and what.args[0] in ['NotEnoughCargoSpace', 'NotEnoughCargoSpaceOverload', 'NotEnoughDroneBaySpace', 'NotEnoughDroneBaySpaceOverload', 'NoSpaceForThat', 'NoSpaceForThatOverload', 'NotEnoughChargeSpace', 'NotEnoughSpecialBaySpace', 'NotEnoughFighterBaySpace']:
                cap = self.GetCapacity()
                free = cap.capacity - cap.used
                if free < 0:
                    raise
                item = data[0][3]
                if item.typeID == const.typePlasticWrap:
                    volume = sm.GetService('invCache').GetInventoryFromId(item.itemID).GetCapacity().used
                else:
                    volume = GetItemVolume(item, 1)
                maxQty = self._CalculateMaxQuantity(free, item, volume)
                if maxQty <= 0:
                    if volume < 0.01:
                        req = 0.01
                    else:
                        req = volume
                    eve.Message('NotEnoughCargoSpaceFor1Unit', {'type': item.typeID, 'free': free, 'required': req})
                    return
                if self._DBLessLimitationsCheck(what.args[0], item):
                    return
                if maxQty == item.stacksize:
                    errmsg = localization.GetByLabel('UI/Common/NoMoreUnits')
                else:
                    errmsg = localization.GetByLabel('UI/Common/NoRoomForMore')
                ret = uix.QtyPopup(int(maxQty), 0, int(maxQty), errmsg)
                if ret is None:
                    quantity = None
                else:
                    quantity = ret['qty']
                if quantity:
                    self._GetInvCacheContainer().MultiMerge([(data[0][0], data[0][1], quantity)], mergeSourceID)
                    return True
            else:
                raise
    def StackAll(self, securityCode=None):
        # irreducible cflow, using cdg fallback
        # ***<module>.BaseInvContainer.StackAll: Failure: Compilation Error
        if not self.CheckAndConfirmOneWayMove():
            return
        else:
            if self.locationFlag:
                retval = self._GetInvCacheContainer().StackAll(self.locationFlag)
                return retval
        try:
            if securityCode is None:
                retval = self._GetInvCacheContainer().StackAll()
            else:
                retval = self._GetInvCacheContainer().StackAll(securityCode=securityCode)
                return retval
        except UserError as what:
                if what.args[0] == 'PermissionDenied':
                    if securityCode:
                        caption = localization.GetByLabel('UI/Menusvc/IncorrectPassword')
                        label = localization.GetByLabel('UI/Menusvc/PleaseTryEnteringPasswordAgain')
                    else:
                        caption = localization.GetByLabel('UI/Menusvc/PasswordRequired')
                        label = localization.GetByLabel('UI/Menusvc/PleaseEnterPassword')
                    passw = utilWindows.NamePopup(caption=caption, label=label, setvalue='', icon=(-1), modal=1, btns=None, maxLength=50, passwordChar='*')
                    if passw == '':
                        raise UserError('IgnoreToTop')
                    else:
                        retval = self.StackAll(securityCode=passw['name'])
                        return retval
                else:
                    raise
    def _DBLessLimitationsCheck(self, errorName, item):
        return False
    def GetCapacity(self):
        try:
            return self._GetInvCacheContainer().GetCapacity(self.locationFlag)
        except RuntimeError as e:
            if e.args[0] in ['CharacterNotAtStation', 'FakeItemNotFound']:
                return ZERO_CAPACITY
            else:
                raise
    def GetOwnerID(self):
        return self.GetInventoryItem().ownerID
    def _GetContainerArgs(self):
        return (self.itemID,)
    def _ValidateMove(self, items):
        forbiddenTypeIDs = set()
        for item in items:
            typeID = getattr(item, 'typeID', None)
            flagID = getattr(item, 'flagID', None)
            if all([typeID, flagID]) and flagID in invConst.fittingFlags and (not can_be_unfitted(typeID)):
                        forbiddenTypeIDs.add(typeID)
        if forbiddenTypeIDs:
            raise ItemCannotBeUnfitted(type_ids=forbiddenTypeIDs)
    def OnDropData(self, nodes):
        if not self.acceptsDrops:
            return
        else:
            items = []
            smart_storage_items = []
            fighters = []
            lockedNodes = [node for node in nodes if getattr(node, 'locked', False)]
            if lockedNodes:
                for node in lockedNodes:
                    nodes.remove(node)
                uicore.Message('SomeLockedItemsNotMoved')
            for node in nodes:
                if self.CheckAndHandlePlexVaultItem(node):
                    continue
                else:
                    if getattr(node, '__guid__', None) == 'SDresourceItem':
                        self.sd_withdraw_resource(node)
                        return
                    else:
                        if getattr(node, 'on_add_item', None):
                            node.on_add_item(self)
                            return
                        else:
                            if type(node.item).__name__ == 'StorageInventoryItem':
                                smart_storage_items.append(node)
                            if getattr(node, '__guid__', None) in ['xtriui.ShipUIModule', 'xtriui.InvItem', 'listentry.InvItem', 'xtriui.FittingSlot']:
                                items.append(node.item)
                            from eve.client.script.ui.shared.inventory.treeData import TreeDataInv
                            if isinstance(node, TreeDataInv) and node.invController.IsMovable():
                                    items.append(node.invController.GetInventoryItem())
                            if getattr(node, '__guid__', None) == 'uicls.FightersHealthGauge':
                                fighters.append(node)
            self._ValidateMove(items)
            if fighters:
                return self.AddFightersFromTube(fighters)
            else:
                if smart_storage_items:
                    return self.sd_withdraw_item(smart_storage_items)
                else:
                    return self.AddItems(items)
    def get_remaining_capacity(self):
        cap = self.GetCapacity()
        return max(0, cap.capacity - cap.used)
    def get_max_quantity(self, itemvolume, itemQuantity):
        cap = self.GetCapacity()
        capacity = cap.capacity - cap.used
        maxQty = capacity / itemvolume + 1e-07
        return min(itemQuantity, int(maxQty))
    def sd_withdraw_resource(self, node):
        if not sm.GetService('smartAssemblySvc').is_operational(node.assembly_id):
            return
        else:
            itemvolume = float(evetypes.GetVolume(typeID=node.type_id))
            max_quantity = self.get_max_quantity(itemvolume, node.quantity) if self.hasCapacity else node.quantity
            if max_quantity < 1:
                cap = self.GetCapacity()
                raise UserError('NotEnoughCargoSpace', {'available': cap.capacity - cap.used, 'volume': node.quantity * evetypes.GetVolume(typeID=node.type_id)})
            else:
                if max_quantity < node.quantity:
                    itemvolume = float(evetypes.GetVolume(typeID=node.type_id))
                    quantity = self.prompt_user_for_quantity_sd_resource(itemvolume, node.quantity)
                else:
                    if node.quantity == 1:
                        quantity = node.quantity
                    else:
                        if uicore.uilib.Key(uiconst.VK_SHIFT):
                            itemvolume = float(evetypes.GetVolume(typeID=node.type_id))
                            quantity = self.prompt_user_for_quantity_sd_resource(itemvolume, node.quantity)
                        else:
                            quantity = node.quantity
                if quantity:
                    sm.GetService('smartAssemblySvc').withdraw_item_types(node.assembly_id, {node.type_id: quantity}, self.itemID, self.locationFlag)
    def sd_withdraw_item(self, nodes):
        items = [node.item for node in nodes]
        if not sm.GetService('smartAssemblySvc').is_operational(items[0].locationID):
            return
        else:
            items_quantity = []
            max_quantity = []
            for item in items:
                items_quantity.append(item.quantity)
                itemvolume = float(GetItemVolume(item) / item.quantity)
                max_quantity.append(self.get_max_quantity(itemvolume, item.quantity))
            items_quantity = sum(items_quantity)
            if self.hasCapacity:
                max_quantity = sum(max_quantity)
            else:
                max_quantity = items_quantity
            if max_quantity < 1:
                cap = self.GetCapacity()
                total_volume = sum([GetItemVolume(item) for item in items])
                raise UserError('NotEnoughCargoSpace', {'available': cap.capacity - cap.used, 'volume': total_volume})
            else:
                if max_quantity < items_quantity or (uicore.uilib.Key(uiconst.VK_SHIFT) and len(items) == 1):
                    itemvolume = float(GetItemVolume(items[0]) / items[0].quantity)
                    quantity = self.prompt_user_for_quantity_sd_resource(itemvolume, items[0].quantity)
                    if not quantity:
                        return
                    else:
                        item = items[0]
                        item.quantity = quantity
                        items = [item]
                item_type_ids = [item.typeID for item in items]
                sm.GetService('smartAssemblySvc').withdraw_items(self.itemID, self.locationFlag, items, items[0].locationID)
    def CheckAndHandlePlexVaultItem(self, node):
        isPlexVaultItem = hasattr(node, 'WithdrawPlex') and callable(node.WithdrawPlex)
        if not isPlexVaultItem:
            return False
        else:
            if not self.DoesAcceptItem(node.item):
                return False
            else:
                node.WithdrawPlex(self)
                return True
    def _EnoughSpaceForExternalChainWithdrawal(self, quantity, items):
        if len(items) == 1 and (quantity or 0) > 0:
            dst_capacity = self.GetCapacity()
            has_enough_space = dst_capacity.used + quantity * evetypes.GetVolume(items[0].typeID) <= dst_capacity.capacity
            return has_enough_space
        else:
            has_enough_space = self.HasEnoughSpaceForItems(items)
            return has_enough_space
    def _ExternalChainWithdrawal(self, quantity, items, sourceId):
        bp = sm.GetService('michelle').GetBallpark()
        if bp is None:
            return False
        else:
            ball_id = bp.GetBallID(sourceId)
            if not ball_id:
                return False
            else:
                ball = bp.GetBall(ball_id)
                if not ball:
                    return False
                else:
                    cr_data = bp.GetCrData(ball_id)
                    if cr_data is None:
                        return False
                    else:
                        if not HasSmartStorageUnitComponent(ball.typeID):
                            return False
                        else:
                            if not sm.GetService('smartAssemblySvc').is_online(sourceId):
                                return True
                            else:
                                if not self._EnoughSpaceForExternalChainWithdrawal(quantity, items):
                                    self._not_enough_space_notification()
                                    return True
                                else:
                                    max_dist = get_smart_assembly_access_range(cr_data.typeID)
                                    if ball.surfaceDist > max_dist:
                                        self._out_of_range_notification(max_dist)
                                        return True
                                    else:
                                        is_owner = session.charid == cr_data.ownerID
                                        sm.GetService('smartAssemblySvc').withdraw_items(sourceId, self.locationFlag, items, self.itemID)
                                        return True
    def _not_enough_space_notification(self):
        cap = self.GetCapacity()
        free = cap.capacity - cap.used
        eve.Message('NotEnoughSpaceWithdrawSmartDeployable', {'free': free})
    def _out_of_range_notification(self, max_dist):
        eve.Message('SmartDeployableOutOfRange', {'distance': max_dist})
    def AddItems(self, items):
        if len(items) > 1:
            items = list(filter(self.DoesAcceptItem, items))
        if not items:
            return
        else:
            sourceLocation = items[0].locationID
            if self.itemID!= sourceLocation and (not sm.GetService('crimewatchSvc').CheckCanTakeItems(sourceLocation)):
                sm.GetService('crimewatchSvc').SafetyActivated(const.shipSafetyLevelPartial)
                container = sm.GetService('invCache').GetInventoryFromId(sourceLocation)
                raise UserError('LootTheftDeniedSafetyPreventsSuspect', {'containerName': (const.UE_TYPEID, container.typeID)})
            else:
                if not sm.GetService('invCache').AcceptPossibleRemovalTax(items):
                    return
                else:
                    if len(items) == 1:
                        item = items[0]
                        if hasattr(item, 'flagID') and IsFittingFlag(item.flagID) and (item.locationID == eveCfg.GetActiveShip()):
                            if not self.CheckAndConfirmOneWayMove():
                                return
                            else:
                                itemKey = item.itemID
                                locationID = item.locationID
                                dogmaLocation = sm.GetService('clientDogmaIM').GetDogmaLocation()
                                containerArgs = self._GetContainerArgs()
                                if IsFittingModule(item.categoryID):
                                    return dogmaLocation.UnloadModuleToContainer(locationID, itemKey, containerArgs, self.locationFlag)
                                else:
                                    if item.categoryID == const.categoryCharge:
                                        ownerID = session.charid if self.locationFlag == const.flagHangar else self.GetOwnerID()
                                        return dogmaLocation.UnloadAmmoToContainer(locationID, item, (containerArgs[0], ownerID, self.locationFlag))
                                    else:
                                        if IsStructureServiceFlag(item.flagID):
                                            sm.GetService('structureControl').CheckCanDisableServiceModule(item)
                                            from eve.client.script.util.eveMisc import GetRemoveServiceConfirmationQuestion
                                            questionPath, params = GetRemoveServiceConfirmationQuestion(item.typeID)
                                            ret = eve.Message(questionPath, params=params, buttons=uiconst.YESNO)
                                            if ret!= uiconst.ID_YES:
                                                return
                        ret = self._AddItem(item, sourceLocation=sourceLocation)
                        if ret:
                            sm.ScatterEvent('OnClientEvent_MoveFromCargoToHangar', sourceLocation, self.itemID, self.locationFlag)
                        return ret
                    else:
                        if not self.CheckAndConfirmOneWayMove():
                            return
                        else:
                            items.sort(key=lambda item: evetypes.GetVolume(item.typeID) * item.stacksize)
                            itemIDs = [node.itemID for node in items]
                            dogmaLocation = sm.GetService('clientDogmaIM').GetDogmaLocation()
                            masters = dogmaLocation.GetAllSlaveModulesByMasterModule(sourceLocation)
                            if masters:
                                inBank = 0
                                for itemID in itemIDs:
                                    if dogmaLocation.IsInWeaponBank(sourceLocation, itemID):
                                        inBank = 1
                                        break
                                if inBank:
                                    ret = eve.Message('CustomQuestion', {'header': localization.GetByLabel('UI/Common/Confirm'), 'question': localization.GetByLabel('UI/Inventory/WeaponLinkUnfitMany')}, uiconst.YESNO)
                                    if ret!= uiconst.ID_YES:
                                        return
                            for item in items:
                                if item.categoryID == const.categoryCharge:
                                    if IsFittingFlag(item.flagID):
                                        log.LogInfo('A module with a db item charge dropped from ship fitting into some container. Cannot use multimove, must remove charge first.')
                                        ret = [self._AddItem(item)]
                                        items.remove(item)
                                        for item in items:
                                            ret.append(self._AddItem(item))
                                        return ret
                            if self._ExternalChainWithdrawal(None, items, sourceLocation):
                                return
                            else:
                                invCacheCont = self._GetInvCacheContainer()
                                if self.locationFlag:
                                    ret = invCacheCont.MultiAdd(itemIDs, sourceLocation, flag=self.locationFlag)
                                else:
                                    ret = invCacheCont.MultiAdd(itemIDs, sourceLocation, flag=const.flagNone)
                                if ret:
                                    sm.ScatterEvent('OnClientEvent_MoveFromCargoToHangar', sourceLocation, self.itemID, self.locationFlag)
                                return ret
    def SetCompactMode(self, isCompact):
        self.isCompact = isCompact
    def CheckAndConfirmOneWayMove(self):
        if self.oneWay:
            return self.PromptOneWayMove()
        else:
            return True
    def PromptOneWayMove(self):
        return uicore.Message('ConfirmOneWayItemMove', {}, uiconst.OKCANCEL) == uiconst.ID_OK
    def GetSpecialActions(self):
        return []
class ShipCargo(BaseInvContainer):
    pass
    __guid__ = 'invCtrl.ShipCargo'
    hasCapacity = True
    locationFlag = const.flagCargo
    def __init__(self, itemID=None, typeID=None):
        self.itemID = itemID or eveCfg.GetActiveShip()
        super(ShipCargo, self).__init__(self.itemID, typeID)
        self.name = localization.GetByLabel('UI/Common/CargoHold')
    def GetMenu(self):
        if self.itemID == session.shipid and InSpace():
            return GetMenuService().GetMenuFromItemIDTypeID(self.itemID, self.GetTypeID())
        else:
            return BaseInvContainer.GetMenu(self)
    def GetIconName(self, highliteIfActive=False):
        if highliteIfActive and self.itemID == eveCfg.GetActiveShip():
            return 'res:/UI/Texture/Icons/1337_64_11.png'
        else:
            return 'res:/ui/Texture/WindowIcons/ships.png'
    def GetScope(self):
        if self.itemID == eveCfg.GetActiveShip():
            return uiconst.SCOPE_INGAME
        else:
            return uiconst.SCOPE_DOCKED
    def GetName(self):
        return cfg.evelocations.Get(self.itemID).name
    def _GetInvCacheContainer(self):
        return sm.GetService('invCache').GetInventoryFromId(self.itemID, locationID=session.stationid)
    def IsItemHere(self, item):
        return item.locationID == self.itemID and item.flagID == self.locationFlag
class BaseShipBay(BaseInvContainer):
    __guid__ = 'invCtrl.BaseShipBay'
    hasCapacity = True
    isMovable = False
    def __init__(self, itemID=None, typeID=None):
        self.itemID = itemID or eveCfg.GetActiveShip()
        super(BaseShipBay, self).__init__(self.itemID, typeID)
    def IsItemHere(self, item):
        return item.locationID == self.itemID and item.flagID == self.locationFlag
    def GetName(self):
        return GetNameForFlag(self.locationFlag)
    def GetScope(self):
        if self.itemID == eveCfg.GetActiveShip():
            return uiconst.SCOPE_INGAME
        else:
            return uiconst.SCOPE_DOCKED
class ShipDroneBay(BaseShipBay):
    __guid__ = 'invCtrl.ShipDroneBay'
    iconName = 'res:/UI/Texture/WindowIcons/dronebay.png'
    locationFlag = const.flagDroneBay
    hasCapacity = True
    scope = uiconst.SCOPE_DOCKED
class ShipFighterBay(BaseShipBay):
    __guid__ = 'invCtrl.ShipFighterBay'
    iconName = 'res:/UI/Texture/WindowIcons/dronebay.png'
    locationFlag = const.flagFighterBay
    hasCapacity = True
    scope = uiconst.SCOPE_DOCKED
class ShipFrigateEscapeBay(BaseShipBay):
    __guid__ = 'invCtrl.ShipFrigateEscapeBay'
    iconName = 'res:/UI/Texture/WindowIcons/shiphangar.png'
    locationFlag = const.flagFrigateEscapeBay
    scope = uiconst.SCOPE_DOCKED
class ShipFuelBay(BaseShipBay):
    __guid__ = 'invCtrl.ShipFuelBay'
    locationFlag = const.flagSpecializedFuelBay
    iconName = 'res:/UI/Texture/WindowIcons/fuelbay.png'
class ShipGeneralMiningHold(BaseShipBay):
    __guid__ = 'invCtrl.ShipGeneralMiningHold'
    locationFlag = const.flagGeneralMiningHold
    iconName = 'res:/UI/Texture/WindowIcons/orehold.png'
class ShipAsteroidHold(BaseShipBay):
    __guid__ = 'invCtrl.ShipAsteroidHold'
    locationFlag = const.flagSpecialAsteroidHold
    iconName = 'res:/UI/Texture/WindowIcons/orehold.png'
class ShipIceHold(BaseShipBay):
    __guid__ = 'invCtrl.ShipIceHold'
    locationFlag = const.flagSpecializedIceHold
    iconName = 'res:/UI/Texture/WindowIcons/icehold.png'
class ShipGasHold(BaseShipBay):
    __guid__ = 'invCtrl.ShipGasHold'
    locationFlag = const.flagSpecializedGasHold
    iconName = 'res:/UI/Texture/WindowIcons/gashold.png'
class ShipMineralHold(BaseShipBay):
    __guid__ = 'invCtrl.ShipMineralHold'
    locationFlag = const.flagSpecializedMineralHold
    iconName = 'res:/UI/Texture/WindowIcons/mineralhold.png'
class ShipSalvageHold(BaseShipBay):
    __guid__ = 'invCtrl.ShipSalvageHold'
    locationFlag = const.flagSpecializedSalvageHold
    iconName = 'res:/UI/Texture/WindowIcons/salvagehold.png'
class ShipShipHold(BaseShipBay):
    __guid__ = 'invCtrl.ShipShipHold'
    locationFlag = const.flagSpecializedShipHold
    iconName = 'res:/UI/Texture/WindowIcons/shiphangar.png'
class ShipSmallShipHold(BaseShipBay):
    __guid__ = 'invCtrl.ShipSmallShipHold'
    locationFlag = const.flagSpecializedSmallShipHold
    iconName = 'res:/UI/Texture/WindowIcons/shiphangar.png'
class ShipMediumShipHold(BaseShipBay):
    __guid__ = 'invCtrl.ShipMediumShipHold'
    locationFlag = const.flagSpecializedMediumShipHold
    iconName = 'res:/UI/Texture/WindowIcons/shiphangar.png'
class ShipLargeShipHold(BaseShipBay):
    __guid__ = 'invCtrl.ShipLargeShipHold'
    locationFlag = const.flagSpecializedLargeShipHold
    iconName = 'res:/UI/Texture/WindowIcons/shiphangar.png'
class ShipIndustrialShipHold(BaseShipBay):
    __guid__ = 'invCtrl.ShipIndustrialShipHold'
    locationFlag = const.flagSpecializedIndustrialShipHold
    iconName = 'res:/UI/Texture/WindowIcons/shiphangar.png'
class ShipAmmoHold(BaseShipBay):
    __guid__ = 'invCtrl.ShipAmmoHold'
    locationFlag = const.flagSpecializedAmmoHold
    iconName = 'res:/UI/Texture/WindowIcons/itemHangar.png'
class ShipQuafeHold(BaseShipBay):
    __guid__ = 'invCtrl.ShipQuafeHold'
    locationFlag = const.flagQuafeBay
class ShipCorpseHold(BaseShipBay):
    __guid__ = 'invCtrl.ShipCorpseHold'
    locationFlag = const.flagCorpseBay
class ShipBoosterHold(BaseShipBay):
    __guid__ = 'invCtrl.ShipBoosterHold'
    locationFlag = const.flagBoosterBay
class ShipSubsystemHold(BaseShipBay):
    __guid__ = 'invCtrl.ShipSubsystemHold'
    locationFlag = const.flagSubsystemBay
class BaseCorpContainer(BaseInvContainer):
    __guid__ = 'invCtrl.BaseCorpContainer'
    scope = uiconst.SCOPE_DOCKED
    oneWay = True
    iconName = 'res:/UI/Texture/WindowIcons/corporation.png'
    isMovable = False
    def __init__(self, itemID=None, divisionID=0):
        super(BaseCorpContainer, self).__init__(itemID=itemID)
        self.divisionID = self.roles = self.locationFlag = None
        self.SetDivisionID(divisionID)
        if self.roles is not None:
            self.SetAccess()
        self.invID = (self.__class__.__name__, self.itemID, divisionID)
    def GetName(self):
        if self.divisionID is not None:
            divisions = sm.GetService('corp').GetDivisionNames()
            return divisions[self.divisionID + 1]
        else:
            return localization.GetByLabel('UI/Inventory/CorporationHangars')
    def SetDivisionID(self, divisionID):
        self.divisionID = divisionID
        self.locationFlag = const.corpFlagByDivision.get(divisionID)
        if self.locationFlag:
            self.roles = (const.corpHangarQueryRolesByFlag[self.locationFlag], const.corpHangarTakeRolesByFlag[self.locationFlag])
    def _GetInvCacheContainer(self):
        # irreducible cflow, using cdg fallback
        # ***<module>.BaseCorpContainer._GetInvCacheContainer: Failure: Compilation Error
        try:
            officeID = sm.GetService('officeManager').GetCorpOfficeAtLocation().officeID
            if officeID == self.itemID:
                return sm.GetService('invCache').GetInventoryFromId(self.itemID)
        except AttributeError:
                pass
        raise RuntimeError('Invalid inventory window.')
    def IsItemHere(self, item):
        ballpark = sm.GetService('michelle').GetBallpark()
        return item.locationID == self.itemID and (item.ownerID == session.corpid or (ballpark and item.ownerID == ballpark.GetCrData(self.ballID).ownerID)) and (self.locationFlag is None or item.flagID == self.locationFlag) and self.CheckCanQuery()
    def CheckCanQuery(self):
        if self.roles is None:
            return True
        else:
            role = self.roles[0]
            if session.corprole & role == role:
                return True
            else:
                return False
    def CheckCanTake(self):
        if self.roles is None:
            return True
        else:
            role = self.roles[1]
            if session.corprole & role == role:
                return True
            else:
                return False
    def SetAccess(self):
        role = self.roles[1]
        if session.corprole & role == role:
            self.viewOnly = False
        else:
            self.viewOnly = True
    @telemetry.ZONE_METHOD
    def GetItems(self):
        return BaseInvContainer.GetItems(self) if self.CheckCanQuery() else []
class StationCorpHangar(BaseCorpContainer):
    pass
    __guid__ = 'invCtrl.StationCorpHangar'
    hasCapacity = False
    def __init__(self, itemID=None, divisionID=0):
        if itemID is None:
            itemID = sm.GetService('officeManager').GetCorpOfficeAtLocation().officeID
        BaseCorpContainer.__init__(self, itemID, divisionID)
    def GetItems(self):
        office = sm.GetService('officeManager').GetCorpOfficeAtLocation()
        if office is None or office.officeID!= self.itemID:
            return []
        else:
            return BaseCorpContainer.GetItems(self)
    def GetCapacity(self):
        if sm.GetService('officeManager').GetCorpOfficeAtLocation() is None:
            return ZERO_CAPACITY
        else:
            return BaseCorpContainer.GetCapacity(self)
    def GetMenu(self):
        return []
    def IsInRange(self):
        office = sm.GetService('officeManager').GetCorpOfficeAtLocation()
        return office and office.officeID == self.itemID
class StationCorpMember(BaseInvContainer):
    pass
    __guid__ = 'invCtrl.StationCorpMember'
    scope = uiconst.SCOPE_STATION
    oneWay = True
    viewOnly = True
    locationFlag = const.flagHangar
    iconName = 'res:/ui/Texture/WindowIcons/member.png'
    def __init__(self, itemID=None, ownerID=None):
        super(StationCorpMember, self).__init__(itemID=itemID)
        self.ownerID = ownerID
        self.invID = (self.__class__.__name__, itemID, ownerID)
    def GetName(self):
        return localization.GetByLabel('UI/Station/Hangar/HangarNameWithOwner', charID=self.ownerID)
    def _GetInvCacheContainer(self):
        return sm.GetService('invCache').GetInventory(const.containerHangar, self.itemID)
    def _GetContainerArgs(self):
        return (const.containerHangar, self.itemID)
    def IsItemHere(self, item):
        return item.flagID == const.flagHangar and item.locationID == session.stationid and (item.ownerID == self.ownerID)
class StationCorpDeliveries(BaseInvContainer):
    pass
    __guid__ = 'invCtrl.StationCorpDeliveries'
    scope = uiconst.SCOPE_DOCKED
    oneWay = True
    locationFlag = const.flagCorpDeliveries
    iconName = 'res:/UI/Texture/WindowIcons/corpdeliveries.png'
    isMovable = False
    acceptsDrops = False
    def __init__(self, *args, **kwargs):
        BaseInvContainer.__init__(self, *args, **kwargs)
        self.name = localization.GetByLabel('UI/Inventory/CorpDeliveries')
    def _GetInvCacheContainer(self):
        return sm.GetService('invCache').GetInventory(const.containerCorpMarket, session.corpid)
    def _GetContainerArgs(self):
        return (const.containerCorpMarket, session.corpid)
    def GetOwnerID(self):
        return session.corpid
    def IsItemHere(self, item):
        return item.flagID == const.flagCorpDeliveries and item.locationID in (session.stationid, session.structureid) and (item.ownerID == session.corpid)
    def DoesAcceptItem(self, item):
        return False
class AssetSafetyDeliveries(BaseInvContainer):
    __guid__ = 'invCtrl.AssetSafetyDeliveries'
    scope = uiconst.SCOPE_DOCKED
    acceptsDrops = False
    locationFlag = const.flagAssetSafety
    iconName = 'res:/UI/Texture/WindowIcons/personalDeliveries.png'
    isMovable = False
    def __init__(self, *args, **kwargs):
        BaseInvContainer.__init__(self, *args, **kwargs)
    def _GetInvCacheContainer(self):
        return sm.GetService('invCache').GetInventory(const.containerHangar)
    def _GetContainerArgs(self):
        return (const.containerHangar,)
    def IsItemHere(self, item):
        return item.flagID == const.flagAssetSafety and item.locationID in (session.stationid, session.structureid) and (item.ownerID == session.charid or (item.ownerID == session.corpid and session.corprole & const.corpRoleDirector))
    def GetMenu(self):
        return []
class StationItems(BaseInvContainer):
    pass
    __guid__ = 'invCtrl.StationItems'
    locationFlag = const.flagHangar
    scope = uiconst.SCOPE_DOCKED
    iconName = 'res:/ui/Texture/WindowIcons/itemHangar.png'
    isMovable = False
    def __init__(self, *args, **kwargs):
        BaseInvContainer.__init__(self, *args, **kwargs)
        self.name = localization.GetByLabel('UI/Inventory/ItemHangar')
        self.hasCapacity = True if self._GetCapacity() else False
    @telemetry.ZONE_METHOD
    def IsItemHere(self, item):
        return item.locationID == session.stationid and item.ownerID == session.charid and (item.flagID == const.flagHangar) and (item.categoryID!= const.categoryShip)
    def _GetCapacity(self):
        return sm.GetService('godma').GetTypeAttribute(self.GetTypeID(), const.attributeCapacity)
    def _GetInvCacheContainer(self):
        return sm.GetService('invCache').GetInventory(const.containerHangar)
    def _GetContainerArgs(self):
        return (const.containerHangar,)
    def IsPrimed(self):
        return self.IsInRange()
    def IsInRange(self):
        return session.stationid and self.itemID == session.stationid
class StationShips(BaseInvContainer):
    pass
    __guid__ = 'invCtrl.StationShips'
    iconName = 'res:/ui/Texture/WindowIcons/shiphangar.png'
    scope = uiconst.SCOPE_DOCKED
    locationFlag = const.flagHangar
    isMovable = False
    def __init__(self, *args, **kwargs):
        BaseInvContainer.__init__(self, *args, **kwargs)
        self.name = localization.GetByLabel('UI/Inventory/ShipHangar')
        self.hasCapacity = True if self._GetCapacity() else False
    @telemetry.ZONE_METHOD
    def IsItemHere(self, item):
        return item.locationID == session.stationid and item.ownerID == session.charid and (item.flagID == const.flagHangar) and (item.categoryID == const.categoryShip)
    def GetActiveShip(self):
        activeShipID = eveCfg.GetActiveShip()
        for item in self._GetItems():
            if item.itemID == activeShipID:
                return item
    def GetCapacity(self):
        capacity = self._GetCapacity()
        used = 0
        for item in self.GetItems():
            if occupies_platform(type_id=item.typeID, singleton=bool(item.singleton)):
                used += 1
        return utillib.KeyVal(capacity=capacity, used=used)
    def _GetCapacity(self):
        return get_platform_count(hangar_type_id=self.GetTypeID())
    def _GetInvCacheContainer(self):
        return sm.GetService('invCache').GetInventory(const.containerHangar)
    def _GetContainerArgs(self):
        return (const.containerHangar,)
    def IsPrimed(self):
        return self.IsInRange()
    def IsInRange(self):
        return session.stationid and self.itemID == session.stationid
LOOT_ALL_BUTTON_NAME = 'invLootAllBtn'
class BaseCelestialContainer(BaseInvContainer):
    __guid__ = 'invCtrl.BaseCelestialContainer'
    hasCapacity = True
    isMovable = False
    def __init__(self, *args, **kwargs):
        BaseInvContainer.__init__(self, *args, **kwargs)
        self._isLootable = None
    def IsItemHere(self, item):
        if self.locationFlag is not None:
            return item.locationID == self.itemID and item.flagID == self.locationFlag
        else:
            return item.locationID == self.itemID
    def IsInRange(self):
        bp = sm.GetService('michelle').GetBallpark()
        if bp is None or not InSpace():
            return True
        else:
            ball = bp.GetBall(self.ballID)
            if not ball:
                return False
            else:
                item = bp.GetCrData(self.ballID)
                if item is None:
                    return False
                else:
                    if ball.surfaceDist > self.GetOperationalDistance(item.typeID):
                        return False
                    else:
                        return True
    def GetOperationalDistance(self, typeID):
        distance = sm.GetService('godma').GetTypeAttribute(typeID, const.attributeMaxOperationalDistance)
        if distance is None:
            distance = const.maxCargoContainerTransferDistance
        return distance
    def GetIconName(self):
        try:
            typeID = self.GetTypeID()
        except UserError:
            return self.iconName
        if typeID:
            icon = inventorycommon.typeHelpers.GetIcon(typeID)
            if icon and icon.iconFile:
                return icon.iconFile
        return self.iconName
    def GetName(self):
        if self.name:
            return self.name
        else:
            bp = sm.GetService('michelle').GetBallpark()
            if bp:
                crData = bp.GetCrData(self.ballID)
                if crData:
                    return get_bracket_title(crData)
            return ''
    def _DBLessLimitationsCheck(self, errorName, item):
        if errorName in ['NotEnoughCargoSpace', 'NotEnoughCargoSpaceOverload']:
            eve.Message('ItemMoveGoesThroughFullCargoHold', {'itemType': item.typeID})
            return True
        else:
            return False
    def GetMenu(self):
        return GetMenuService().GetMenuFromItemIDTypeID(self.itemID, self.GetTypeID())
    def GetSpecialActions(self):
        if self.IsLootable():
            return [(localization.GetByLabel('UI/Inventory/LootAll'), self.LootAll, LOOT_ALL_BUTTON_NAME, True)]
        else:
            return []
    def LootAll(self, *args):
        items = self.GetItems()
        shipCargo = ShipCargo()
        if len(items) > 0:
            if sm.GetService('crimewatchSvc').CheckCanTakeItems(self.ballID):
                shipCargo.AddItems(items)
                sm.GetService('audio').SendUIEvent('ui_notify_mission_rewards_play')
            else:
                sm.GetService('crimewatchSvc').SafetyActivated(const.shipSafetyLevelPartial)
                raise UserError('LootTheftDeniedSafetyPreventsSuspect', {'containerName': (const.UE_TYPEID, self.GetTypeID())})
        if shipCargo.HasEnoughSpaceForItems(items):
            sm.ScatterEvent('OnWreckLootAll', self.GetInvID(), items)
    def IsLootable(self):
        if self._isLootable is None:
            bp = sm.GetService('michelle').GetBallpark()
            item = bp.GetCrData(self.ballID) if bp else None
            if item and item.groupID in LOOT_GROUPS:
                self._isLootable = True
                return self._isLootable
            else:
                self._isLootable = False
        return self._isLootable
class ItemFloatingCargo(BaseCelestialContainer):
    pass
    __guid__ = 'invCtrl.ItemFloatingCargo'
    iconName = 'res:/UI/Texture/Shared/Brackets/containerCargo_20x20.png'
    def GetIconName(self):
        return self.iconName
    def GetItems(self):
        sm.GetService('wreck').MarkViewed(self.ballID, self.itemID, True)
        return BaseCelestialContainer.GetItems(self)
    @telemetry.ZONE_METHOD
    def EnterPassword(self, pwd):
        self._GetInvCacheContainer().EnterPassword(pwd)
class ShipMaintenanceBay(BaseCelestialContainer):
    pass
    __guid__ = 'invCtrl.ShipMaintenanceBay'
    locationFlag = const.flagShipHangar
    iconName = 'res:/ui/Texture/WindowIcons/settings.png'
    def GetName(self):
        bayName = GetNameForFlag(self.locationFlag)
        if session.solarsystemid and self.itemID!= eveCfg.GetActiveShip():
            return localization.GetByLabel('UI/Inventory/BayAndLocationName', bayName=evetypes.GetName(self.GetTypeID()), locationName=bayName)
        else:
            return bayName
    def GetOperationalDistance(self, *args):
        return const.maxCargoContainerTransferDistance
class ShipFleetHangar(BaseCelestialContainer):
    __guid__ = 'invCtrl.ShipFleetHangar'
    locationFlag = const.flagFleetHangar
    iconName = 'res:/ui/Texture/WindowIcons/fleet.png'
    def GetName(self):
        bayName = GetNameForFlag(self.locationFlag)
        if session.solarsystemid and self.itemID!= eveCfg.GetActiveShip():
            return localization.GetByLabel('UI/Inventory/BayAndLocationName', bayName=evetypes.GetName(self.GetTypeID()), locationName=bayName)
        else:
            return bayName
    def GetOperationalDistance(self, *args):
        return const.maxCargoContainerTransferDistance
class IndustryStructure(BaseCelestialContainer):
    __guid__ = 'invCtrl.IndustryStructure'
    locationFlag = const.flagCargo
    iconName = 'res:/ui/Texture/WindowIcons/fleet.png'
    def __init__(self, *args, **kwargs):
        BaseCelestialContainer.__init__(self, *args, **kwargs)
    def GetMenu(self):
        return GetMenuService().InvItemMenu(self.GetInventoryItem())
    def GetName(self):
        name = cfg.evelocations.Get(self.itemID).name
        if not name:
            name = evetypes.GetName(self.GetTypeID())
        return name
    def IsInRange(self):
        return True
class StationContainer(BaseCelestialContainer):
    pass
    __guid__ = 'invCtrl.StationContainer'
    hasCapacity = True
    isMovable = True
    def __init__(self, *args, **kwargs):
        BaseCelestialContainer.__init__(self, *args, **kwargs)
        self._oneWay = None
        self.invItem = None
    @property
    def oneWay(self):
        if self._oneWay is not None:
            return self._oneWay
        else:
            if self.invItem is None:
                try:
                    self.invItem = self.GetInventoryItem()
                except Exception:
                    self._oneWay = super(StationContainer, self).oneWay
                    return self._oneWay
            if self.invItem.ownerID == session.corpid and self.invItem.flagID in invConst.flagCorpSAGs:
                    self._oneWay = True
            return self._oneWay
    def GetMenu(self):
        return GetMenuService().InvItemMenu(self.GetInventoryItem())
    def GetName(self):
        name = cfg.evelocations.Get(self.itemID).name
        if not name:
            name = evetypes.GetName(self.GetTypeID())
        return name
    def IsInRange(self):
        return True
    def CheckAndConfirmOneWayMove(self):
        if self.oneWay:
            return self.PromptOneWayMove()
        else:
            if session.solarsystemid:
                invItem = self.GetInventoryItem()
                bp = sm.GetService('michelle').GetBallpark()
                if bp:
                    crData = bp.GetCrData(invItem.locationID)
                    if invItem.flagID == const.flagFleetHangar and invItem.ownerID!= session.charid:
                        return self.PromptOneWayMove()
            return True
    def AddItems(self, items):
        allowedItems = []
        forbiddenTypes = set()
        for item in items:
            typeID = item.typeID
            if can_be_added_to_container(typeID):
                allowedItems.append(item)
            else:
                forbiddenTypes.add(typeID)
        if forbiddenTypes:
            raise ItemCannotBeAddedToContainer(type_ids=forbiddenTypes)
        else:
            super(StationContainer, self).AddItems(allowedItems)
class AssetSafetyContainer(StationContainer):
    __guid__ = 'invCtrl.AssetSafetyContainer'
    scope = uiconst.SCOPE_DOCKED
    isMovable = False
    def __init__(self, itemID=None, typeID=None, name=None):
        StationContainer.__init__(self, itemID, typeID)
        self.name = name
    def GetName(self):
        return self.name or ''
    def IsItemHere(self, item):
        return item.locationID == self.itemID
class ItemWreck(BaseCelestialContainer):
    pass
    __guid__ = 'invCtrl.ItemWreck'
    hasCapacity = False
    def GetIconName(self):
        crData = sm.GetService('michelle').GetCrData(self.ballID)
        if crData:
            state = []
            if crData.isEmpty:
                state.append(BracketState.EMPTY)
            state.append(BracketState.DEFAULT)
            icon = get_brackets_repository().get_icon_bracket(type_id=crData.typeID, state=state)
            if icon is not None:
                return icon.get_texture(16)
    @telemetry.ZONE_METHOD
    def GetItems(self):
        sm.GetService('wreck').MarkViewed(self.ballID, self.itemID, True, True)
        return BaseCelestialContainer.GetItems(self)
class SmartTurretInventory(BaseCelestialContainer):
    __guid__ = 'invCtrl.SmartTurretInventory'
    iconName = 'res:/ui/Texture/WindowIcons/itemHangar.png'
    locationFlag = const.flagCargo
class SmartTurretFitting(BaseCelestialContainer):
    __guid__ = 'invCtrl.SmartTurretFitting'
    iconName = 'res:/ui/Texture/WindowIcons/itemHangar.png'
    locationFlag = const.flagHiSlot0
class SmartHangarInventory(BaseCelestialContainer):
    __guid__ = 'invCtrl.SmartHangarInventory'
    iconName = 'res:/ui/Texture/WindowIcons/itemHangar.png'
    locationFlag = const.flagCargo
class PlayerTrade(BaseInvContainer):
    pass
    __guid__ = 'invCtrl.PlayerTrade'
    scope = uiconst.SCOPE_DOCKED
    viewOnly = True
    hasCapacity = False
    isLockable = False
    filtersEnabled = False
    isMovable = False
    def __init__(self, itemID=None, ownerID=None, tradeSession=None):
        super(PlayerTrade, self).__init__(itemID=itemID)
        self.ownerID = ownerID
        self.tradeSession = tradeSession
        self.invID = (self.__class__.__name__, itemID, ownerID)
    def _GetItems(self):
        return [item for item in self.tradeSession.List().items]
    def IsItemHere(self, item):
        return item.ownerID == self.ownerID and self.itemID == item.locationID
    def GetOwnerID(self):
        return self.ownerID
    def AddItems(self, items):
        activeShipID = eveCfg.GetActiveShip()
        nonTradableTypes = set()
        for item in items:
            if item.itemID == activeShipID:
                raise UserError('PeopleAboardShip')
            else:
                if item.typeID == const.typeAssetSafetyWrap:
                    raise UserError('CannotTradeAssetSafety')
                else:
                    if not is_tradable(item.typeID):
                        nonTradableTypes.add(item.typeID)
        if nonTradableTypes:
            raise ItemCannotBeTraded(type_ids=nonTradableTypes)
        else:
            BaseInvContainer.AddItems(self, items)
    def _GetInvCacheContainer(self):
        self.tradeSession.GetItem = self.tradeSession.GetSelfInvItem
        return self.tradeSession
class SpaceComponentInventory(BaseCelestialContainer):
    pass
    __guid__ = 'invCtrl.SpaceComponentInventory'
    iconName = 'res:/ui/Texture/WindowIcons/itemHangar.png'
    locationFlag = const.flagCargo
    def GetMenu(self):
        return GetMenuService().CelestialMenu(self.itemID)
    def _GetAcceptedCargoBayTypeIDs(self):
        myTypeID = self.GetTypeID()
        if HasCargoBayComponent(myTypeID):
            cargo_bay = get_space_component_for_type(myTypeID, CARGO_BAY)
            return cargo_bay.acceptedTypeIDs
        else:
            return None
    def DoesAcceptItem(self, item):
        if not BaseCelestialContainer.DoesAcceptItem(self, item):
            return False
        else:
            acceptedTypeIDs = self._GetAcceptedCargoBayTypeIDs()
            if acceptedTypeIDs is not None and item.typeID not in acceptedTypeIDs:
                return False
            else:
                return True
class StructureContainer(BaseInvContainer):
    isMovable = False
    def IsInRange(self):
        return session.structureid and self.itemID == session.structureid
    def GetMenu(self):
        return []
class StructureBay(StructureContainer):
    def IsItemHere(self, item):
        return item.locationID == self.itemID and item.flagID == self.locationFlag and (item.ownerID == self.GetOwnerID())
class Structure(StructureContainer):
    __guid__ = 'invCtrl.Structure'
    iconName = 'res:/ui/Texture/WindowIcons/structurebrowser.png'
    def GetName(self):
        name = cfg.evelocations.Get(self.itemID).name
        if not name:
            name = evetypes.GetName(self.GetTypeID())
        return name
    def IsItemHere(self, item):
        return False
class StructureAmmoBay(StructureBay):
    __guid__ = 'invCtrl.StructureAmmoBay'
    iconName = 'res:/ui/Texture/WindowIcons/itemHangar.png'
    locationFlag = const.flagCargo
    def GetName(self):
        return localization.GetByLabel('UI/Ship/AmmoHold')
    def DoesAcceptItem(self, item):
        return item.categoryID == const.categoryCharge
class StructureFuelBay(StructureBay):
    __guid__ = 'invCtrl.StructureFuelBay'
    iconName = 'res:/UI/Texture/WindowIcons/fuelbay.png'
    locationFlag = const.flagStructureFuel
    def GetName(self):
        return localization.GetByLabel('UI/Ship/FuelBay')
    def DoesAcceptItem(self, item):
        return item.groupID == const.groupFuelBlock
class StructureFighterBay(StructureBay):
    __guid__ = 'invCtrl.StructureFighterBay'
    iconName = 'res:/UI/Texture/WindowIcons/dronebay.png'
    locationFlag = const.flagFighterBay
    hasCapacity = True
    def GetName(self):
        return localization.GetByLabel('UI/Ship/FighterBay')
    def DoesAcceptItem(self, item):
        return item.categoryID == const.categoryFighter
class StructureItemHangar(StructureContainer):
    __guid__ = 'invCtrl.StructureItemHangar'
    iconName = 'res:/ui/Texture/WindowIcons/itemHangar.png'
    locationFlag = const.flagHangar
    def __init__(self, *args, **kwargs):
        BaseInvContainer.__init__(self, *args, **kwargs)
        self.name = localization.GetByLabel('UI/Inventory/ItemHangar')
    def IsItemHere(self, item):
        return item.locationID == self.itemID and item.ownerID == session.charid and (item.flagID == const.flagHangar) and (item.categoryID!= const.categoryShip)
class StructureShipHangar(StructureContainer):
    __guid__ = 'invCtrl.StructureShipHangar'
    iconName = 'res:/ui/Texture/WindowIcons/shiphangar.png'
    locationFlag = const.flagHangar
    def __init__(self, *args, **kwargs):
        BaseInvContainer.__init__(self, *args, **kwargs)
        self.name = localization.GetByLabel('UI/Inventory/ShipHangar')
    def IsItemHere(self, item):
        return item.locationID == self.itemID and item.ownerID == session.charid and (item.flagID == const.flagHangar) and (item.categoryID == const.categoryShip)
class StructureDeliveriesHangar(StructureContainer):
    __guid__ = 'invCtrl.StructureDeliveriesHangar'
    iconName = 'res:/ui/Texture/WindowIcons/personalDeliveries.png'
    locationFlag = const.flagDeliveries
    isMovable = False
    def __init__(self, *args, **kwargs):
        BaseInvContainer.__init__(self, *args, **kwargs)
        self.name = localization.GetByLabel('UI/Inventory/DeliveriesHangar')
    def IsItemHere(self, item):
        return item.locationID == self.itemID and item.ownerID == session.charid and (item.flagID == const.flagDeliveries)
    def DoesAcceptItem(self, item):
        if item.typeID == invConst.typePlex and item.itemID is None:
            return False
        else:
            return super(StructureDeliveriesHangar, self).DoesAcceptItem(item)
class StructureCorpHangar(BaseCorpContainer):
    __guid__ = 'invCtrl.StructureCorpHangar'
    def IsInRange(self):
        office = sm.GetService('officeManager').GetCorpOfficeAtLocation()
        return office and office.officeID == self.itemID
    def GetMenu(self):
        return []
    def GetItems(self):
        try:
            return BaseCorpContainer.GetItems(self)
        except UserError:
            return []
    def SetDivisionID(self, divisionID):
        BaseCorpContainer.SetDivisionID(self, divisionID)
        self.locationFlag = const.corpFlagByDivision.get(divisionID)
class AssetSafetyCorpContainer(StructureCorpHangar):
    __guid__ = 'invCtrl.AssetSafetyCorpContainer'
    scope = uiconst.SCOPE_DOCKED
    isMovable = False
    def GetName(self):
        if self.divisionID == invConst.flagCorpDeliveries:
            return localization.GetByLabel('UI/Inventory/CorpDeliveries')
        else:
            return StructureCorpHangar.GetName(self)
    def SetDivisionID(self, divisionID):
        StructureCorpHangar.SetDivisionID(self, divisionID)
        self.locationFlag = invConst.corpAssetSafetyFlagsFromDivision.get(divisionID)
    def GetIconName(self):
        if self.locationFlag == const.flagCorpDeliveries:
            return 'res:/UI/Texture/WindowIcons/corpdeliveries.png'
        else:
            return StructureCorpHangar.GetIconName(self)
    def DoesAcceptItem(self, item):
        if item.typeID == invConst.typePlex and item.itemID is None:
            return False
        else:
            return super(AssetSafetyCorpContainer, self).DoesAcceptItem(item)
    def _GetInvCacheContainer(self):
        return sm.GetService('invCache').GetInventoryFromId(self.itemID)
    def IsInRange(self):
        return True
class StructureDeedBay(StructureBay):
    __guid__ = 'invCtrl.StructureDeedBay'
    iconName = 'res:/UI/Texture/WindowIcons/fuelbay.png'
    locationFlag = invConst.flagStructureDeed
    def GetName(self):
        return localization.GetByLabel('UI/Ship/StructureDeedBay')
    def DoesAcceptItem(self, item):
        return item.groupID == invConst.groupStructureDeed
def GetInvCtrlFromInvID(invID):
    from eve.client.script.environment import invControllers
    if invID is None:
        return
    else:
        cls = getattr(invControllers, invID[0], None)
        if cls is not None:
            return cls(*invID[1:])
        else:
            return None
class ItemSiphonPseudoSilo(BaseCelestialContainer):
    pass
    __guid__ = 'invCtrl.ItemSiphonPseudoSilo'
    iconName = 'res:/UI/Texture/Icons/38_20_12.png'
    def GetIconName(self):
        return self.iconName
    def GetItems(self):
        return BaseCelestialContainer.GetItems(self)
class PlexVault(BaseInvContainer):
    __guid__ = 'invCtrl.PlexVault'
    iconName = PLEX_128_GRADIENT_YELLOW
    locationFlag = None
    hasCapacity = False
    oneWay = False
    viewOnly = False
    scope = None
    isLockable = False
    isMovable = False
    filtersEnabled = False
    typeID = None
    acceptsDrops = True
    def IsItemHere(self, item):
        return False
    def IsPrimed(self):
        return True
    def DoesAcceptItem(self, item):
        return item.groupID == invConst.groupCurrency
    def GetInventoryItem(self):
        return
    def GetMenu(self):
        return []
    def GetItems(self):
        return []
    def AddItems(self, items):
        locationID = session.stationid or session.structureid
        inventoryMgr = sm.GetService('invCache').GetInventoryMgr()
        for item in items:
            if item.groupID!= invConst.groupCurrency:
                continue
            else:
                quantity = item.stacksize
                if len(items) == 1 and uicore.uilib.Key(uiconst.VK_SHIFT):
                        quantity = self.PromptUserForQuantity(item, quantity)
                if quantity:
                    reference = inventoryMgr.DepositPlexToVault(locationID, item.itemID, quantity)
    def OnDropData(self, nodes):
        items = super(PlexVault, self).OnDropData(nodes)
        for node in nodes:
            if getattr(node, '__guid__', None) == 'listentry.InvAssetItem':
                items.append(node.item)
        return items
    def CheckAndHandlePlexVaultItem(self, node):
        return False
    def PromptUserForQuantity(self, item, itemQuantity, sourceLocation=None):
        message = localization.GetByLabel('UI/Inventory/ItemActions/DivideItemStack')
        quantity = item.stacksize
        ret = uix.QtyPopup(maxvalue=quantity, minvalue=0, setvalue=quantity, hint=message)
        if ret:
            return ret['qty']
        else:
            return None