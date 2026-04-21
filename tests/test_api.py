import pytest
import pytest_asyncio
from aiohttp import web
from unittest.mock import MagicMock, AsyncMock

from pyalexatodo.api import AlexaToDoAPI
from pyalexatodo.models.list_info import ListInfo
from pyalexatodo.models.list_item import ListItem
from pyalexatodo.models.list_type import ListType
from pyalexatodo.models.list_item_status import ListItemStatus
from pyalexatodo.exceptions import ItemNotFoundException

class FakeAlexaApiServer:
    def __init__(self):
        self.lists: list[ListInfo] = [
            ListInfo(listId="list1",
                     listType=ListType.SHOP),
            ListInfo(listId="list2",
                     listType=ListType.TODO),
            ListInfo(listId="list3",
                     listType=ListType.CUSTOM,
                     listName="Places to Visit")  # ty:ignore[unknown-argument]
            
        ]
        self.items: dict[str, list[ListItem]] = {
            "list1": [
                ListItem(itemId="item1",
                         itemName="Tapioka",
                         itemStatus=ListItemStatus.ACTIVE,
                         version=1),
                ListItem(itemId="item2",
                         itemName="Milk",
                         itemStatus=ListItemStatus.ACTIVE,
                         version=1),
                ListItem(itemId="item3",
                         itemName="Jasmine Tea",
                         itemStatus=ListItemStatus.COMPLETE,
                         version=1)
            ],
            "list2": [
                ListItem(itemId="item4",
                         itemName="Text my mum",
                         itemStatus=ListItemStatus.ACTIVE,
                         version=1),
                ListItem(itemId="item5",
                         itemName="Dishes",
                         itemStatus=ListItemStatus.COMPLETE,
                         version=1)
            ],
            "list3": []
        }
        self.fail_next = False

    async def fetch_lists(self, request):
        if self.fail_next:
            self.fail_next = False
            return web.Response(status=500)
        return web.json_response({
            "listInfoList": [list_info.model_dump(by_alias=True, mode='json') for list_info in self.lists]
        })

    async def fetch_items(self, request):
        if self.fail_next:
            self.fail_next = False
            return web.Response(status=500)
        list_id = request.match_info['list_id']
        items = self.items.get(list_id, [])
        return web.json_response({
            "itemInfoList": [i.model_dump(by_alias=True, mode='json') for i in items]
        })

    async def add_item(self, request):
        if self.fail_next:
            self.fail_next = False
            return web.Response(status=500)
        list_id = request.match_info['list_id']
        data = await request.json()
        for item_data in data.get('items', []):
            new_item = ListItem(
                itemId=f"item{len(self.items.get(list_id, [])) + 1}",
                itemName=item_data['itemName'],
                itemStatus=ListItemStatus.ACTIVE,
                version=1
            )
            if list_id not in self.items:
                self.items[list_id] = []
            self.items[list_id].append(new_item)
        return web.json_response({"status": "SUCCESS"})

    async def update_item(self, request):
        if self.fail_next:
            self.fail_next = False
            return web.Response(status=400)
        list_id = request.match_info['list_id']
        item_id = request.match_info['item_id']
        data = await request.json()
        
        items = self.items.get(list_id, [])
        item = next((i for i in items if i.id == item_id), None)
        
        if not item:
            return web.Response(status=404)
            
        for update in data.get('itemAttributesToUpdate', []):
            if update['type'] == 'itemStatus':
                item.status = ListItemStatus(update['value'])
            elif update['type'] == 'itemName':
                item.original_name = update['value']
        
        item.version += 1
        return web.json_response({"status": "SUCCESS"})

    async def delete_item(self, request):
        if self.fail_next:
            self.fail_next = False
            return web.Response(status=404)
        list_id = request.match_info['list_id']
        item_id = request.match_info['item_id']
        
        items = self.items.get(list_id, [])
        self.items[list_id] = [i for i in items if i.id != item_id]
        return web.json_response({"status": "SUCCESS"})

@pytest.fixture
def fake_alexa():
    return FakeAlexaApiServer()

@pytest_asyncio.fixture
async def api(aiohttp_client, fake_alexa):
    app = web.Application()
    app.router.add_post('/alexashoppinglists/api/v2/lists/fetch', fake_alexa.fetch_lists)
    app.router.add_post('/alexashoppinglists/api/v2/lists/{list_id}/items/fetch', fake_alexa.fetch_items)
    app.router.add_post('/alexashoppinglists/api/v2/lists/{list_id}/items', fake_alexa.add_item)
    app.router.add_put('/alexashoppinglists/api/v2/lists/{list_id}/items/{item_id}', fake_alexa.update_item)
    app.router.add_delete('/alexashoppinglists/api/v2/lists/{list_id}/items/{item_id}', fake_alexa.delete_item)
    
    client = await aiohttp_client(app)
    
    mock_echo_api = MagicMock()
    mock_echo_api.domain = "com"
    mock_echo_api._http_wrapper = MagicMock()
    
    async def session_request(method, url, input_data, json_data):
        resp = await client.session.request(method, url, json=input_data if json_data else None)
        return None, resp
        
    mock_echo_api._http_wrapper.session_request = AsyncMock(side_effect=session_request)
    
    return AlexaToDoAPI(mock_echo_api, base_url=str(client.make_url('')))

