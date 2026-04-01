# Decompiled with PyLingual (https://pylingual.io)
# Internal filename: 'C:\\BuildAgent\\work\\6ec9bf56460fca58\\packages\\frontier\\industry\\client\\ui\\item_slots.py'
# Bytecode version: 3.12.0rc2 (3531)
# Source timestamp: 2026-03-17 10:26:07 UTC (1773743167)

from __future__ import annotations
import eveformat
import eveicon
import evelink.client as evelink
import eveui
import graviton
import threadutils
import typing as t
import uthread2
from carbonui import Align, uiconst
from carbonui.control.buttonIcon import ButtonIcon
from carbonui.uicore import uicore
from eve.client.script.ui.control.itemIcon import ItemIcon
from eveservices.menu import GetMenuService
from frontier.industry.client.ui.controller import ItemSlotController
from functools import partial
from graviton import Palette
from frontier.smart_assemblies.client.storage.controller import StorageController
from frontier.smart_assemblies.client.storage.smart_storage_inventory import SmartStorageUnitInventory
class ItemSlotCard(eveui.ContainerAutoSize):
    pass
    def __init__(self, controller: ItemSlotController, set_focused, pointer_direction, **kwargs):
        super(ItemSlotCard, self).__init__(state=uiconst.UI_NORMAL, alignMode=Align.TOTOP, **kwargs)
        self._controller = controller
        self._set_focused = set_focused
        self._pointer_direction = pointer_direction
        self._quantity_label = None
        self._frame = None
        self._tooltip_anchor = None
        self._layout()
        if self._controller.withdraw:
            self.MakeDragObject()
        if self._controller.deposit:
            self.MakeDropLocation()
            self._bottom_container.MakeDropLocation()
            self._bottom_container.OnDropData = self.OnDropData
        self._on_current_quantity_changed()
        self._on_pending_quantity_changed()
        self._controller.on_current_quantity_changed.connect(self._on_current_quantity_changed)
        self._controller.on_pending_quantity_changed.connect(self._on_pending_quantity_changed)
    def _on_current_quantity_changed(self):
        self._item_stack.set_quantity_text(self._controller.current_quantity, self._get_quantity_text_color())
        self._capacity_bar.value = self._controller.usage_percentage
    def _on_pending_quantity_changed(self):
        self._capacity_bar.target_value = self._controller.pending_usage_percentage or None
    def _layout(self):
        top_container = eveui.ContainerAutoSize(parent=self, align=Align.TOTOP, alignMode=Align.TOTOP, padBottom=8)
        graviton.Text(parent=top_container, align=Align.TORIGHT, style=graviton.TextStyle.DISKET_SMALL, text=str(self._controller.quantity_per_run), padLeft=8)
        graviton.Text(parent=top_container, align=Align.TOTOP, style=graviton.TextStyle.DISKET_SMALL, maxLines=1, text=self._controller.name)
        self._tooltip_anchor = eveui.Container(parent=self, align=Align.TOTOP_NOPUSH, height=23)
        self._tooltip_anchor.GetTooltipPointer = lambda: self._pointer_direction
        body_container = eveui.ContainerAutoSize(parent=self, align=Align.TOTOP, alignMode=Align.TOTOP)
        self._info_icon = ButtonIcon(parent=body_container, align=Align.TOPRIGHT, padding=8, texturePath=eveicon.show_info, func=lambda *args: sm.GetService('info').ShowInfo(self._controller.type_id))
        self._info_icon.display = False
        self._item_stack = ItemStackContainer(parent=body_container, align=Align.TOTOP, type_id=self._controller.type_id, state=uiconst.UI_DISABLED)
        self.GetMenu = self._item_stack.GetMenu
        self._bottom_container = eveui.ContainerAutoSize(parent=self, state=uiconst.UI_NORMAL, align=Align.TOTOP, alignMode=Align.TOTOP)
        self._bottom_container.LoadTooltipPanel = self._load_bottom_tooltip_panel
        self._bottom_container.GetTooltipPointer = lambda: uiconst.POINT_TOP_2
        self._capacity_bar = graviton.SegmentedProgressBar(parent=self._bottom_container, align=Align.TOTOP, height=6, segment_count=self._controller.max_runs, segment_spacing=2, color=Palette.MARTIAN_RED, change_color=Palette.MARTIAN_RED.with_alpha(0.3), back_color=Palette.NEUTRAL.with_alpha(0.2), padTop=8)
    def _get_quantity_text_color(self):
        if self._controller.current_quantity is None:
            return (0, 0, 0, 0)
        else:
            if self._controller.current_quantity == 0:
                return Palette.NEUTRAL.with_alpha(0.3)
            else:
                if self._controller.current_quantity >= self._controller.quantity_per_run:
                    return Palette.MARTIAN_RED
                else:
                    return Palette.NEUTRAL
    def _load_bottom_tooltip_panel(self, tooltip_panel, *args, **kwargs):
        tooltip_panel.columns = 2
        tooltip_panel.margin = 8
        tooltip_panel.cellSpacing = (24, 4)
        tooltip_panel.AddLabelMedium(text='Quantity per run', colSpan=1)
        tooltip_panel.AddLabelMedium(text=eveformat.number(self._controller.quantity_per_run), colSpan=1, align=Align.TORIGHT)
        tooltip_panel.AddLabelMedium(text='Storage Capacity', colSpan=1)
        tooltip_panel.AddLabelMedium(text='{} / {}'.format(eveformat.number(self._controller.current_quantity), eveformat.number(self._controller.max_quantity)), colSpan=1, align=Align.TORIGHT)
        tooltip_panel.AddLabelMedium(text='Max Runs', colSpan=1)
        tooltip_panel.AddLabelMedium(text=eveformat.number(self._controller.max_runs), colSpan=1, align=Align.TORIGHT)
    def GetTooltipDelay(self):
        return 0
    def OnClick(self, *args):
        super(ItemSlotCard, self).OnClick(*args)
        self._set_focused(self._tooltip_anchor, self._controller)
    def OnMouseEnter(self, *args):
        super(ItemSlotCard, self).OnMouseEnter(*args)
        self._item_stack.hovered = True
        self._info_icon.display = True
        self._set_focused(self._tooltip_anchor, self._controller)
    def OnMouseExit(self, *args):
        super(ItemSlotCard, self).OnMouseExit(*args)
        self._item_stack.hovered = False
        self._info_icon.display = False
    def GetDragData(self):
        return [IndustryItemDragData(self._controller)]
