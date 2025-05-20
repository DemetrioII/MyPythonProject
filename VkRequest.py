from functions import *
import json
import httpx
import asyncio
from fastapi import FastAPI, HTTPException
# from env import *

VK_APP_ID = "53265566"
BASE_DOMEN = "http://localhost"

VK_SERVICE_KEY = "fea2d7a3fea2d7a3fea2d7a30efd8e133dffea2fea2d7a39947b135431f0ea0ac217ce9"
VK_API_VERSION = "5.199"

app = FastAPI()

@app.get("/full-profile", tags=["Агрегированный профиль"])
async def get_full_profile(link: str):
    user_id = int(await parse(link))
    url = "https://api.vk.com/method/"
    token = VK_SERVICE_KEY
    version = "5.199"
    async with httpx.AsyncClient() as client:
        base_info = client.get(f"{url}users.get", params={
            "access_token": token,
            "user_ids": user_id,
            "v": version,
            "fields": "bdate, sex, city, relation, last_seen"
        })

        groups = client.get(f"{url}groups.get", params={
            "access_token": token,
            "user_id": user_id,
            "v": version,
            "extended": 1,
            "fields": "activity, age_limits"
        })

        wall = client.get(f"{url}wall.get", params={
            "access_token": token,
            "domain": user_id,
            "v": version
        })

        friends = client.get(f"{url}friends.get", params={
            "access_token": token,
            "user_id": user_id,
            "v": version,
            "fields": "sex,city"
        })

        followers = client.get(f"{url}users.getFollowers", params={
            "access_token": token,
            "user_id": user_id,
            "v": version,
            "fields": "sex,city"
        })

        responses = await asyncio.gather(base_info, groups, wall, friends, followers)

        data = {
            "base_info": responses[0].json().get("response", {}),
            "groups": responses[1].json().get("response", {}),
            "wall": responses[2].json().get("response", {}),
            "friends": responses[3].json().get("response", {}),
            "followers": responses[4].json().get("response", {})
        }

        for info, answer in data.items():
            if info == "base_info":
                data[info] = answer[0]
            if info == "groups":
                fields_to_keep = {'is_closed', 'deactivated', 'activity', 'age_limits', 'ban_info', 'is_favorite'}
                value_to_age = {1: 0, 2: 16, 3: 18}
                for item in data[info]['items']:
                    keys = list(item.keys())
                    for key in keys:
                        if key not in fields_to_keep:
                            del item[key]
                        if key == "age_limits":
                            item[key] = value_to_age.get(item[key], item[key])
            if info == "wall":
                if "reaction_sets" in answer:
                    del data[info]["reaction_sets"]

                fields_to_keep = {'marked_as_ads', 'date', 'from_id', 'id', 'reactions', 'owner_id', 'views'}
                for item in data[info]['items']:
                    keys = list(item.keys())
                    for key in keys:
                        if key not in fields_to_keep:
                            del item[key]
                        if key == "views":
                            item[key] = item["views"].get("count")
                        if key == "reactions":
                            item[key] = item["reactions"].get("count")

            if info == "friends":
                fields_to_keep = {'id', 'deactivated', 'sex', 'first_name', 'last_name', 'can_access_closed',
                                  'is_closed', 'city'}
                for item in data[info]['items']:
                    keys = list(item.keys())
                    for key in keys:
                        if key not in fields_to_keep:
                            del item[key]
            try:
                if info == "followers":
                    fields_to_keep = {'id', 'deactivated', 'sex', 'first_name', 'last_name', 'can_access_closed',
                                      'is_closed', 'city'}
                    for item in data[info]['items']:
                        keys = list(item.keys())
                        for key in keys:
                            if key not in fields_to_keep:
                                del item[key]
            except Exception:
                raise HTTPException(status_code=400)
        return json.dumps(data)

