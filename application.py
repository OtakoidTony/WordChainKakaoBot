from flask import Flask, request, jsonify
from urllib.request import urlopen, Request
from bs4 import BeautifulSoup
import urllib

import random
import json
from alliteration import *

ERROR_MESSAGE = '네트워크 접속에 문제가 발생하였습니다. 잠시 후 다시 시도해주세요.'

each_server = {}

app = Flask(__name__)


def send(text):
    res = {
        "version" : "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": text
                    }
                }
            ]
        }
    }
    return res


def load():
    with open('kkutu.txt', 'rt', encoding='utf-8') as f:
        s = f.read()
    global wordDict
    global hanbangSet
    global pat
    pat = re.compile('^[ㄱ-ㅎ가-힣]+$')
    wordDict = dict()
    hanbangSet = set()

    for i in sorted([i for i in s.split() if pat.match(i) and len(i) >= 2], key=lambda x: -len(x)):
        if i[0] not in wordDict:
            wordDict[i[0]] = set()
        wordDict[i[0]].add(i)
    global delList
    delList = list()
    for i in wordDict:
        for j in wordDict[i]:
            if j[-1] not in wordDict:
                delList.append(j)
    for j in delList:
        hanbangSet.add(j)
        wordDict[j[0]].remove(j)


def patch_data(dict, null_name, null_data):
    if not (null_name in dict):
        dict[null_name] = null_data


@app.route('/wordchain', methods=['POST'])
def wordchain():
    req = request.get_json()
    user_id = req["userRequest"]["user"]["id"]
    message = req["userRequest"]["utterance"]
    print(user_id)
    if not (str(user_id) in each_server):
        each_server[str(user_id)] = {
            "alreadySet" : set(),
            "round"      : 0,
            "win"        : 0,
            "lose"       : 0,
            "who"        : "CPU",
            "lastWord"   : "",
            "firstLetter": "",
            "firstTurn"  : True,
            "resetRound" : False,
            "isPlaying"  : False,
            "error"      : False
        }
    this_server = each_server[str(user_id)]

    if message == "!시작":
        load()
        this_server["lastWord"] = ''
        this_server["alreadySet"] = set()
        this_server["firstTurn"], this_server["resetRound"], this_server["isPlaying"] = True, False, True
        this_server["who"] = 'CPU'

        if this_server["isPlaying"] and this_server["who"] == 'CPU':
            if this_server["firstTurn"]:
                this_server["lastWord"] = random.choice(list(wordDict[random.choice(list(wordDict.keys()))]))
                this_server["alreadySet"].add(this_server["lastWord"])
                this_server["who"] = 'USER'
                this_server["firstTurn"] = False

        res = {
            "version" : "2.0",
            "template": {
                "outputs": [
                    {
                        "simpleText": {
                            "text": "CPU : " + this_server["lastWord"]
                        }
                    }
                ]
            }
        }
        return jsonify(res)

    else:
        if this_server["isPlaying"] and this_server["who"] == 'USER' and not this_server["firstTurn"]:
            if message == '!exit' or message == '!기권':
                this_server["resetRound"] = True
                this_server["isPlaying"] = False
                this_server["lose"] += 1
                this_server["who"] = 'CPU'
                this_server["error"] = False
                return jsonify(send('[결과] 당신은 기권했습니다. CPU의 승리입니다!'))

            this_server["firstLetter"] = message[0]
            this_server["error"] = False
            try:
                if (this_server["firstLetter"] != this_server["lastWord"][-1]) and not checkDueum(
                        this_server["lastWord"][-1], this_server["firstLetter"]):
                    this_server["who"] = 'USER'
                    this_server["error"] = True
                    return jsonify(send(" [오류] '" + this_server["lastWord"][-1] + "' (으)로 시작하는 단어를 입력하세요."))
                elif message in hanbangSet:
                    this_server["who"] = 'USER'
                    this_server["error"] = True
                    return jsonify(send(' [오류] 한방단어는 사용할 수 없습니다.'))
                elif message in this_server["alreadySet"]:
                    this_server["who"] = 'USER'
                    this_server["error"] = True
                    return jsonify(send(' [오류] 이미 나온 단어입니다.'))
                elif message not in wordDict.get(this_server["firstLetter"], set()):
                    this_server["who"] = 'USER'
                    this_server["error"] = True
                    return jsonify(send(' [오류] 사전에 없는 단어입니다.'))
            except IndexError:
                if this_server["firstLetter"] != this_server["lastWord"][-1]:
                    this_server["who"] = 'USER'
                    this_server["error"] = True
                    return jsonify(send(" [오류] '" + this_server["lastWord"][-1] + "' (으)로 시작하는 단어를 입력하세요."))
                elif message in hanbangSet:
                    this_server["who"] = 'USER'
                    this_server["error"] = True
                    return jsonify(send(' [오류] 한방단어는 사용할 수 없습니다.'))
                elif message in this_server["alreadySet"]:
                    this_server["who"] = 'USER'
                    this_server["error"] = True
                    return jsonify(send(' [오류] 이미 나온 단어입니다.'))
                elif message not in wordDict.get(this_server["firstLetter"], set()):
                    this_server["who"] = 'USER'
                    this_server["error"] = True
                    return jsonify(send(' [오류] 사전에 없는 단어입니다.'))

            if not this_server["error"]:
                this_server["who"] = 'CPU'
                this_server["alreadySet"].add(message)
                this_server["lastWord"] = message
                this_server["firstLetter"] = this_server["lastWord"][-1]
                if not list(filter(lambda x: x not in this_server["alreadySet"],
                                   wordDict.get(this_server["firstLetter"], set()))):
                    # 라운드 종료
                    this_server["who"] = 'CPU'
                    this_server["isPlaying"] = False
                    this_server["win"] += 1
                    return jsonify(send('[결과] CPU가 기권했습니다. 당신의 승리입니다!'))
                else:
                    nextWords = sorted(
                        filter(lambda x: x not in this_server["alreadySet"], wordDict[this_server["firstLetter"]]),
                        key=lambda x: -len(x))[
                                :random.randint(20, 50)]
                    this_server["lastWord"] = nextWords[random.randint(0, random.randrange(0, len(nextWords)))]
                    this_server["alreadySet"].add(this_server["lastWord"])
                    this_server["who"] = 'USER'
                    return jsonify(send(' CPU : ' + this_server["lastWord"]))

        if this_server["resetRound"] and not this_server["firstTurn"]:
            this_server["firstTurn"], this_server["resetRound"] = True, False
            this_server["who"] = 'CPU'
    return None


# 메인 함수
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)