class ItemStackContainer(eveui.Container):
    def __init__(self, type_id, quantity_text=None, on_click=None, on_hover=None, height=80, state=uiconst.UI_NORMAL, **kwargs):
        super(ItemStackContainer, self).__init__(state=state, height=height, **kwargs)
        self._type_id = type_id
        self._on_click = on_click
        self._on_hover = on_hover
        self._error = None
        self._hovered = False
        self._selected = False
        self._layout()
        self.set_quantity_text(quantity_text)
    def set_quantity_text(self, text, color=None):
        self._quantity_label.text = text
        if color is not None:
            self._quantity_label.color = color
    @property
    def type_id(self):
        return self._type_id
    @property
    def selected(self):
        return self._selected
    @selected.setter
    def selected(self, value):
        if self._selected == value:
            return
        else:
            self._selected = value
            self._update_frame()
    @property
    def hovered(self):
        return self._hovered
    @hovered.setter
    def hovered(self, value):
        if self._hovered == value:
            return
        else:
            self._error = False
            eveui.Sound.entry_hover.play()
            self._hovered = value
            if self._on_hover:
                self._on_hover(self)
            self._update_frame()
    @property
    def error(self):
        return self._error
    @error.setter
    def error(self, value):
        if self._error == value:
            return
        else:
            self._error = value
            self._update_frame()
    def OnClick(self, *args, **kwargs):
        if self._on_click:
            self._on_click(self)
    def GetMenu(self):
        return GetMenuService().GetMenuFromItemIDTypeID(None, self.type_id, includeMarketDetails=True)
    def OnMouseEnter(self, *args):
        super(ItemStackContainer, self).OnMouseEnter(*args)
        self.hovered = True
    def OnMouseExit(self, *args):
        super(ItemStackContainer, self).OnMouseExit(*args)
        self.hovered = False
    def _layout(self):
        self._icon = ItemIcon(parent=self, state=uiconst.UI_DISABLED, align=Align.CENTER, height=64, width=64, typeID=self.type_id)
        self._quantity_label = graviton.Text(parent=self, align=Align.BOTTOMRIGHT, style=graviton.TextStyle.ABC_MEDIUM, text='', shadowOffset=(0, 0), left=6, top=2)
        self._construct_frame()
    def _construct_frame(self):
        container = eveui.Container(parent=self, align=Align.TOALL)
        self._corner_frame = eveui.Frame(parent=container, align=Align.TOALL, color=(0, 0, 0, 0), texturePath='res:/UI/Texture/Shared/frame_corners_8.png', cornerSize=10)
        self._frame = eveui.Frame(parent=container, align=Align.TOALL, color=(0, 0, 0, 0))
        eveui.Fill(parent=container, align=Align.TOALL, color=Palette.CRUDE.with_alpha(0.8), padding=1)
        self._update_frame()
    def _update_frame(self):
        if self.error:
            self._corner_frame.color = Palette.CRITICAL
            self._frame.color = Palette.CRITICAL.with_alpha(0.4)
        else:
            if self.selected:
                self._corner_frame.color = Palette.MARTIAN_RED
                self._frame.color = Palette.MARTIAN_RED.with_alpha(0.4)
            else:
                if self.hovered:
                    self._corner_frame.color = Palette.MARTIAN_RED.with_alpha(0.3)
                    self._frame.color = Palette.MARTIAN_RED.with_alpha(0.2)
                else:
                    self._corner_frame.color = Palette.NEUTRAL.with_alpha(0.4)
                    self._frame.color = Palette.NEUTRAL.with_alpha(0.2)
