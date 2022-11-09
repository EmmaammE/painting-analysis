from collections import defaultdict

from base_dao import SqliteDAO
import numpy as np
from opencc import OpenCC
import pandas as pd
import json

assoc_type2event_type = {
  '09': 'kinship',
  '04': 'politics',
  '02': 'academia',
  '05': 'academia',
  '01': 'sociality',
  '03': 'socaility',
  '08': 'religion',
  '06': 'military',
}

class CBDBDAO(SqliteDAO):
  def __init__(self, path, use_cache=True):
      super().__init__(path, use_cache)
      self.person_name2ids = {}
      self.cbdbid2name = {}
      self.peopleId = None
  
  def getCBDBID(self, peopleId):
    # 根据名字找到CBDB ID ? 还是直接对应ID
    cc = OpenCC('s2t')
    
    sql_str = '''SELECT c_personid,c_name_chn FROM BIOG_MAIN WHERE c_personid = {}'''.format(peopleId)
    rows = self._select(sql_str, ['c_personid', 'c_name_chn'])
    for row in rows:
      self.person_name2ids[cc.convert(row['c_name_chn'])] = row['c_personid']
      self.cbdbid2name[row['c_personid']] = cc.convert(row['c_name_chn'])

    self.peopleId = peopleId;

  def get_all_kin_data(self):
    cc = OpenCC('t2s')

    # 获取所有的亲属关系
    peopleIds = list(self.person_name2ids.values())
    sql_str = ''' select c_personid, c_kin_id, c_kinrel_chn from kin_data
      left outer join kinship_codes on kin_data.c_kin_code = kinship_codes.c_kincode 
      where kin_data.c_personid in {}'''.format(
        tuple(peopleIds) if len(peopleIds) > 1 else "({})".format(peopleIds[0])
      )

    rows = self._select(sql_str, ['c_personid', 'c_kin_id', 'c_kinrel_chn'])
    # [{'c_personid': 3676, 'c_kin_id': 1366, 'c_kinrel_chn': '子', type: 'kinship'},
    assoc_people = set()
    for row in rows:
      if row['c_kin_id'] not in self.cbdbid2name:
        assoc_people.add(row['c_kin_id'])
    self.get_people_info(list(assoc_people))
    
    # 翻译事件描述
    events = []
    for row in rows:
      event = {}
      event['p1'] = row['c_personid']
      event['p2'] = row['c_kin_id']
      event['type'] = 'kinship'
      event['year'] = None
      event['place'] = None
      event['desc'] = cc.convert(row['c_kinrel_chn'])
      events.append(event)
      
    return events

  def get_assoc_type(self, assoc_codes):
    if len(assoc_codes) == 0:
      return {}
    sql_str = '''SELECT c_assoc_code, c_assoc_type_id FROM assoc_code_type_rel
      WHERE c_assoc_code in {}'''.format(
        tuple(assoc_codes) if len(assoc_codes) > 1 else "({})".format(assoc_codes[0])
      )
    rows = self._select(sql_str, ['c_assoc_code', 'c_assoc_type'])
    assoc_code_rel = {}
    for row in rows:
      type = row['c_assoc_type'][:2]
      if type in assoc_type2event_type:
        assoc_code_rel[row['c_assoc_code']] = assoc_type2event_type[type]
      else:
        assoc_code_rel[row['c_assoc_code']] = 'others'
    return assoc_code_rel
  
  def get_people_info(self, pids):
    if(len(pids) == 0):
      return

    cc = OpenCC('t2s')
    
    sql_str = '''SELECT c_personid,c_name_chn FROM BIOG_MAIN WHERE c_personid in {}'''.format(
        tuple(pids) if len(pids) > 1 else "({})".format(pids[0])
      )
    rows = self._select(sql_str, ['c_personid', 'c_name_chn'])

    # print('info', pids)
    for row in rows:
      self.cbdbid2name[row['c_personid']] = cc.convert(row['c_name_chn'])

  def get_address_info(self, aids):
    cc = OpenCC('t2s')

    sql_str = '''SELECT c_addr_id, c_name_chn, belongs1_Name, belongs2_Name, belongs3_Name
        FROM addresses WHERE c_addr_id in {}'''.format(
        tuple(aids) if len(aids) > 1 else "({})".format(aids[0])
      )
    rows = self._select(sql_str, ['c_addr_id', 'c_name_chn', 'belongs1_Name', 'belongs2_Name', 'belongs3_Name'])
    
    address_info = {}
    for row in rows:
      address_info[row['c_addr_id']] = cc.convert(row['c_name_chn'])
      for key in ['belongs1_Name', 'belongs2_Name', 'belongs3_Name']:
        if row[key] is not None:
          address_info[row['c_addr_id']] += ' '+cc.convert(row[key])
    return address_info

  def get_all_assoc_data(self):
    cc = OpenCC('t2s')

    events = self.get_all_kin_data()

    # 查询关联到的人
    peopleIds = list(self.person_name2ids.values())
    sql_str = '''SELECT c_assoc_id FROM assoc_data WHERE c_personid in {}'''.format(
        tuple(peopleIds) if len(peopleIds) > 1 else "({})".format(peopleIds[0])
    )
    assoc_rows = self._select(sql_str, ['c_assoc_id'])
    assoc_people = set()
    for row in assoc_rows:
      if row['c_assoc_id'] not in self.cbdbid2name:
        assoc_people.add(row['c_assoc_id'])
    peopleIds.extend(list(assoc_people))

    sql_str = ''' SELECT assoc_data.c_assoc_code, c_personid, c_assoc_id, c_assoc_year, c_addr_id, c_assoc_desc_chn FROM assoc_data
      LEFT OUTER JOIN assoc_codes ON assoc_data.c_assoc_code = assoc_codes.c_assoc_code
      WHERE assoc_data.c_personid in {} and assoc_data.c_assoc_id in {}'''.format(
        tuple(peopleIds) if len(peopleIds) > 1 else "({})".format(peopleIds[0]),
        tuple(peopleIds) if len(peopleIds) > 1 else "({})".format(peopleIds[0]),
      )
    assoc_rows = self._select(sql_str, ['c_assoc_code', 'c_personid', 'c_assoc_id', 'c_assoc_year', 'c_addr_id','c_assoc_desc_chn'])

    # 查询关联到的地点、事件类型
    addr_list = set()
    assoc_codes = set()
    for row in assoc_rows:
      if row['c_addr_id'] != None and row['c_addr_id'] != 0:
          addr_list.add(row['c_addr_id'])
      assoc_codes.add(row['c_assoc_code'])

    # 查询code和info
    assoc_code_rel = self.get_assoc_type(list(assoc_codes))
    self.get_people_info(list(assoc_people))
    if len(addr_list) > 0:
      address_info = self.get_address_info(list(addr_list))
    else:
      address_info = {}

    # 翻译事件描述
    for row in assoc_rows:
      event = {}
      event['p1'] = row['c_personid']
      event['p2'] = row['c_assoc_id']
      event['type'] = assoc_code_rel.get(row['c_assoc_code'], None)
      event['year'] = row['c_assoc_year']
      event['place'] = address_info.get(row['c_addr_id'], None)
      event['desc'] = cc.convert(row['c_assoc_desc_chn'])
      events.append(event)

    json_object = json.dumps({
      'id': self.peopleId,
      'id2name': self.cbdbid2name,
      'events': events
    },ensure_ascii=False,)
    with open("sample_qiu.json", "w", encoding='utf-8' ) as outfile:
      outfile.write(json_object)

  def get_all_people(self, names):
    cc = OpenCC('s2t')
    names = [cc.convert(name) for name in names]

    print(names)

    sql_str = '''SELECT c_personid, c_name_chn FROM BIOG_MAIN WHERE c_name_chn in {}'''.format(
        tuple(names) if len(names) > 1 else "({})".format(names[0])
      )
    rows = self._select(sql_str, ['c_personid', 'c_name_chn'])
    json_object = json.dumps(rows, ensure_ascii=False)
    with open("data.json", "w", encoding='utf-8' ) as outfile:
      outfile.write(json_object)

if __name__ == '__main__':
  cbdb_dao = CBDBDAO('./database/cbdb20220727.db', use_cache=True)

  # people = ['3676', '3767'] # Mifu Sushi
  # people = 1430 # 米芾 苏轼 仇英
  # people = 1430 # 米芾 苏轼 仇英
  # people = 3676
  # people = '张羽'

  # cbdb_dao.getCBDBID(people)
  # cbdb_dao.get_all_assoc_data()

  df = pd.read_csv(r'./authorID_authorName_themes.csv')
  # names = df['authorNameCN']
  names= ['苏轼', '仇英']
  cbdb_dao.get_all_people(names)
