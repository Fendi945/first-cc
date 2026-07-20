""""""
import json, sys
from datetime import datetime, timedelta

sys.path.insert(0, '.')
from engine.feishu_client import FeishuClient

client = FeishuClient()
state = json.loads(open('feishu_bitable_state.json', encoding='utf-8').read())

info = state['bitables']['']
app_token = info['app_token']
# 
table_id = list(info['table_map'].values())[0]
print('table_id:', table_id)

tomorrow = int((datetime.now() + timedelta(days=1)).timestamp())

fields = {
    '': '',
    '': '',
    '': 'P0',
    '': tomorrow,
    '': ''
}
record = client.create_bitable_record(app_token, table_id, fields)
print('OK, record_id:', record.get('record_id', ''))