class ItemSlotActions(eveui.ContainerAutoSize):
    def __init__(self, controller: ItemSlotController, state=uiconst.UI_NORMAL, align=Align.TOTOP, max_content_height=None, **kwargs):
        super(ItemSlotActions, self).__init__(state=state, align=align, alignMode=Align.TOTOP, minWidth=220, **kwargs)
        self._controller = controller
        self._max_content_height = max_content_height
        self._header_title = None
        self._header_subtitle = None
        self._displaying = None
        self._construct_header()
        if max_content_height:
            content_parent = eveui.ScrollContainer(parent=self, align=Align.TOTOP, pushContent=False, scaleHeightWithContent=True, maxHeight=max_content_height)
        else:
            content_parent = self
        self._content = eveui.ContainerAutoSize(parent=content_parent, align=Align.TOTOP)
        self._display_actions()
        self._controller.on_current_quantity_changed.connect(self._on_current_quantity_changed)
    def Close(self):
        super(ItemSlotActions, self).Close()
        self._controller.on_current_quantity_changed.disconnect(self._on_current_quantity_changed)
    def _on_current_quantity_changed(self):
        if self._displaying == 'deposit':
            if self._controller.is_full:
                self._display_actions()
        else:
            if self._displaying == 'withdraw':
                if not self._controller.current_quantity:
                    self._display_actions()
    def _deposit(self, inventory, runs=None):
        if isinstance(inventory, SmartStorageUnitInventory):
            from frontier.smart_assemblies.client.smart_assembly_svc import SmartAssemblySvc
            items = SmartAssemblySvc.get_inventory_for_ssu(sm.GetService('smartAssemblySvc'), session.charid, inventory.itemID)
            print(f'Items in SSU {inventory.locationFlag}: {items}')
            for inventory in self._controller.get_nearby_inventories():
                print(inventory)
                if has_relevant_items(items, self._controller.type_id):
                    print(f"items are relevant { has_relevant_items(items, self._controller.type_id)}")
                    self._controller.deposit(items, runs, inventory, uicore.uilib.Key(uiconst.VK_SHIFT))
                else:
                    print(f"No relevant items in inventory {inventory.GetName()}")
        else:
            print(f'Items in inventory')
            for inventory in self._controller.get_nearby_inventories():
                if has_relevant_items(inventory, self._controller.type_id):
                    self._controller.deposit(inventory, runs, inventory, uicore.uilib.Key(uiconst.VK_SHIFT))
                else:
                    print(f"No relevant items in inventory {inventory.GetName()}")

        self._display_deposit()
    def _withdraw(self, inventory, runs=None):
        if isinstance(inventory, SmartStorageUnitInventory):
            self._controller.withdraw(inventory, runs, inventory.locationFlag, uicore.uilib.Key(uiconst.VK_SHIFT))
        else:
            self._controller.withdraw(inventory, runs, inventory.locationFlag, uicore.uilib.Key(uiconst.VK_SHIFT))
    def _display_actions(self):
        if not self._controller.allow_deposit:
            self._display_withdraw()
            return
        else:
            self._displaying = 'actions'
            self._flush_content()
            self._set_header(title=self._controller.name, subtitle=self._controller.group_name)
            if self._controller.allow_deposit:
                ActionEntry(parent=self._content, align=Align.TOTOP, title='Deposit', on_click=self._display_deposit, enabled=self._controller.can_deposit)
            if self._controller.allow_withdraw:
                ActionEntry(parent=self._content, align=Align.TOTOP, title='Withdraw', on_click=self._display_withdraw, enabled=self._controller.can_withdraw)
            self._content.minHeight = 0
            self._content.EnableAutoSize()
    def _display_deposit(self):
        self._displaying = 'deposit'
        self._flush_content()
        self._set_header(title='Deposit', subtitle='Choose source inventory')
        inv_container = eveui.ContainerAutoSize(parent=self._content, align=Align.TOTOP, minHeight=32)
        self._construct_inventories(inv_container, self._controller.get_nearby_inventories, self._deposit, require_relevant=True)
        self._construct_controls(self._content)
        self._content.minHeight = 0
        self._content.EnableAutoSize()
    def _display_withdraw(self):
        self._displaying = 'withdraw'
        self._flush_content()
        self._set_header(title='Withdraw', subtitle='Choose destination inventory')
        inv_container = eveui.ContainerAutoSize(parent=self._content, align=Align.TOTOP)
        if not self._controller.can_withdraw:
            graviton.Text(parent=inv_container, align=Align.TOTOP, style=graviton.TextStyle.ABC_SMALL, text='No items to withdraw', padding=8)
        else:
            self._construct_inventories(inv_container, self._controller.get_nearby_inventories, self._withdraw, require_relevant=False)
        self._construct_controls(self._content)
        self._content.minHeight = 0
        self._content.EnableAutoSize()
    def _flush_content(self):
        self._content.DisableAutoSize()
        self._content.minHeight = self._content.GetCurrentAbsoluteSize()[1]
        self._content.Flush()
    @threadutils.threaded
    def _construct_inventories(self, parent, get_inventories, action, require_relevant):
        loading = eveui.Container(parent=parent, align=Align.TOTOP, height=32)
        inventories = get_inventories()
        loading.Close()
        added_entry = False
        for inventory in inventories:
            print(inventory)
            if isinstance(inventory, SmartStorageUnitInventory):
                from frontier.smart_assemblies.client.smart_assembly_svc import SmartAssemblySvc
                items = SmartAssemblySvc.get_inventory_for_ssu(sm.GetService('smartAssemblySvc'), session.charid, inventory.itemID)
                if not items:
                    continue
                else:
                    if require_relevant and (not has_relevant_items(items, self._controller.type_id)):
                        continue
                    else:
                        InventoryActionEntry(parent=parent, align=Align.TOTOP, title=inventory.GetName(), inventory=inventory, relevant_type_id=self._controller.type_id, require_relevant=require_relevant, on_click=partial(action, inventory), on_right_click=partial(action, inventory, runs=1))
                        print(f'WTF {inventory}, {items}')
                        added_entry = True
                        continue
            else:
                if require_relevant and (not has_relevant_items(inventory, self._controller.type_id)):
                    continue
            InventoryActionEntry(parent=parent, align=Align.TOTOP, title=inventory.GetName(), inventory=inventory, relevant_type_id=self._controller.type_id, require_relevant=require_relevant, on_click=partial(action, inventory), on_right_click=partial(action, inventory, runs=1))
            added_entry = True
        if not added_entry:
            graviton.Text(parent=parent, align=Align.TOTOP, style=graviton.TextStyle.ABC_SMALL, text='No available inventory found', padding=8)
    def _construct_controls(self, parent):
        wrapper = eveui.ContainerAutoSize(parent=parent, align=Align.TOTOP, alignMode=Align.TOTOP, bgColor=Palette.CRUDE.with_alpha(0.8))
        eveui.Frame(parent=wrapper, align=Align.TOALL, color=Palette.NEUTRAL.with_alpha(0.05))
        container = eveui.FlowContainer(parent=wrapper, align=Align.TOTOP, autoHeight=True, content_spacing=(12, 8), padding=(4, 8, 4, 8))
        click_container = eveui.ContainerAutoSize(parent=container, align=Align.NOALIGN, alignMode=Align.CENTERLEFT, padding=4)
        eveui.Sprite(parent=click_container, state=uiconst.UI_DISABLED, align=Align.CENTERLEFT, height=16, width=16, texturePath='res:/UI/Texture/Shared/mouse/left_click_16.png')
        graviton.Text(parent=click_container, align=Align.CENTERLEFT, padLeft=20, style=graviton.TextStyle.ABC_SMALL, color=Palette.NEUTRAL.with_alpha(0.6), text='Max')
        click_container = eveui.ContainerAutoSize(parent=container, align=Align.NOALIGN, alignMode=Align.CENTERLEFT, padding=4)
        eveui.Sprite(parent=click_container, state=uiconst.UI_DISABLED, align=Align.CENTERLEFT, height=16, width=16, texturePath='res:/UI/Texture/Shared/mouse/right_click_16.png')
        graviton.Text(parent=click_container, align=Align.CENTERLEFT, padLeft=20, style=graviton.TextStyle.ABC_SMALL, color=Palette.NEUTRAL.with_alpha(0.6), text='1 Run')
        click_container = eveui.ContainerAutoSize(parent=container, align=Align.NOALIGN, alignMode=Align.CENTERLEFT, padding=4)
        eveui.Sprite(parent=click_container, state=uiconst.UI_DISABLED, align=Align.CENTERLEFT, height=16, width=36, texturePath='res:/UI/Texture/Shared/mouse/shift_left_click_16.png')
        graviton.Text(parent=click_container, align=Align.CENTERLEFT, padLeft=40, style=graviton.TextStyle.ABC_SMALL, color=Palette.NEUTRAL.with_alpha(0.6), text='Custom')
    def _set_header(self, title, subtitle):
        self._header_title.text = title
        self._header_subtitle.text = subtitle
    def _construct_header(self):
        container = eveui.ContainerAutoSize(parent=self, state=uiconst.UI_DISABLED, align=Align.TOTOP, alignMode=Align.TOTOP, bgColor=Palette.CRUDE)
        eveui.Frame(parent=container, align=Align.TOALL, color=Palette.MARTIAN_RED.with_alpha(0.2))
        text_container = eveui.ContainerAutoSize(parent=container, align=Align.TOTOP, padding=(8, 4, 8, 4), clipChildren=True)
        self._header_subtitle = graviton.Text(parent=text_container, align=Align.TOTOP, style=graviton.TextStyle.ABC_SMALL, text=' ', color=Palette.NEUTRAL.with_alpha(0.3))
        self._header_title = graviton.Text(parent=text_container, align=Align.TOTOP, style=graviton.TextStyle.DISKET_MEDIUM, text=' ', color=Palette.NEUTRAL)
    def _construct_body(self):
        return
    def _construct_footer(self):
        return
