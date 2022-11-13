from flask import Flask
from flask_cors import CORS, cross_origin
import pandas as pd
import math
from cbdb_dao import CBDBDAO

app = Flask(__name__)
CORS(app, support_credentials=True)

@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"

@app.route("/analysis/network/<name>", methods=['GET'])
@cross_origin(support_credentials=True)
def getAssocData(name):
  data_csv = pd.read_csv(r'data.csv')
  row = data_csv[data_csv['authorNameCN'] == name]

  if len(row) == 0 or math.isnan(row['cid']) == True:
    return  {
      'data': {
        'id':'',
        'id2name': {},
        'events':[],
        'id2painter': {}
      }
    }
  else:
    id = int(row['cid'])
    cbdb_dao = CBDBDAO('./database/cbdb20220727.db', use_cache=True)
    cbdb_dao.getCBDBID(id)
    # 一度亲属关系和有直接事件联系的人，这群人互相之间关联的事件
    events = cbdb_dao.get_all_assoc_data()

    # 有画作信息的画家
    painter = {int(r['cid']): [r['山水'],r['人物'],r['花鸟']] 
      for i,r in data_csv.iterrows() 
      if math.isnan(r['cid']) == False
    }
    # cbdb认为是画家的人
    painterList = cbdb_dao.get_all_painter()

    id2painter = {key: painter[key] for key in cbdb_dao.cbdbid2name if key in painter}
    for id in painterList:
      if id not in id2painter:
        id2painter[id] = []

    return {
    'data': {
        'id':id,
        'id2name': cbdb_dao.cbdbid2name,
        'events':events,
        'id2painter': id2painter
      }
    }


if __name__ == '__main__':
  app.run(port=5000, debug=True)