@pytest.mark.asyncio
async def test_get_lists_success(api):
    lists = await api.get_lists()
    assert len(lists) == 3
    assert lists[0].id == "list1"
    assert lists[0].name == "Shop"
    assert lists[1].id == "list2"
    assert lists[1].name == "Todo"
    assert lists[2].id == "list3"
    assert lists[2].name == "Places to Visit"

@pytest.mark.asyncio
async def test_get_lists_failure(api, fake_alexa):
    fake_alexa.fail_next = True
    with pytest.raises(Exception, match="Failed to fetch lists"):
        await api.get_lists()

@pytest.mark.asyncio
async def test_get_list_items_success(api):
    items = await api.get_list_items("list1")
    assert len(items) == 3
    assert items[0].id == "item1"
    assert items[0].name == "Tapioka"
    assert items[0].status == ListItemStatus.ACTIVE
    assert items[1].id == "item2"
    assert items[1].name == "Milk"
    assert items[1].status == ListItemStatus.ACTIVE
    assert items[2].id == "item3"
    assert items[2].name == "Jasmine Tea"
    assert items[2].status == ListItemStatus.COMPLETE

@pytest.mark.asyncio
async def test_get_list_items_failure(api, fake_alexa):
    fake_alexa.fail_next = True
    with pytest.raises(Exception, match="Failed to fetch list items for list: list1"):
        await api.get_list_items("list1")

@pytest.mark.asyncio
async def test_set_item_checked_status_success(api, fake_alexa):
    await api.set_item_checked_status("list1", "item1", True, 1)
    assert fake_alexa.items["list1"][0].is_checked

@pytest.mark.asyncio
async def test_set_item_checked_status_failure(api, fake_alexa):
    fake_alexa.fail_next = True
    with pytest.raises(Exception, match="Failed to toggle item: item1"):
        await api.set_item_checked_status("list1", "item1", True, 1)

@pytest.mark.asyncio
async def test_add_item_success(api, fake_alexa):
    await api.add_item("list1", "Grass Jelly")
    assert len(fake_alexa.items["list1"]) == 4
    assert fake_alexa.items["list1"][-1].original_name == "Grass Jelly"

@pytest.mark.asyncio
async def test_add_item_failure(api, fake_alexa):
    fake_alexa.fail_next = True
    with pytest.raises(Exception, match="Failed to add item: Bread"):
        await api.add_item("list1", "Bread")

@pytest.mark.asyncio
async def test_delete_item_success(api, fake_alexa):
    before_count = len(fake_alexa.items["list1"])
    await api.delete_item("list1", "item1", 1)
    assert len(fake_alexa.items["list1"]) == before_count - 1

@pytest.mark.asyncio
async def test_delete_item_failure(api, fake_alexa):
    fake_alexa.fail_next = True
    with pytest.raises(Exception, match="Failed to delete item: item1"):
        await api.delete_item("list1", "item1", 1)

@pytest.mark.asyncio
async def test_rename_item_success(api, fake_alexa):
    await api.rename_item("list1", "item1", "Soy Milk", 1)
    assert fake_alexa.items["list1"][0].original_name == "Soy Milk"

@pytest.mark.asyncio
async def test_rename_item_failure(api, fake_alexa):
    fake_alexa.fail_next = True
    with pytest.raises(Exception, match="Failed to rename item: item1"):
        await api.rename_item("list1", "item1", "Soy Milk", 1)

@pytest.mark.asyncio
async def test_get_item_by_name_found(api):
    item = await api.get_item_by_name("list1", "Milk")
    assert item.id == "item2"

@pytest.mark.asyncio
async def test_get_item_by_name_case_insensitive(api):
    item = await api.get_item_by_name("list1", "milk")
    assert item.id == "item2"

@pytest.mark.asyncio
async def test_init(api):
    assert api._domain_extension == "com"
    assert api._base_url.startswith("http://127.0.0.1:")

@pytest.mark.asyncio
async def test_set_item_checked_status_uncheck(api, fake_alexa):
    # First set to checked
    await api.set_item_checked_status("list1", "item1", True, 1)
    assert fake_alexa.items["list1"][0].status == ListItemStatus.COMPLETE
    # Then uncheck
    await api.set_item_checked_status("list1", "item1", False, 2)
    assert fake_alexa.items["list1"][0].status == ListItemStatus.ACTIVE

@pytest.mark.asyncio
async def test_get_item_by_name_empty_list(api, fake_alexa):
    fake_alexa.items["list1"] = []
    with pytest.raises(ItemNotFoundException):
        await api.get_item_by_name("list1", "Milk")