class ActionEntry(eveui.Container):
    pass
    def __init__(self, title, on_click, on_right_click=None, subtitle='', enabled=True, **kwargs):
        super(ActionEntry, self).__init__(state=uiconst.UI_NORMAL, height=32, **kwargs)
        self._title = title
        self._subtitle = subtitle
        self._on_click = on_click
        self._on_right_click = on_right_click
        self._enabled = enabled
        self._selected = False
        self._hovered = False
        self._busy = False
        self._title_label = None
        self._subtitle_label = None
        self._layout()
    @property
    def subtitle(self):
        return self._subtitle
    @subtitle.setter
    def subtitle(self, value):
        self._subtitle = value
        self._subtitle_label.text = value
    def _layout(self):
        self._construct_underlay()
        text_container = eveui.Container(parent=self, align=Align.TOALL, padding=(8, 0, 8, 0))
        subtitle_container = eveui.ContainerAutoSize(parent=text_container, align=Align.TORIGHT, clipChildren=True, padLeft=4 if self._subtitle else 0)
        self._subtitle_label = graviton.Text(parent=subtitle_container, align=Align.CENTERRIGHT, style=graviton.TextStyle.ABC_SMALL, text=self._subtitle)
        title_container = eveui.Container(parent=text_container, align=Align.TOALL, clipChildren=True)
        self._title_label = graviton.Text(parent=title_container, align=Align.CENTERLEFT, style=graviton.TextStyle.ABC_SMALL, text=self._title)
        self._update_state()
    def _construct_underlay(self):
        self._corner_frame = eveui.Frame(parent=self, align=Align.TOALL, color=(0, 0, 0, 0), texturePath='res:/UI/Texture/Shared/frame_corners_8.png', cornerSize=10)
        self._frame = eveui.Frame(parent=self, align=Align.TOALL, color=Palette.NEUTRAL.with_alpha(0.05))
        self._bg = eveui.Fill(bgParent=self, align=Align.TOALL, color=Palette.CRUDE.with_alpha(0.6), padding=1)
    def OnClick(self, *args, **kwargs):
        if self._on_click and self._enabled:
                self._set_busy(True)
                self._on_click()
                self._set_busy(False)
    def GetMenu(self):
        if self._on_right_click and self._enabled:
                self._set_busy(True)
                self._on_right_click()
                self._set_busy(False)
    def OnMouseDown(self, *args):
        super(ActionEntry, self).OnMouseDown(*args)
        self._set_selected(True)
    def OnMouseUp(self, *args):
        super(ActionEntry, self).OnMouseUp(*args)
        self._set_selected(False)
    def OnMouseEnter(self, *args):
        super(ActionEntry, self).OnMouseEnter(*args)
        self._set_hovered(True)
    def OnMouseExit(self, *args):
        super(ActionEntry, self).OnMouseExit(*args)
        self._set_hovered(False)
    def _set_enabled(self, value):
        if self._enabled == value:
            return
        else:
            self._enabled = value
            self._update_state()
    def _set_selected(self, value):
        if self._selected == value:
            return
        else:
            self._selected = value
            self._update_state()
    def _set_hovered(self, value):
        if self._hovered == value:
            return
        else:
            self._hovered = value
            self._update_state()
    def _set_busy(self, value):
        if self._busy == value:
            return
        else:
            self._busy = value
            self._update_state()
    def _update_state(self):
        if not self._enabled or self._busy:
            self._corner_frame.color = (0, 0, 0, 0)
            self._frame.color = Palette.NEUTRAL.with_alpha(0.05)
            self._bg.color = Palette.CRUDE.with_alpha(0.6)
            self._update_text_color(Palette.NEUTRAL.with_alpha(0.2))
        else:
            if self._selected:
                self._corner_frame.color = Palette.MARTIAN_RED
                self._frame.color = Palette.MARTIAN_RED.with_alpha(0.4)
                self._bg.color = Palette.MARTIAN_RED.with_alpha(0.1)
                self._update_text_color(Palette.NEUTRAL.with_alpha(0.8))
            else:
                if self._hovered:
                    self._corner_frame.color = Palette.MARTIAN_RED.with_alpha(0.3)
                    self._frame.color = Palette.MARTIAN_RED.with_alpha(0.2)
                    self._bg.color = Palette.NEUTRAL.with_alpha(0.05)
                    self._update_text_color(Palette.NEUTRAL.with_alpha(0.8))
                else:
                    self._corner_frame.color = (0, 0, 0, 0)
                    self._frame.color = Palette.NEUTRAL.with_alpha(0.05)
                    self._bg.color = Palette.CRUDE.with_alpha(0.6)
                    self._update_text_color(Palette.NEUTRAL.with_alpha(0.8))
    def _update_text_color(self, color):
        self._title_label.color = color
        self._subtitle_label.color = color
class InventoryActionEntry(ActionEntry):
    pass
    def __init__(self, inventory, relevant_type_id, require_relevant=False, **kwargs):
        self._inventory = inventory
        self._relevant_type_id = relevant_type_id
        self._require_relevant = require_relevant
        self._progress_bar = None
        super(InventoryActionEntry, self).__init__(**kwargs)
        self._update()
        sm.RegisterForNotifyEvent(self, 'OnItemChanged')
    def Close(self):
        sm.UnregisterForNotifyEvent(self, 'OnItemChanged')
        super(InventoryActionEntry, self).Close()
    def _layout(self):
        self._progress_bar = graviton.SegmentedProgressBar(parent=self, align=Align.TOBOTTOM_NOPUSH, value=0, color=Palette.NEUTRAL.with_alpha(0.8), change_color=Palette.NEUTRAL.with_alpha(0), height=2, padding=(8, 0, 8, 4))
        super(InventoryActionEntry, self)._layout()
    def OnItemChanged(self, item, change, location):
        self._update()
    @threadutils.threaded
    def _update(self):
        self._update_subtitle()
        self._update_progress()
    def _update_progress(self):
        capacity = self._inventory.GetCapacity()
        self._progress_bar.value = capacity.used / capacity.capacity
    def _update_subtitle(self):
        relevant_quantity = get_relevant_items_quantity(self._inventory, self._relevant_type_id)
        self.subtitle = relevant_quantity or ''
        print(type(self._inventory))
        if self._require_relevant:
            self._set_enabled(bool(relevant_quantity))
    def _update_text_color(self, color):
        super(InventoryActionEntry, self)._update_text_color(color)
        self._progress_bar.color = color
class IndustryItemDragData(object):
    __guid__ = 'IndustryItemDragData'
    def __init__(self, controller: ItemSlotController):
        self.controller = controller
    def get_link(self):
        return evelink.type_link(self.controller.type_id)
    def LoadIcon(self, icon, parent, size):
        icon.LoadIconByTypeID(self.controller.type_id, size=size)
    def on_add_item(self, inventory):
        self.controller.withdraw(inventory, prompt_quantity=uicore.uilib.Key(uiconst.VK_SHIFT))
def get_relevant_items_quantity(inventory, type_id):
    try:
        # Legacy code, might not be needed anymore
        if isinstance(inventory, list): 
            item = enumerate(inventory)
            for itemsub in item:
                #print(f"testing items: {itemsub[0]}: {itemsub[1]}")
                value = itemsub[1].type_id
                if value == type_id:
                    #print("found item quantity")
                    return itemsub[1].quantity
            return False
        # Since we pass the whole inventory object to this function, we need to verify if it actually contains said items.
        elif isinstance(inventory, SmartStorageUnitInventory):
            from frontier.smart_assemblies.client.smart_assembly_svc import SmartAssemblySvc
            ssu = SmartAssemblySvc.get_inventory_for_ssu(sm.GetService('smartAssemblySvc'), session.charid, inventory.itemID)
            print("TEST")
            item = enumerate(ssu)
            for itemsub in item:
                #print(f"testing items: {itemsub[0]}: {itemsub[1]}")
                value = itemsub[1].type_id
                if value == type_id:
                    #print("found item quantity")
                    return itemsub[1].quantity
        else:
            return sum([item.stacksize for item in inventory.GetItems() if (item.typeID == type_id and (not item.singleton))])
    except Exception as e:
        print(f"get_relevant_items_quantity failed with: {e}")
        return 0    
def has_relevant_items(inventory, type_id):
    try:
        print(f"HAVE: {inventory} - {type(inventory)} - - REQUIRED: {type_id}")
        if isinstance(inventory, list): 
            item = enumerate(inventory)
            print(item)
            for itemsub in item:
                value = itemsub[1].type_id
                if value == type_id:
                    print("TRUE")
                    return True
            return False
        else:
            return any([item for item in inventory.GetItems() if item.typeID == type_id and (not item.singleton)])
    except Exception as e:
        print(e)
        return False